# app/services/stop_loss_take_profit_service.py
"""
손절/익절 자동 체결 시스템
- 최근 체결 내역 기반 가격 체크
- 조건 만족 시 자동 청산
"""
from sqlmodel import Session, select
from app.models.database import Order, OrderType, OrderStatus, OrderSide, Position, PositionStatus
from app.models.futures import FuturesPosition, FuturesPositionStatus, FuturesPositionSide
from app.services.binance_service import get_recent_trades, get_current_price
from decimal import Decimal
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

async def check_stop_loss_take_profit_orders(session: Session):
    """
    현물 거래 손절/익절 주문 체크
    
    로직:
    1. PENDING 상태의 STOP_LOSS, TAKE_PROFIT 주문 조회
    2. 최근 체결 내역에서 stop_price 도달 여부 확인
    3. 조건 만족 시 시장가로 체결
    """
    
    try:
        # 대기 중인 손절/익절 주문 조회
        pending_orders = session.exec(
            select(Order).where(
                Order.order_status == OrderStatus.PENDING,
                Order.order_type.in_([OrderType.STOP_LOSS, OrderType.TAKE_PROFIT])
            )
        ).all()
        
        if not pending_orders:
            return
        
        logger.debug(f"🔍 손절/익절 주문 체크: {len(pending_orders)}개")
        
        # 심볼별 최근 체결 내역 캐시
        trades_cache = {}
        
        for order in pending_orders:
            try:
                # 최근 체결 내역 조회 (캐시 활용)
                if order.symbol not in trades_cache:
                    trades_cache[order.symbol] = await get_recent_trades(
                        order.symbol, 
                        limit=100
                    )
                
                recent_trades = trades_cache[order.symbol]
                
                if not recent_trades:
                    continue
                
                # 조건 체크
                should_execute = check_price_condition(
                    order=order,
                    recent_trades=recent_trades
                )
                
                if should_execute:
                    # 자동 체결
                    await execute_stop_loss_take_profit(session, order, recent_trades)
                    
                    logger.info(
                        f"✅ {order.order_type.value} 자동 체결: "
                        f"{order.symbol} #{order.id}"
                    )
            
            except Exception as e:
                logger.error(f"❌ 주문 체크 실패 {order.id}: {e}")
                continue
    
    except Exception as e:
        logger.error(f"❌ 손절/익절 체크 실패: {e}")


def check_price_condition(order: Order, recent_trades: list) -> bool:
    """
    가격 조건 체크
    
    Args:
        order: 주문 정보
        recent_trades: 최근 체결 내역
    
    Returns:
        bool: 체결 조건 만족 여부
    """
    
    if not order.stop_price:
        return False
    
    stop_price = order.stop_price
    
    # 최근 체결 내역에서 조건 만족하는 거래 찾기
    for trade in recent_trades:
        trade_price = Decimal(str(trade['price']))
        
        if order.order_type == OrderType.STOP_LOSS:
            # 손절: 매도 주문
            # 가격이 stop_price 이하로 떨어졌는지 체크
            if trade_price <= stop_price:
                logger.info(
                    f"🔴 손절 조건 만족: {order.symbol} "
                    f"체결가 ${trade_price} <= 손절가 ${stop_price}"
                )
                return True
        
        elif order.order_type == OrderType.TAKE_PROFIT:
            # 익절: 매도 주문
            # 가격이 stop_price 이상으로 올랐는지 체크
            if trade_price >= stop_price:
                logger.info(
                    f"🟢 익절 조건 만족: {order.symbol} "
                    f"체결가 ${trade_price} >= 익절가 ${stop_price}"
                )
                return True
    
    return False


async def execute_stop_loss_take_profit(
    session: Session,
    order: Order,
    recent_trades: list
):
    """
    손절/익절 주문 체결
    
    로직:
    1. 최근 체결 내역 기반으로 체결
    2. 평균 체결가 계산
    3. 잔액/포지션 업데이트
    """
    
    try:
        from app.models.database import TradingAccount, Transaction
        from app.services.order_service import OrderService
        
        # 계정 조회
        account = session.exec(
            select(TradingAccount).where(TradingAccount.user_id == order.user_id)
        ).first()
        
        if not account:
            raise Exception("계정을 찾을 수 없습니다")
        
        # 현재 가격으로 체결
        current_price = await get_current_price(order.symbol)
        
        # 수수료 계산
        from app.core.config import settings
        fee = order.quantity * Decimal(str(current_price)) * Decimal(str(settings.DEFAULT_TRADING_FEE))
        
        # 주문 업데이트
        order.executed_quantity = order.quantity
        order.executed_price = Decimal(str(current_price))
        order.fee = fee
        order.order_status = OrderStatus.FILLED
        order.updated_at = datetime.utcnow()
        
        # 포지션 업데이트 (매도)
        position = session.exec(
            select(Position).where(
                Position.user_id == order.user_id,
                Position.symbol == order.symbol,
                Position.position_status == PositionStatus.OPEN
            )
        ).first()
        
        if position:
            # PnL 계산
            realized_pnl = (order.executed_price - position.average_price) * order.quantity
            position.realized_pnl += realized_pnl
            position.quantity -= order.quantity
            
            if position.quantity <= 0:
                position.position_status = PositionStatus.CLOSED
            
            # 계정 업데이트
            revenue = (order.executed_price * order.quantity) - fee
            account.balance += revenue
            account.total_profit += realized_pnl
        
        # 거래 내역 추가
        transaction = Transaction(
            user_id=order.user_id,
            order_id=order.id,
            transaction_type=f"TRADE_{order.order_type.value}",
            amount=order.quantity * order.executed_price,
            balance_after=account.balance,
            description=f"{order.order_type.value} {order.quantity} {order.symbol} @ {order.executed_price}"
        )
        
        session.add(transaction)
        session.commit()
        
        logger.info(
            f"📈 {order.order_type.value} 체결 완료: "
            f"{order.quantity} {order.symbol} @ ${current_price:.2f}"
        )
        
    except Exception as e:
        session.rollback()
        logger.error(f"❌ 손절/익절 체결 실패: {e}")
        raise


async def check_futures_stop_loss_take_profit(session: Session):
    """
    선물 거래 손절/익절 체크
    
    로직:
    1. OPEN 상태 포지션 중 stop_loss, take_profit 설정된 것 조회
    2. 현재 가격과 비교
    3. 조건 만족 시 자동 청산
    """
    
    try:
        # 손절/익절 설정된 포지션 조회
        positions = session.exec(
            select(FuturesPosition).where(
                FuturesPosition.status == FuturesPositionStatus.OPEN
            )
        ).all()
        
        for position in positions:
            if not position.stop_loss and not position.take_profit:
                continue
                
            try:
                # 현재 가격 조회
                current_price = await get_current_price(position.symbol)
                current_price = Decimal(str(current_price))
                
                should_close = False
                close_reason = ""
                
                # 손절 체크
                if position.stop_loss:
                    if position.side == FuturesPositionSide.LONG:
                        # 롱: 가격 하락 시 손절
                        if current_price <= position.stop_loss:
                            should_close = True
                            close_reason = "STOP_LOSS"
                    else:  # SHORT
                        # 숏: 가격 상승 시 손절
                        if current_price >= position.stop_loss:
                            should_close = True
                            close_reason = "STOP_LOSS"
                
                # 익절 체크
                if not should_close and position.take_profit:
                    if position.side == FuturesPositionSide.LONG:
                        # 롱: 가격 상승 시 익절
                        if current_price >= position.take_profit:
                            should_close = True
                            close_reason = "TAKE_PROFIT"
                    else:  # SHORT
                        # 숏: 가격 하락 시 익절
                        if current_price <= position.take_profit:
                            should_close = True
                            close_reason = "TAKE_PROFIT"
                
                if should_close:
                    await execute_futures_auto_close(
                        session, position, current_price, close_reason
                    )
                    
                    logger.info(
                        f"{'🔴' if close_reason == 'STOP_LOSS' else '🟢'} "
                        f"선물 {close_reason}: {position.symbol} "
                        f"{position.side.value} #{position.id}"
                    )
                    
            except Exception as e:
                logger.error(f"❌ 포지션 체크 실패 {position.id}: {e}")
                continue
    
    except Exception as e:
        logger.error(f"❌ 선물 손절/익절 체크 실패: {e}")


async def execute_futures_auto_close(
    session: Session,
    position: FuturesPosition,
    close_price: Decimal,
    reason: str
):
    """선물 포지션 자동 청산"""
    
    try:
        from app.models.futures import FuturesAccount, FuturesTransaction
        from app.services.futures_service import futures_service
        
        # Close position using futures service
        closed_position = await futures_service.close_position(
            session=session,
            user_id=position.user_id,
            position_id=position.id
        )
        
        logger.info(
            f"✅ 선물 {reason} 체결: {position.symbol} {position.side.value} "
            f"손익: ${closed_position.realized_pnl:.2f}"
        )
        
    except Exception as e:
        logger.error(f"❌ 선물 자동 청산 실패: {e}")
        raise