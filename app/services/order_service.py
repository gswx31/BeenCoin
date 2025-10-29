# app/services/order_service.py
"""
주문 서비스 - 실제 거래소 시뮬레이션
최근 체결 내역 기반으로 주문 처리
"""

from sqlmodel import Session, select
from app.models.database import (
    Order, TradingAccount, Position, Transaction,
    OrderSide, OrderType, OrderStatus
)
from app.schemas.order import OrderCreate
from app.services.binance_service import get_current_price, get_recent_trades
from decimal import Decimal
from datetime import datetime
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)


async def create_order(session: Session, user_id: str, order_data: OrderCreate) -> Order:
    """
    주문 생성 (실제 거래소 방식)
    
    로직:
    1. 최근 체결 내역 조회 (Binance API)
    2. 주문 수량만큼 체결 내역에서 체결
    3. 매수: 낮은 가격부터 체결
    4. 매도: 높은 가격부터 체결
    """
    
    try:
        # 계정 조회
        account = session.exec(
            select(TradingAccount).where(TradingAccount.user_id == user_id)
        ).first()
        
        if not account:
            raise HTTPException(status_code=404, detail="계정을 찾을 수 없습니다")
        
        # 주문 생성
        order = Order(
            account_id=account.id,
            user_id=user_id,
            symbol=order_data.symbol,
            side=OrderSide(order_data.side),
            order_type=OrderType(order_data.order_type),
            order_status=OrderStatus.PENDING,
            quantity=Decimal(str(order_data.quantity)),
            price=Decimal(str(order_data.price)) if order_data.price else None,
            filled_quantity=Decimal("0"),
            average_price=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        session.add(order)
        session.flush()
        
        # ✅ 시장가 주문 → 최근 체결 내역으로 즉시 체결
        if order.order_type == OrderType.MARKET:
            await execute_order_with_recent_trades(session, order)
            logger.info(f"✅ 시장가 주문 체결 완료: {order.symbol}")
        
        # ✅ 지정가 주문 → 체결 가능하면 즉시 체결, 아니면 대기
        elif order.order_type == OrderType.LIMIT:
            # 현재가 확인
            current_price = await get_current_price(order_data.symbol)
            
            # 체결 가능 여부 판단
            can_fill = False
            if order.side == OrderSide.BUY and current_price <= order.price:
                can_fill = True  # 매수: 현재가 ≤ 주문가
            elif order.side == OrderSide.SELL and current_price >= order.price:
                can_fill = True  # 매도: 현재가 ≥ 주문가
            
            if can_fill:
                await execute_order_with_recent_trades(session, order)
                logger.info(f"✅ 지정가 주문 즉시 체결: {order.symbol} @ ${order.price}")
            else:
                logger.info(f"⏳ 지정가 주문 대기: {order.symbol} @ ${order.price}")
        
        session.commit()
        session.refresh(order)
        
        return order
    
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"❌ 주문 생성 실패: {e}")
        raise HTTPException(status_code=500, detail=f"주문 생성 실패: {str(e)}")


async def execute_order_with_recent_trades(session: Session, order: Order):
    """
    최근 체결 내역 기반으로 주문 실행 (실제 거래소 방식)
    
    예시:
    - 최근 체결: [120원, 119.5원, 121원, 120.5원, ...]
    - 매수 0.5 BTC 주문
    - → 낮은 가격부터: 119.5원(0.2) + 120원(0.15) + 120.5원(0.15) = 0.5 BTC
    - → 평균 체결가: 120원
    """
    
    try:
        # 계정 조회
        account = session.get(TradingAccount, order.account_id)
        if not account:
            raise HTTPException(status_code=404, detail="계정을 찾을 수 없습니다")
        
        # ✅ 1단계: 최근 체결 내역 조회 (Binance API)
        recent_trades = await get_recent_trades(order.symbol, limit=100)
        
        if not recent_trades:
            # API 실패 시 현재가로 fallback
            logger.warning(f"⚠️ 체결 내역 조회 실패, 현재가로 체결: {order.symbol}")
            current_price = await get_current_price(order.symbol)
            await execute_order_simple(session, order, current_price)
            return
        
        # ✅ 2단계: 체결 내역 정렬
        if order.side == OrderSide.BUY:
            # 매수: 낮은 가격부터 체결
            sorted_trades = sorted(recent_trades, key=lambda x: x['price'])
        else:
            # 매도: 높은 가격부터 체결
            sorted_trades = sorted(recent_trades, key=lambda x: x['price'], reverse=True)
        
        # ✅ 3단계: 주문 수량만큼 체결
        remaining_quantity = order.quantity
        total_cost = Decimal("0")
        filled_quantity = Decimal("0")
        
        for trade in sorted_trades:
            if remaining_quantity <= 0:
                break
            
            trade_price = Decimal(str(trade['price']))
            trade_quantity = Decimal(str(trade['quantity']))
            
            # 이번 체결량 결정
            fill_qty = min(remaining_quantity, trade_quantity)
            
            # 체결
            total_cost += fill_qty * trade_price
            filled_quantity += fill_qty
            remaining_quantity -= fill_qty
            
            logger.debug(f"  체결: {fill_qty} @ ${trade_price}")
        
        # 체결 완료 확인
        if filled_quantity < order.quantity:
            logger.warning(f"⚠️ 부분 체결: {filled_quantity}/{order.quantity}")
        
        # 평균 체결가 계산
        average_price = total_cost / filled_quantity if filled_quantity > 0 else Decimal("0")
        
        logger.info(f"📊 체결 완료: {filled_quantity} {order.symbol} @ 평균 ${average_price:.2f}")
        
        # ✅ 4단계: 잔액/포지션 업데이트
        await finalize_order_execution(
            session, order, account, 
            filled_quantity, average_price
        )
    
    except Exception as e:
        session.rollback()
        logger.error(f"❌ 주문 체결 실패: {e}")
        raise


async def execute_order_simple(session: Session, order: Order, price: Decimal):
    """
    단순 체결 (API 실패 시 fallback)
    """
    
    try:
        account = session.get(TradingAccount, order.account_id)
        if not account:
            raise HTTPException(status_code=404, detail="계정을 찾을 수 없습니다")
        
        await finalize_order_execution(
            session, order, account,
            order.quantity, price
        )
    
    except Exception as e:
        session.rollback()
        logger.error(f"❌ 단순 체결 실패: {e}")
        raise


async def finalize_order_execution(
    session: Session,
    order: Order,
    account: TradingAccount,
    filled_quantity: Decimal,
    average_price: Decimal
):
    """
    주문 체결 최종 처리
    - 잔액 업데이트
    - 포지션 업데이트
    - 거래 내역 기록
    """
    
    try:
        # 수수료 계산 (0.1%)
        fee_rate = Decimal("0.001")
        total_amount = filled_quantity * average_price
        fee = total_amount * fee_rate
        
        # ===== 매수 =====
        if order.side == OrderSide.BUY:
            # 필요 금액 확인
            required_balance = total_amount + fee
            
            if account.balance < required_balance:
                raise HTTPException(
                    status_code=400,
                    detail=f"잔액 부족 (필요: ${required_balance:.2f}, 보유: ${account.balance:.2f})"
                )
            
            # 잔액 차감
            account.balance -= required_balance
            
            # 포지션 업데이트
            position = session.exec(
                select(Position).where(
                    Position.account_id == account.id,
                    Position.symbol == order.symbol
                )
            ).first()
            
            if not position:
                # 신규 포지션 생성
                position = Position(
                    account_id=account.id,
                    symbol=order.symbol,
                    quantity=filled_quantity,
                    average_price=average_price,
                    current_price=average_price,
                    current_value=filled_quantity * average_price,
                    unrealized_profit=Decimal("0"),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                session.add(position)
            else:
                # 기존 포지션 업데이트 (평균가 계산)
                total_qty = position.quantity + filled_quantity
                total_cost = (position.quantity * position.average_price) + total_amount
                position.average_price = total_cost / total_qty
                position.quantity = total_qty
                position.current_value = total_qty * average_price
                position.unrealized_profit = total_qty * (average_price - position.average_price)
                position.updated_at = datetime.utcnow()
            
            logger.info(
                f"💰 매수 체결: {filled_quantity} @ ${average_price:.2f}, "
                f"수수료: ${fee:.2f}, 잔액: ${account.balance:.2f}"
            )
        
        # ===== 매도 =====
        else:
            # 포지션 확인
            position = session.exec(
                select(Position).where(
                    Position.account_id == account.id,
                    Position.symbol == order.symbol
                )
            ).first()
            
            if not position or position.quantity < filled_quantity:
                raise HTTPException(
                    status_code=400,
                    detail=f"수량 부족 (필요: {filled_quantity}, 보유: {position.quantity if position else 0})"
                )
            
            # 수익 계산
            profit = filled_quantity * (average_price - position.average_price)
            
            # 잔액 증가 (매도 대금 - 수수료)
            account.balance += (total_amount - fee)
            account.total_profit += profit
            
            # 포지션 차감
            position.quantity -= filled_quantity
            if position.quantity > 0:
                position.current_value = position.quantity * average_price
                position.unrealized_profit = position.quantity * (average_price - position.average_price)
            else:
                # 전체 청산
                position.quantity = Decimal("0")
                position.current_value = Decimal("0")
                position.unrealized_profit = Decimal("0")
                position.current_price = Decimal("0")
            
            position.updated_at = datetime.utcnow()
            
            logger.info(
                f"💸 매도 체결: {filled_quantity} @ ${average_price:.2f}, "
                f"수익: ${profit:.2f}, 수수료: ${fee:.2f}, 잔액: ${account.balance:.2f}"
            )
        
        # 주문 상태 업데이트
        order.order_status = OrderStatus.FILLED
        order.filled_quantity = filled_quantity
        order.average_price = average_price
        order.fee = fee
        order.updated_at = datetime.utcnow()
        
        # 거래 내역 기록
        transaction = Transaction(
            user_id=account.user_id,
            order_id=order.id,
            symbol=order.symbol,
            side=order.side,
            quantity=filled_quantity,
            price=average_price,
            fee=fee,
            timestamp=datetime.utcnow()
        )
        
        # DB 커밋
        account.updated_at = datetime.utcnow()
        
        session.add_all([order, account, position, transaction])
        session.commit()
        
        session.refresh(order)
        session.refresh(account)
        session.refresh(position)
    
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"❌ 체결 처리 실패: {e}")
        raise


def get_user_orders(
    session: Session,
    user_id: str,
    symbol: str = None,
    status: str = None,
    limit: int = 100
) -> list:
    """사용자 주문 목록 조회"""
    
    try:
        query = select(Order).where(Order.user_id == user_id)
        
        if symbol:
            query = query.where(Order.symbol == symbol)
        
        if status:
            query = query.where(Order.order_status == status)
        
        query = query.order_by(Order.created_at.desc()).limit(limit)
        
        orders = session.exec(query).all()
        
        logger.debug(f"📋 주문 목록 조회: User={user_id}, Count={len(orders)}")
        
        return list(orders)
    
    except Exception as e:
        logger.error(f"❌ 주문 목록 조회 실패: {e}")
        return []


def cancel_order(session: Session, user_id: str, order_id: int) -> Order:
    """
    주문 취소 (시그니처 수정)
    
    Args:
        session: DB 세션
        user_id: 사용자 ID (UUID string)
        order_id: 주문 ID
    
    Returns:
        Order: 취소된 주문
    """
    
    try:
        order = session.get(Order, order_id)
        
        if not order:
            raise HTTPException(status_code=404, detail="주문을 찾을 수 없습니다")
        
        if order.user_id != user_id:
            raise HTTPException(status_code=403, detail="권한이 없습니다")
        
        if order.order_status != OrderStatus.PENDING:
            raise HTTPException(
                status_code=400,
                detail=f"취소할 수 없는 주문 상태: {order.order_status}"
            )
        
        order.order_status = OrderStatus.CANCELLED
        order.updated_at = datetime.utcnow()
        
        session.add(order)
        session.commit()
        session.refresh(order)
        
        logger.info(f"🚫 주문 취소: Order ID={order_id}")
        
        return order
    
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"❌ 주문 취소 실패: {e}")
        raise HTTPException(status_code=500, detail=f"주문 취소 실패: {str(e)}")