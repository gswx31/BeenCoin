# app/services/order_service.py - 수수료 제거 버전
from sqlmodel import Session, select
from fastapi import HTTPException
from decimal import Decimal
from datetime import datetime
import asyncio
from typing import List

from app.models.database import (
    Order, SpotAccount, SpotPosition, Transaction,
    OrderSide, OrderStatus, OrderType, TradingType
)
from app.schemas.order import OrderCreate
from app.services.binance_service import get_current_price, get_recent_trades
from app.utils.logger import logger


async def create_order(
    session: Session,
    user_id: int,
    order_data: OrderCreate
) -> Order:
    """
    주문 생성 (수수료 없음)
    """
    # 수량과 가격 검증
    quantity = Decimal(str(order_data.quantity))
    price = Decimal(str(order_data.price)) if order_data.price else None
    
    if quantity <= 0:
        raise HTTPException(status_code=400, detail="수량은 0보다 커야 합니다")
    
    if order_data.order_type == OrderType.LIMIT and (not price or price <= 0):
        raise HTTPException(status_code=400, detail="지정가 주문은 가격이 필요합니다")
    
    # 주문 객체 생성
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
    if order.order_type == OrderType.MARKET:
        try:
            current_price = await get_current_price(order.symbol)
            _fill_order(session, order, Decimal(str(current_price)), quantity)
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
    elif order.order_type == OrderType.LIMIT:
        if not price:
            raise HTTPException(status_code=400, detail="지정가 주문은 가격이 필요합니다")
        
        asyncio.create_task(
            _monitor_limit_order(order.id, order.symbol, order.side, quantity, price, user_id)
        )
        logger.info(f"⏳ 지정가 모니터링 시작: ID={order.id}, Target=${price}")
    
    return order


def _fill_order(session: Session, order: Order, price: Decimal, quantity: Decimal):
    """
    주문 체결 처리 (수수료 없음)
    
    Args:
        session: 데이터베이스 세션
        order: 주문 객체
        price: 체결 가격
        quantity: 체결 수량
    """
    
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
            total_cost = price * quantity  # 수수료 없음
            
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
            proceeds = price * quantity  # 수수료 없음
            profit = (price - position.average_price) * quantity
            
            account.usdt_balance += proceeds
            account.total_profit += profit
            
            logger.info(f"💸 매도 체결: {quantity} {order.symbol} @ ${price} (손익: ${profit})")
        
        # 주문 상태 업데이트
        order.filled_quantity = quantity
        order.average_price = price
        order.status = OrderStatus.FILLED
        order.updated_at = datetime.utcnow()
        
        # 거래 내역 기록 (수수료 0)
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
    """
    지정가 주문 모니터링
    """
    from app.core.database import engine
    
    max_duration = 24 * 3600  # 24시간
    check_interval = 2  # 2초
    elapsed_time = 0
    last_trade_id = None
    
    logger.info(f"⏳ 지정가 모니터링 시작: {side} {quantity} {symbol} @ ${target_price}")
    
    try:
        while elapsed_time < max_duration:
            try:
                # 최근 거래 조회
                trades = await get_recent_trades(symbol, limit=50)
                
                if trades:
                    if last_trade_id:
                        trades = [t for t in trades if t['id'] > last_trade_id]
                    
                    if trades:
                        last_trade_id = max(t['id'] for t in trades)
                    
                    # 거래 확인
                    for trade in trades:
                        trade_price = Decimal(str(trade['price']))
                        
                        should_fill = False
                        
                        # 매수: 시장가가 목표가 이하로 떨어지면 체결
                        if side == OrderSide.BUY and trade_price <= target_price:
                            should_fill = True
                            logger.info(f"💰 매수 조건 충족: ${trade_price} <= ${target_price}")
                        
                        # 매도: 시장가가 목표가 이상으로 올라가면 체결
                        elif side == OrderSide.SELL and trade_price >= target_price:
                            should_fill = True
                            logger.info(f"💸 매도 조건 충족: ${trade_price} >= ${target_price}")
                        
                        # 체결 처리
                        if should_fill:
                            with Session(engine) as session:
                                order = session.exec(
                                    select(Order).where(Order.id == order_id)
                                ).first()
                                
                                if order and order.status == OrderStatus.PENDING:
                                    _fill_order(session, order, target_price, quantity)
                                    logger.info(f"✅ 지정가 체결: Order ID={order_id}")
                                    return
                
                await asyncio.sleep(check_interval)
                elapsed_time += check_interval
                
            except Exception as e:
                logger.error(f"❌ 모니터링 오류: {e}")
                await asyncio.sleep(check_interval)
                elapsed_time += check_interval
        
        # 만료 처리
        with Session(engine) as session:
            order = session.exec(
                select(Order).where(Order.id == order_id)
            ).first()
            
            if order and order.status == OrderStatus.PENDING:
                order.status = OrderStatus.EXPIRED
                order.updated_at = datetime.utcnow()
                session.add(order)
                session.commit()
                logger.info(f"⏰ 주문 만료: Order ID={order_id}")
                
    except Exception as e:
        logger.error(f"❌ 모니터링 실패: {e}")


def get_user_orders(session: Session, user_id: int, limit: int = 50) -> List[Order]:
    """
    사용자 주문 목록 조회
    """
    orders = session.exec(
        select(Order)
        .where(Order.user_id == user_id)
        .order_by(Order.created_at.desc())
        .limit(limit)
    ).all()
    
    return orders


def cancel_order(session: Session, order_id: int, user_id: int) -> Order:
    """
    주문 취소
    """
    order = session.exec(
        select(Order).where(
            Order.id == order_id,
            Order.user_id == user_id
        )
    ).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="주문을 찾을 수 없습니다")
    
    if order.status != OrderStatus.PENDING:
        raise HTTPException(status_code=400, detail="대기 중인 주문만 취소할 수 있습니다")
    
    order.status = OrderStatus.CANCELLED
    order.updated_at = datetime.utcnow()
    
    session.add(order)
    session.commit()
    session.refresh(order)
    
    logger.info(f"❌ 주문 취소: Order ID={order_id}")
    
    return order