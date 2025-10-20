# app/services/order_service.py
"""
주문 서비스 - 동시성 문제 해결 및 안정성 강화
"""
from sqlmodel import Session, select
from sqlalchemy import select as sa_select
from app.models.database import (
    Order, SpotAccount, SpotPosition, Transaction,
    OrderSide, OrderStatus, TradingType
)
from app.services.binance_service import get_current_price, execute_market_order, get_recent_trades
from decimal import Decimal, InvalidOperation
from app.schemas.order import OrderCreate
from fastapi import HTTPException
from datetime import datetime
import logging
import asyncio

logger = logging.getLogger(__name__)

# 수수료 설정
FEE_RATE = Decimal('0.001')  # 0.1%

# 지정가 주문 모니터링 태스크 관리
active_monitoring_tasks = {}


class OrderError(HTTPException):
    """주문 처리 중 발생하는 에러의 기본 클래스"""
    pass


class InsufficientBalanceError(OrderError):
    def __init__(self, available: Decimal, required: Decimal):
        super().__init__(
            status_code=400,
            detail=f"잔액 부족: 보유 ${float(available):.2f} / 필요 ${float(required):.2f}"
        )


class InsufficientQuantityError(OrderError):
    def __init__(self, available: Decimal, required: Decimal):
        super().__init__(
            status_code=400,
            detail=f"보유 수량 부족: {float(available):.8f} / 필요 {float(required):.8f}"
        )


async def create_order(session: Session, user_id: int, order_data: OrderCreate) -> Order:
    """
    주문 생성 및 처리
    
    개선사항:
    - ✅ 비관적 락으로 동시성 문제 해결
    - ✅ 트랜잭션 롤백 보장
    - ✅ 에러 처리 세분화
    """
    
    # 1. 입력 검증
    try:
        quantity = Decimal(str(order_data.quantity))
        if quantity <= 0:
            raise ValueError("수량은 0보다 커야 합니다")
        
        price = None
        if order_data.price:
            price = Decimal(str(order_data.price))
            if price <= 0:
                raise ValueError("가격은 0보다 커야 합니다")
    except (ValueError, InvalidOperation) as e:
        raise HTTPException(status_code=400, detail=f"잘못된 입력: {str(e)}")
    
    # 2. ✅ 비관적 락으로 계정 조회 (동시성 문제 해결)
    try:
        account = session.exec(
            sa_select(SpotAccount)
            .where(SpotAccount.user_id == user_id)
            .with_for_update()  # ✅ 행 단위 락
        ).first()
        
        if not account:
            raise HTTPException(status_code=404, detail="계정을 찾을 수 없습니다")
            
    except Exception as e:
        logger.error(f"❌ 계정 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="계정 조회 실패")
    
    # 3. 시장가 주문 사전 검증
    if order_data.order_type == 'MARKET':
        try:
            estimated_price = await get_current_price(order_data.symbol)
            
            # 매수: 잔액 검증
            if order_data.side == OrderSide.BUY:
                required = estimated_price * quantity
                
                if account.usdt_balance < required:
                    raise InsufficientBalanceError(account.usdt_balance, required)
            
            # 매도: 포지션 검증
            elif order_data.side == OrderSide.SELL:
                position = session.exec(
                    select(SpotPosition).where(
                        SpotPosition.account_id == account.id,
                        SpotPosition.symbol == order_data.symbol
                    )
                ).first()
                
                available = position.quantity if position else Decimal('0')
                if available < quantity:
                    raise InsufficientQuantityError(available, quantity)
                    
        except OrderError:
            raise
        except Exception as e:
            logger.error(f"❌ 가격 조회 실패: {e}")
            raise HTTPException(status_code=503, detail="시장 가격 조회 실패")
    
    # 4. 주문 생성
    order = Order(
        user_id=user_id,
        trading_type=TradingType.SPOT,
        symbol=order_data.symbol,
        side=order_data.side,
        order_type=order_data.order_type,
        quantity=quantity,
        price=price,
        status=OrderStatus.PENDING,
        filled_quantity=Decimal('0')
    )
    
    try:
        session.add(order)
        session.commit()
        session.refresh(order)
        
        logger.info(f"📝 주문 생성: ID={order.id}, {order.side} {quantity} {order_data.symbol}")
        
    except Exception as e:
        session.rollback()
        logger.error(f"❌ 주문 생성 실패: {e}")
        raise HTTPException(status_code=500, detail="주문 생성 실패")
    
    # 5. 주문 실행
    try:
        if order.order_type == 'MARKET':
            current_price = await execute_market_order(order.symbol, order.side, quantity)
            _fill_order(session, order, current_price, quantity)
            session.refresh(order)
            logger.info(f"✅ 시장가 체결: ID={order.id}, ${current_price}")
            
        elif order.order_type == 'LIMIT':
            if not price:
                raise HTTPException(status_code=400, detail="지정가 주문은 가격이 필요합니다")
            
            _start_monitoring_task(order.id, order.symbol, order.side, quantity, price, user_id)
            logger.info(f"⏳ 지정가 모니터링 시작: ID={order.id}, Target=${price}")
            
    except OrderError:
        order.status = OrderStatus.REJECTED
        session.add(order)
        session.commit()
        raise
    except Exception as e:
        order.status = OrderStatus.REJECTED
        session.add(order)
        session.commit()
        logger.error(f"❌ 주문 실행 실패: {e}")
        raise HTTPException(status_code=500, detail=f"주문 실행 실패: {str(e)}")
    
    return order


def _fill_order(session: Session, order: Order, price: Decimal, quantity: Decimal):
    """
    주문 체결 처리
    
    개선사항:
    - ✅ 트랜잭션 롤백 보장
    - ✅ 수수료 계산 추가
    """
    
    try:
        # ✅ 비관적 락으로 계정 조회
        account = session.exec(
            sa_select(SpotAccount)
            .where(SpotAccount.user_id == order.user_id)
            .with_for_update()
        ).first()
        
        if not account:
            raise HTTPException(status_code=404, detail="계정을 찾을 수 없습니다")
        
        # ✅ 비관적 락으로 포지션 조회/생성
        position = session.exec(
            sa_select(SpotPosition)
            .where(
                SpotPosition.account_id == account.id,
                SpotPosition.symbol == order.symbol
            )
            .with_for_update()
        ).first()
        
        if not position:
            position = SpotPosition(
                account_id=account.id,
                symbol=order.symbol,
                quantity=Decimal('0'),
                average_price=Decimal('0'),
                current_price=price,
                current_value=Decimal('0'),
                unrealized_profit=Decimal('0')
            )
            session.add(position)
            session.flush()
        
        # ✅ 수수료 계산
        fee = price * quantity * FEE_RATE
        
        # 매수 처리
        if order.side == OrderSide.BUY:
            total_cost = (price * quantity) + fee
            
            if account.usdt_balance < total_cost:
                raise InsufficientBalanceError(account.usdt_balance, total_cost)
            
            # 평균단가 계산
            if position.quantity > 0:
                total_value = (position.average_price * position.quantity) + (price * quantity)
                new_quantity = position.quantity + quantity
                position.average_price = total_value / new_quantity
            else:
                position.average_price = price
            
            position.quantity += quantity
            account.usdt_balance -= total_cost
            
            logger.info(f"💰 매수 체결: {quantity} {order.symbol} @ ${price} (수수료: ${fee})")
        
        # 매도 처리
        elif order.side == OrderSide.SELL:
            if position.quantity < quantity:
                raise InsufficientQuantityError(position.quantity, quantity)
            
            # 실현 손익 계산
            proceeds = (price * quantity) - fee
            realized_profit = (price - position.average_price) * quantity
            
            position.quantity -= quantity
            account.usdt_balance += proceeds
            account.total_profit += realized_profit
            
            # 포지션이 0이 되면 평균단가 초기화
            if position.quantity == 0:
                position.average_price = Decimal('0')
            
            logger.info(f"💸 매도 체결: {quantity} {order.symbol} @ ${price} (손익: ${realized_profit})")
        
        # 주문 상태 업데이트
        order.filled_quantity = quantity
        order.average_price = price
        order.status = OrderStatus.FILLED
        order.updated_at = datetime.utcnow()
        
        # 거래 내역 기록
        transaction = Transaction(
            user_id=order.user_id,
            order_id=order.id,
            trading_type=TradingType.SPOT,
            symbol=order.symbol,
            side=order.side,
            quantity=quantity,
            price=price,
            fee=fee,  # ✅ 수수료 기록
            timestamp=datetime.utcnow()
        )
        
        # 포지션 평가 업데이트
        position.current_price = price
        position.current_value = position.quantity * price
        position.unrealized_profit = position.quantity * (price - position.average_price) if position.quantity > 0 else Decimal('0')
        position.updated_at = datetime.utcnow()
        
        # ✅ 모든 변경사항을 한번에 커밋
        session.add_all([order, account, position, transaction])
        session.commit()
        
        logger.info(f"✅ 체결 완료: Order ID={order.id}")
        
    except OrderError:
        session.rollback()
        raise
    except HTTPException:
        session.rollback()
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"❌ 체결 처리 실패: {e}")
        raise HTTPException(status_code=500, detail="주문 체결 처리 실패")


def _start_monitoring_task(
    order_id: int,
    symbol: str,
    side: str,
    quantity: Decimal,
    target_price: Decimal,
    user_id: int
):
    """
    지정가 주문 모니터링 태스크 시작
    
    개선사항:
    - ✅ 태스크 관리로 메모리 누수 방지
    """
    
    # 이미 모니터링 중인지 확인
    if order_id in active_monitoring_tasks:
        logger.warning(f"⚠️ 주문 {order_id}는 이미 모니터링 중입니다")
        return
    
    # 태스크 생성 및 등록
    task = asyncio.create_task(
        _monitor_limit_order(order_id, symbol, side, quantity, target_price, user_id)
    )
    
    active_monitoring_tasks[order_id] = task
    
    # 태스크 완료 시 자동 제거
    def cleanup(future):
        active_monitoring_tasks.pop(order_id, None)
        logger.info(f"🧹 태스크 정리 완료: Order ID={order_id}")
    
    task.add_done_callback(cleanup)
    
    logger.info(f"🚀 모니터링 태스크 시작: Order ID={order_id}")


async def _monitor_limit_order(
    order_id: int,
    symbol: str,
    side: str,
    quantity: Decimal,
    target_price: Decimal,
    user_id: int
):
    """지정가 주문 모니터링 (24시간)"""
    from app.core.database import engine
    
    max_duration = 24 * 3600  # 24시간
    check_interval = 2  # 2초마다 체크
    elapsed_time = 0
    last_trade_id = None
    
    logger.info(f"⏳ 지정가 주문 모니터링 시작: Order ID={order_id}")

def get_user_orders(session: Session, user_id: int, limit: int = 50):
    """사용자 주문 내역 조회"""
    orders = session.exec(
        select(Order)
        .where(Order.user_id == user_id)
        .order_by(Order.created_at.desc())
        .limit(limit)
    ).all()
    
    return orders
def cancel_order(session: Session, user_id: int, order_id: int) -> dict:
    """주문 취소"""
    try:
        order = session.get(Order, order_id)
        
        if not order:
            raise HTTPException(status_code=404, detail="주문을 찾을 수 없습니다")
        
        if order.user_id != user_id:
            raise HTTPException(status_code=403, detail="권한이 없습니다")
        
        if order.status != OrderStatus.PENDING:
            raise HTTPException(status_code=400, detail="취소할 수 없는 주문입니다")
        
        order.status = OrderStatus.CANCELLED
        order.updated_at = datetime.utcnow()
        session.add(order)
        session.commit()
        
        logger.info(f"❌ 주문 취소: ID={order_id}")
        
        return {"message": "주문이 취소되었습니다", "order_id": order_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 주문 취소 실패: {e}")
        raise HTTPException(status_code=500, detail="주문 취소 실패")


def get_user_orders(session: Session, user_id: int, limit: int = 50):
    """사용자 주문 내역 조회"""
    orders = session.exec(
        select(Order)
        .where(Order.user_id == user_id)
        .order_by(Order.created_at.desc())
        .limit(limit)
    ).all()
    
    return orders


def get_account_summary(session: Session, user_id: int) -> dict:
    """계정 요약 조회"""
    account = session.exec(
        select(SpotAccount).where(SpotAccount.user_id == user_id)
    ).first()
    
    if not account:
        return {"balance": 0, "total_profit": 0}
    
    return {
        "balance": float(account.usdt_balance),
        "total_profit": float(account.total_profit)
    }


def get_transaction_history(session: Session, user_id: int, limit: int = 100):
    """거래 내역 조회"""
    transactions = session.exec(
        select(Transaction)
        .where(Transaction.user_id == user_id)
        .order_by(Transaction.timestamp.desc())
        .limit(limit)
    ).all()
    
    return transactions