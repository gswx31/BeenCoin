# app/services/order_service.py
from sqlmodel import Session, select
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


async def create_order(session: Session, user_id: int, order_data: OrderCreate) -> Order:
    """주문 생성 및 처리 (수수료 없음)"""
    
    # 입력 검증
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
    
    # 계정 조회
    account = session.exec(
        select(SpotAccount).where(SpotAccount.user_id == user_id)
    ).first()
    
    if not account:
        raise HTTPException(status_code=404, detail="계정을 찾을 수 없습니다")
    
    # 시장가 매수 - 사전 잔액 검증
    if order_data.order_type == 'MARKET' and order_data.side == OrderSide.BUY:
        try:
            estimated_price = await get_current_price(order_data.symbol)
            required = estimated_price * quantity
            
            if account.usdt_balance < required:
                raise HTTPException(
                    status_code=400,
                    detail=f"잔액 부족: 보유 ${float(account.usdt_balance):.2f} / 필요 ${float(required):.2f}"
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ 가격 조회 실패: {e}")
            raise HTTPException(status_code=503, detail="시장 가격 조회 실패")
    
    # 주문 생성
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
    
    # 시장가 주문 즉시 체결
    if order.order_type == 'MARKET':
        try:
            current_price = await execute_market_order(order.symbol, order.side, quantity)
            _fill_order(session, order, current_price, quantity)
            session.refresh(order)
            logger.info(f"✅ 시장가 체결: ID={order.id}, ${current_price}")
            
        except HTTPException:
            order.status = OrderStatus.REJECTED
            session.add(order)
            session.commit()
            raise
            
        except Exception as e:
            order.status = OrderStatus.REJECTED
            session.add(order)
            session.commit()
            logger.error(f"❌ 시장가 체결 실패: {e}")
            raise HTTPException(status_code=500, detail=f"주문 체결 실패: {str(e)}")
    
    # 지정가 주문 모니터링
    elif order.order_type == 'LIMIT':
        if not price:
            raise HTTPException(status_code=400, detail="지정가 주문은 가격이 필요합니다")
        
        asyncio.create_task(
            _monitor_limit_order(order.id, order.symbol, order.side, quantity, price, user_id)
        )
        logger.info(f"⏳ 지정가 모니터링 시작: ID={order.id}, Target=${price}")
    
    return order


def _fill_order(session: Session, order: Order, price: Decimal, quantity: Decimal):
    """주문 체결 처리 (수수료 없음)"""
    
    try:
        # 계정 조회
        account = session.exec(
            select(SpotAccount).where(SpotAccount.user_id == order.user_id)
        ).first()
        
        if not account:
            raise HTTPException(status_code=404, detail="계정을 찾을 수 없습니다")
        
        # 포지션 조회/생성
        position = session.exec(
            select(SpotPosition).where(
                SpotPosition.account_id == account.id,
                SpotPosition.symbol == order.symbol
            )
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
        
        # 매수 처리
        if order.side == OrderSide.BUY:
            total_cost = price * quantity
            
            if account.usdt_balance < total_cost:
                raise HTTPException(
                    status_code=400,
                    detail=f"잔액 부족: 보유 ${float(account.usdt_balance):.2f} / 필요 ${float(total_cost):.2f}"
                )
            
            # 평균단가 계산
            new_qty = position.quantity + quantity
            total_value = (position.average_price * position.quantity) + (price * quantity)
            position.average_price = total_value / new_qty if new_qty > 0 else price
            position.quantity = new_qty
            account.usdt_balance -= total_cost
            
            logger.info(f"💰 매수 체결: {quantity} {order.symbol} @ ${price}")
        
        # 매도 처리
        elif order.side == OrderSide.SELL:
            if position.quantity < quantity:
                raise HTTPException(
                    status_code=400,
                    detail=f"보유 수량 부족: {float(position.quantity)} (필요: {float(quantity)})"
                )
            
            position.quantity -= quantity
            proceeds = price * quantity
            profit = (price - position.average_price) * quantity
            
            account.usdt_balance += proceeds
            account.total_profit += profit
            
            logger.info(f"💸 매도 체결: {quantity} {order.symbol} @ ${price} (손익: ${profit})")
        
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
            fee=Decimal('0'),  # 수수료 없음
            timestamp=datetime.utcnow()
        )
        session.add(transaction)
        
        # 포지션 평가
        position.current_price = price
        position.current_value = position.quantity * price
        position.unrealized_profit = position.quantity * (price - position.average_price)
        position.updated_at = datetime.utcnow()
        
        # 커밋
        session.add(order)
        session.add(account)
        session.add(position)
        session.commit()
        
        logger.info(f"✅ 체결 완료: Order ID={order.id}")
        
    except HTTPException:
        session.rollback()
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"❌ 체결 처리 실패: {e}")
        raise HTTPException(status_code=500, detail="주문 체결 처리 실패")


async def _monitor_limit_order(
    order_id: int,
    symbol: str,
    side: str,
    quantity: Decimal,
    target_price: Decimal,
    user_id: int
):
    """지정가 주문 모니터링"""
    from app.core.database import engine
    
    max_duration = 24 * 3600
    check_interval = 2
    elapsed_time = 0
    last_trade_id = None
    
    logger.info(f"⏳ 지정가 모니터링 시작: {side} {quantity} {symbol} @ ${target_price}")
    
    try:
        while elapsed_time < max_duration:
            try:
                trades = await get_recent_trades(symbol, limit=50)
                
                if trades:
                    if last_trade_id:
                        trades = [t for t in trades if t['id'] > last_trade_id]
                    
                    if trades:
                        last_trade_id = max(t['id'] for t in trades)
                    
                    for trade in trades:
                        trade_price = Decimal(str(trade['price']))
                        
                        should_fill = False
                        
                        if side == OrderSide.BUY and trade_price <= target_price:
                            should_fill = True
                            logger.info(f"💰 매수 조건 충족: ${trade_price} <= ${target_price}")
                        
                        elif side == OrderSide.SELL and trade_price >= target_price:
                            should_fill = True
                            logger.info(f"💸 매도 조건 충족: ${trade_price} >= ${target_price}")
                        
                        if should_fill:
                            with Session(engine) as new_session:
                                order = new_session.get(Order, order_id)
                                if order and order.status == OrderStatus.PENDING:
                                    _fill_order(new_session, order, trade_price, quantity)
                                    logger.info(f"✅ 지정가 체결: ID={order_id} @ ${trade_price}")
                            return
                
                await asyncio.sleep(check_interval)
                elapsed_time += check_interval
                
            except Exception as e:
                logger.error(f"❌ 모니터링 체크 오류: {e}")
                await asyncio.sleep(5)
                elapsed_time += 5
        
        # 24시간 만료
        with Session(engine) as new_session:
            order = new_session.get(Order, order_id)
            if order and order.status == OrderStatus.PENDING:
                order.status = OrderStatus.EXPIRED
                order.updated_at = datetime.utcnow()
                new_session.add(order)
                new_session.commit()
                logger.warning(f"⏰ 주문 만료: ID={order_id}")
                
    except Exception as e:
        logger.error(f"❌ 모니터링 중단: {e}")


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
        
        logger.info(f"🚫 주문 취소: ID={order_id}")
        
        return {"message": "주문이 취소되었습니다"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 주문 취소 실패: {e}")
        raise HTTPException(status_code=500, detail="주문 취소 실패")


def get_user_orders(session: Session, user_id: int, limit: int = 100):
    """사용자 주문 내역 조회"""
    try:
        return session.exec(
            select(Order)
            .where(Order.user_id == user_id)
            .order_by(Order.created_at.desc())
            .limit(limit)
        ).all()
    except Exception as e:
        logger.error(f"❌ 주문 내역 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="주문 내역 조회 실패")


def get_account_summary(session: Session, user_id: int) -> dict:
    """계정 요약 정보"""
    try:
        account = session.exec(
            select(SpotAccount).where(SpotAccount.user_id == user_id)
        ).first()
        
        if not account:
            raise HTTPException(status_code=404, detail="계정을 찾을 수 없습니다")
        
        positions = session.exec(
            select(SpotPosition).where(SpotPosition.account_id == account.id)
        ).all()
        
        total_value = account.usdt_balance
        for pos in positions:
            total_value += pos.current_value
        
        return {
            "balance": float(account.usdt_balance),
            "total_value": float(total_value),
            "total_profit": float(account.total_profit),
            "positions_count": len(positions)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 계정 요약 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="계정 요약 조회 실패")


def get_transaction_history(session: Session, user_id: int, limit: int = 100):
    """거래 내역 조회"""
    try:
        transactions = session.exec(
            select(Transaction)
            .where(Transaction.user_id == user_id)
            .order_by(Transaction.timestamp.desc())
            .limit(limit)
        ).all()
        
        return transactions
        
    except Exception as e:
        logger.error(f"❌ 거래 내역 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="거래 내역 조회 실패")    