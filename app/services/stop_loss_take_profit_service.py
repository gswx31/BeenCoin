# app/services/stop_loss_take_profit_service.py
"""
손절/익절 자동 체결 시스템
- 최근 체결 내역 기반 가격 체크
- 조건 만족 시 자동 청산
"""
from sqlmodel import Session, select
from app.models.database import Order, OrderType, OrderStatus, OrderSide
from app.models.futures import FuturesPosition, FuturesPositionStatus
from app.services.binance_service import get_recent_trades
from app.services.order_service import execute_market_order_complete
from app.services.futures_service import close_futures_position
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
        from app.models.database import TradingAccount
        
        # 계정 조회
        account = session.get(TradingAccount, order.account_id)
        if not account:
            raise Exception("계정을 찾을 수 없습니다")
        
        # 조건에 맞는 체결 내역 필터링
        eligible_trades = []
        
        for trade in recent_trades:
            trade_price = Decimal(str(trade['price']))
            
            if order.order_type == OrderType.STOP_LOSS:
                if trade_price <= order.stop_price:
                    eligible_trades.append(trade)
            elif order.order_type == OrderType.TAKE_PROFIT:
                if trade_price >= order.stop_price:
                    eligible_trades.append(trade)
        
        if not eligible_trades:
            logger.warning(f"⚠️ 조건 만족 체결 내역 없음: {order.symbol}")
            return
        
        # 가격 정렬 (매도이므로 높은 가격 우선)
        sorted_trades = sorted(
            eligible_trades, 
            key=lambda x: Decimal(str(x['price'])),
            reverse=True
        )
        
        # 체결 처리
        remaining_quantity = order.quantity
        total_cost = Decimal("0")
        filled_quantity = Decimal("0")
        
        for trade in sorted_trades:
            if remaining_quantity <= 0:
                break
            
            trade_price = Decimal(str(trade['price']))
            trade_quantity = Decimal(str(trade['quantity']))
            
            fill_qty = min(remaining_quantity, trade_quantity)
            
            total_cost += fill_qty * trade_price
            filled_quantity += fill_qty
            remaining_quantity -= fill_qty
            
            logger.debug(f"  📊 체결: {fill_qty} @ ${trade_price}")
        
        # 남은 수량은 stop_price로 체결
        if remaining_quantity > 0:
            total_cost += remaining_quantity * order.stop_price
            filled_quantity += remaining_quantity
            logger.debug(
                f"  📊 나머지 체결: {remaining_quantity} @ ${order.stop_price}"
            )
        
        # 평균 체결가
        average_price = total_cost / filled_quantity if filled_quantity > 0 else order.stop_price
        
        logger.info(
            f"📈 {order.order_type.value} 체결 완료: "
            f"{filled_quantity} {order.symbol} @ 평균 ${average_price:.2f}"
        )
        
        # 최종 처리
        from app.services.order_service import finalize_order_execution
        await finalize_order_execution(
            session, order, account,
            filled_quantity, average_price
        )
        
    except Exception as e:
        session.rollback()
        logger.error(f"❌ 손절/익절 체결 실패: {e}")
        raise


async def check_futures_stop_loss_take_profit(session: Session):
    """
    선물 거래 손절/익절 체크
    
    로직:
    1. OPEN 상태 포지션 중 stop_loss_price, take_profit_price 설정된 것 조회
    2. 최근 체결 내역에서 가격 도달 여부 확인
    3. 조건 만족 시 자동 청산
    """
    
    try:
        # 손절/익절 설정된 포지션 조회
        positions = session.exec(
            select(FuturesPosition).where(
                FuturesPosition.status == FuturesPositionStatus.OPEN,
                (FuturesPosition.stop_loss_price.isnot(None)) | 
                (FuturesPosition.take_profit_price.isnot(None))
            )
        ).all()
        
        if not positions:
            return
        
        logger.debug(f"🔍 선물 손절/익절 체크: {len(positions)}개 포지션")
        
        # 심볼별 최근 체결 내역 캐시
        trades_cache = {}
        
        for position in positions:
            try:
                # 최근 체결 내역 조회
                if position.symbol not in trades_cache:
                    trades_cache[position.symbol] = await get_recent_trades(
                        position.symbol,
                        limit=100
                    )
                
                recent_trades = trades_cache[position.symbol]
                
                if not recent_trades:
                    continue
                
                # 가격 범위 확인
                prices = [Decimal(str(t['price'])) for t in recent_trades]
                min_price = min(prices)
                max_price = max(prices)
                
                # 손절 체크
                if position.stop_loss_price:
                    should_stop_loss = False
                    
                    if position.side == FuturesPositionSide.LONG:
                        # 롱: 가격 하락 시 손절
                        should_stop_loss = min_price <= position.stop_loss_price
                    else:  # SHORT
                        # 숏: 가격 상승 시 손절
                        should_stop_loss = max_price >= position.stop_loss_price
                    
                    if should_stop_loss:
                        await execute_futures_stop_loss(
                            session, position, recent_trades
                        )
                        logger.warning(
                            f"🔴 선물 손절 체결: {position.symbol} "
                            f"{position.side.value} #{position.id}"
                        )
                        continue
                
                # 익절 체크
                if position.take_profit_price:
                    should_take_profit = False
                    
                    if position.side == FuturesPositionSide.LONG:
                        # 롱: 가격 상승 시 익절
                        should_take_profit = max_price >= position.take_profit_price
                    else:  # SHORT
                        # 숏: 가격 하락 시 익절
                        should_take_profit = min_price <= position.take_profit_price
                    
                    if should_take_profit:
                        await execute_futures_take_profit(
                            session, position, recent_trades
                        )
                        logger.info(
                            f"🟢 선물 익절 체결: {position.symbol} "
                            f"{position.side.value} #{position.id}"
                        )
                        continue
            
            except Exception as e:
                logger.error(f"❌ 포지션 체크 실패 {position.id}: {e}")
                continue
    
    except Exception as e:
        logger.error(f"❌ 선물 손절/익절 체크 실패: {e}")


async def execute_futures_stop_loss(
    session: Session,
    position: FuturesPosition,
    recent_trades: list
):
    """선물 손절 체결"""
    
    try:
        from app.models.futures import FuturesAccount, FuturesTransaction
        
        # 손절가 이하/이상 거래 찾기
        eligible_trades = []
        
        for trade in recent_trades:
            trade_price = Decimal(str(trade['price']))
            
            if position.side == FuturesPositionSide.LONG:
                # 롱: 손절가 이하
                if trade_price <= position.stop_loss_price:
                    eligible_trades.append(trade)
            else:  # SHORT
                # 숏: 손절가 이상
                if trade_price >= position.stop_loss_price:
                    eligible_trades.append(trade)
        
        # 평균 청산가 계산
        if eligible_trades:
            avg_price = sum(
                Decimal(str(t['price'])) for t in eligible_trades
            ) / len(eligible_trades)
        else:
            avg_price = position.stop_loss_price
        
        # 손익 계산
        pnl = position.calculate_pnl(avg_price)
        fee_rate = Decimal("0.0004")
        position_value = avg_price * position.quantity
        fee = position_value * fee_rate
        net_pnl = pnl - fee
        
        # 계정 업데이트
        account = session.get(FuturesAccount, position.account_id)
        account.balance += (position.margin + net_pnl)
        account.margin_used -= position.margin
        account.total_profit += net_pnl
        account.unrealized_pnl -= position.unrealized_pnl
        account.updated_at = datetime.utcnow()
        
        # 포지션 업데이트
        position.status = FuturesPositionStatus.CLOSED
        position.mark_price = avg_price
        position.realized_pnl = net_pnl
        position.closed_at = datetime.utcnow()
        
        # 거래 내역
        transaction = FuturesTransaction(
            user_id=account.user_id,
            position_id=position.id,
            symbol=position.symbol,
            side=position.side,
            action="STOP_LOSS",
            quantity=position.quantity,
            price=avg_price,
            leverage=position.leverage,
            pnl=net_pnl,
            fee=fee,
            timestamp=datetime.utcnow()
        )
        
        session.add_all([account, position, transaction])
        session.commit()
        
        logger.warning(
            f"🔴 손절 체결: {position.symbol} {position.side.value} "
            f"손실: ${net_pnl:.2f} (청산가: ${avg_price:.2f})"
        )
    
    except Exception as e:
        session.rollback()
        logger.error(f"❌ 선물 손절 실패: {e}")
        raise


async def execute_futures_take_profit(
    session: Session,
    position: FuturesPosition,
    recent_trades: list
):
    """선물 익절 체결"""
    
    try:
        from app.models.futures import FuturesAccount, FuturesTransaction
        
        # 익절가 이상/이하 거래 찾기
        eligible_trades = []
        
        for trade in recent_trades:
            trade_price = Decimal(str(trade['price']))
            
            if position.side == FuturesPositionSide.LONG:
                # 롱: 익절가 이상
                if trade_price >= position.take_profit_price:
                    eligible_trades.append(trade)
            else:  # SHORT
                # 숏: 익절가 이하
                if trade_price <= position.take_profit_price:
                    eligible_trades.append(trade)
        
        # 평균 청산가 계산
        if eligible_trades:
            avg_price = sum(
                Decimal(str(t['price'])) for t in eligible_trades
            ) / len(eligible_trades)
        else:
            avg_price = position.take_profit_price
        
        # 손익 계산
        pnl = position.calculate_pnl(avg_price)
        fee_rate = Decimal("0.0004")
        position_value = avg_price * position.quantity
        fee = position_value * fee_rate
        net_pnl = pnl - fee
        
        # 계정 업데이트
        account = session.get(FuturesAccount, position.account_id)
        account.balance += (position.margin + net_pnl)
        account.margin_used -= position.margin
        account.total_profit += net_pnl
        account.unrealized_pnl -= position.unrealized_pnl
        account.updated_at = datetime.utcnow()
        
        # 포지션 업데이트
        position.status = FuturesPositionStatus.CLOSED
        position.mark_price = avg_price
        position.realized_pnl = net_pnl
        position.closed_at = datetime.utcnow()
        
        # 거래 내역
        transaction = FuturesTransaction(
            user_id=account.user_id,
            position_id=position.id,
            symbol=position.symbol,
            side=position.side,
            action="TAKE_PROFIT",
            quantity=position.quantity,
            price=avg_price,
            leverage=position.leverage,
            pnl=net_pnl,
            fee=fee,
            timestamp=datetime.utcnow()
        )
        
        session.add_all([account, position, transaction])
        session.commit()
        
        logger.info(
            f"🟢 익절 체결: {position.symbol} {position.side.value} "
            f"수익: ${net_pnl:.2f} (청산가: ${avg_price:.2f})"
        )
    
    except Exception as e:
        session.rollback()
        logger.error(f"❌ 선물 익절 실패: {e}")
        raise