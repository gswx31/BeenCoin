# app/services/order_service.py
"""
주문 서비스 - 수정 버전
1. 시장가 주문 완전 체결 보장
2. locked_balance 구현 (주문 금액 락)
3. 손절/익절 주문 지원
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
    주문 생성
    
    로직 개선:
    1. 시장가 주문 → 완전 체결 보장
    2. 지정가 주문 → locked_balance로 금액 잠금
    3. 손절/익절 주문 지원
    """
    
    try:
        # 계정 조회
        account = session.exec(
            select(TradingAccount).where(TradingAccount.user_id == user_id)
        ).first()
        
        if not account:
            raise HTTPException(status_code=404, detail="계정을 찾을 수 없습니다")
        
        # 현재가 조회
        current_price = await get_current_price(order_data.symbol)
        
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
            stop_price=Decimal(str(order_data.stop_price)) if hasattr(order_data, 'stop_price') and order_data.stop_price else None,
            filled_quantity=Decimal("0"),
            average_price=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        session.add(order)
        session.flush()
        
        # ===== 시장가 주문 =====
        if order.order_type == OrderType.MARKET:
            await execute_market_order_complete(session, order, current_price)
            logger.info(f"✅ 시장가 주문 완전 체결: {order.symbol}")
        
        # ===== 지정가 주문 =====
        elif order.order_type == OrderType.LIMIT:
            # 즉시 체결 가능 여부 확인
            can_fill = False
            if order.side == OrderSide.BUY and current_price <= order.price:
                can_fill = True
            elif order.side == OrderSide.SELL and current_price >= order.price:
                can_fill = True
            
            if can_fill:
                # 즉시 체결
                await execute_market_order_complete(session, order, current_price)
                logger.info(f"✅ 지정가 주문 즉시 체결: {order.symbol} @ ${order.price}")
            else:
                # 대기 상태 → 금액 잠금
                await lock_order_amount(session, order, account)
                logger.info(f"⏳ 지정가 주문 대기: {order.symbol} @ ${order.price}")
        
        # ===== 손절/익절 주문 =====
        elif order.order_type in [OrderType.STOP_LOSS, OrderType.TAKE_PROFIT]:
            # 조건 확인
            triggered = False
            if order.order_type == OrderType.STOP_LOSS and current_price <= order.stop_price:
                triggered = True
            elif order.order_type == OrderType.TAKE_PROFIT and current_price >= order.stop_price:
                triggered = True
            
            if triggered:
                await execute_market_order_complete(session, order, current_price)
                logger.info(f"✅ {order.order_type} 주문 트리거: {order.symbol}")
            else:
                await lock_order_amount(session, order, account)
                logger.info(f"⏳ {order.order_type} 주문 대기")
        
        session.commit()
        session.refresh(order)
        
        return order
    
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"❌ 주문 생성 실패: {e}")
        raise HTTPException(status_code=500, detail=f"주문 생성 실패: {str(e)}")


async def execute_market_order_complete(
    session: Session,
    order: Order,
    current_price: Decimal
):
    """
    시장가 주문 완전 체결 (개선 버전)
    
    기존 문제:
    - recent_trades의 수량이 부족하면 부분 체결
    
    개선:
    1. recent_trades로 최대한 채움
    2. 부족하면 현재가로 나머지 체결
    3. 100% 체결 보장
    """
    
    try:
        account = session.get(TradingAccount, order.account_id)
        if not account:
            raise HTTPException(status_code=404, detail="계정을 찾을 수 없습니다")
        
        # 1단계: 최근 체결 내역으로 체결 시도
        recent_trades = await get_recent_trades(order.symbol, limit=100)
        
        remaining_quantity = order.quantity
        total_cost = Decimal("0")
        filled_quantity = Decimal("0")
        
        if recent_trades:
            # 정렬
            if order.side == OrderSide.BUY:
                sorted_trades = sorted(recent_trades, key=lambda x: x['price'])
            else:
                sorted_trades = sorted(recent_trades, key=lambda x: x['price'], reverse=True)
            
            # 체결
            for trade in sorted_trades:
                if remaining_quantity <= 0:
                    break
                
                trade_price = Decimal(str(trade['price']))
                trade_quantity = Decimal(str(trade['quantity']))
                
                fill_qty = min(remaining_quantity, trade_quantity)
                
                total_cost += fill_qty * trade_price
                filled_quantity += fill_qty
                remaining_quantity -= fill_qty
                
                logger.debug(f"  체결: {fill_qty} @ ${trade_price}")
        
        # 2단계: 남은 수량을 현재가로 체결 (완전 체결 보장)
        if remaining_quantity > 0:
            logger.warning(
                f"⚠️ Recent trades 부족, 남은 {remaining_quantity}를 "
                f"현재가 ${current_price}로 체결"
            )
            total_cost += remaining_quantity * current_price
            filled_quantity += remaining_quantity
            remaining_quantity = Decimal("0")
        
        # 평균 체결가 계산
        average_price = total_cost / filled_quantity if filled_quantity > 0 else current_price
        
        logger.info(
            f"📊 완전 체결: {filled_quantity} {order.symbol} @ "
            f"평균 ${average_price:.2f}"
        )
        
        # 3단계: 잔액/포지션 업데이트
        await finalize_order_execution(
            session, order, account,
            filled_quantity, average_price
        )
    
    except Exception as e:
        session.rollback()
        logger.error(f"❌ 주문 체결 실패: {e}")
        raise


async def lock_order_amount(
    session: Session,
    order: Order,
    account: TradingAccount
):
    """
    지정가/손절/익절 주문 시 금액 잠금
    
    - 매수: (가격 * 수량 * 1.001) 만큼 잠금
    - 매도: 포지션 수량 확인만
    """
    
    try:
        if order.side == OrderSide.BUY:
            # 매수 주문 → 금액 잠금
            price = order.price if order.order_type == OrderType.LIMIT else order.stop_price
            required_amount = price * order.quantity * Decimal("1.001")  # 수수료 포함
            
            if account.balance < required_amount:
                raise HTTPException(
                    status_code=400,
                    detail=f"잔액 부족 (필요: ${required_amount:.2f}, 보유: ${account.balance:.2f})"
                )
            
            # 잔액에서 locked_balance로 이동
            account.balance -= required_amount
            account.locked_balance += required_amount
            
            logger.info(f"🔒 금액 잠금: ${required_amount:.2f} (주문 ID: {order.id})")
        
        else:
            # 매도 주문 → 포지션 확인만
            position = session.exec(
                select(Position).where(
                    Position.account_id == account.id,
                    Position.symbol == order.symbol
                )
            ).first()
            
            if not position or position.quantity < order.quantity:
                raise HTTPException(
                    status_code=400,
                    detail=f"수량 부족 (필요: {order.quantity}, 보유: {position.quantity if position else 0})"
                )
            
            logger.info(f"✅ 매도 주문 수량 확인 완료")
        
        account.updated_at = datetime.utcnow()
        session.add(account)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 금액 잠금 실패: {e}")
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
    """
    
    try:
        fee_rate = Decimal("0.001")
        total_amount = filled_quantity * average_price
        fee = total_amount * fee_rate
        
        # ===== 매수 =====
        if order.side == OrderSide.BUY:
            required_balance = total_amount + fee
            
            # locked_balance에서 차감된 경우 (지정가 주문)
            if order.order_status == OrderStatus.PENDING:
                # 잠긴 금액 해제 후 다시 차감
                locked_amount = order.price * order.quantity * Decimal("1.001")
                account.locked_balance -= locked_amount
                account.balance += locked_amount
            
            # 잔액 확인
            if account.balance < required_balance:
                raise HTTPException(
                    status_code=400,
                    detail=f"잔액 부족"
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
            position = session.exec(
                select(Position).where(
                    Position.account_id == account.id,
                    Position.symbol == order.symbol
                )
            ).first()
            
            if not position or position.quantity < filled_quantity:
                raise HTTPException(
                    status_code=400,
                    detail=f"수량 부족"
                )
            
            # 실현 손익 계산
            profit = filled_quantity * (average_price - position.average_price)
            
            # 잔액 증가
            account.balance += (total_amount - fee)
            account.total_profit += profit
            
            # 포지션 차감
            position.quantity -= filled_quantity
            if position.quantity > 0:
                position.current_value = position.quantity * average_price
                position.unrealized_profit = position.quantity * (average_price - position.average_price)
            else:
                position.quantity = Decimal("0")
                position.current_value = Decimal("0")
                position.unrealized_profit = Decimal("0")
            
            position.updated_at = datetime.utcnow()
            
            logger.info(
                f"💸 매도 체결: {filled_quantity} @ ${average_price:.2f}, "
                f"수익: ${profit:.2f}, 수수료: ${fee:.2f}"
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
            realized_profit=profit if order.side == OrderSide.SELL else None,
            timestamp=datetime.utcnow()
        )
        
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
    주문 취소 + locked_balance 해제
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
        
        # 계정 조회
        account = session.get(TradingAccount, order.account_id)
        
        # locked_balance 해제 (매수 주문인 경우)
        if order.side == OrderSide.BUY:
            price = order.price if order.order_type == OrderType.LIMIT else order.stop_price
            locked_amount = price * order.quantity * Decimal("1.001")
            
            account.locked_balance -= locked_amount
            account.balance += locked_amount
            account.updated_at = datetime.utcnow()
            
            logger.info(f"🔓 금액 해제: ${locked_amount:.2f}")
        
        # 주문 취소
        order.order_status = OrderStatus.CANCELLED
        order.updated_at = datetime.utcnow()
        
        session.add_all([order, account])
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


async def check_pending_orders(session: Session):
    """
    대기 중인 주문 체크 (백그라운드 작업)
    
    - 지정가 주문: 가격 도달 시 체결
    - 손절/익절 주문: 조건 만족 시 체결
    """
    
    try:
        pending_orders = session.exec(
            select(Order).where(Order.order_status == OrderStatus.PENDING)
        ).all()
        
        for order in pending_orders:
            current_price = await get_current_price(order.symbol)
            
            should_execute = False
            
            # 지정가 체크
            if order.order_type == OrderType.LIMIT:
                if order.side == OrderSide.BUY and current_price <= order.price:
                    should_execute = True
                elif order.side == OrderSide.SELL and current_price >= order.price:
                    should_execute = True
            
            # 손절/익절 체크
            elif order.order_type == OrderType.STOP_LOSS:
                if current_price <= order.stop_price:
                    should_execute = True
            
            elif order.order_type == OrderType.TAKE_PROFIT:
                if current_price >= order.stop_price:
                    should_execute = True
            
            # 체결 실행
            if should_execute:
                account = session.get(TradingAccount, order.account_id)
                await execute_market_order_complete(session, order, current_price)
                logger.info(f"⚡ 대기 주문 체결: {order.symbol} #{order.id}")
    
    except Exception as e:
        logger.error(f"❌ 대기 주문 체크 실패: {e}")