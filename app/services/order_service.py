# app/services/order_service.py
from sqlmodel import Session, select
from app.models.database import (
    Order, SpotAccount, SpotPosition, Transaction,
    OrderSide, OrderStatus, TradingType
)
from app.services.binance_service import get_current_price, monitor_limit_order, execute_market_order
from decimal import Decimal
import asyncio
from app.schemas.order import OrderCreate
from fastapi import HTTPException, status
from app.core.config import settings
from typing import Optional, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# 수수료율 0.1%
FEE_RATE = Decimal('0.001')

async def create_order(session: Session, user_id: int, order_data: OrderCreate) -> Order:
    """주문 생성 및 처리 (현물만 지원)"""
    
    # 심볼 검증
    if order_data.symbol not in settings.SUPPORTED_SYMBOLS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"지원하지 않는 심볼입니다: {order_data.symbol}"
        )
    
    # 주문 생성
    order = Order(
        user_id=user_id,
        trading_type=TradingType.SPOT,  # 현물만 지원
        symbol=order_data.symbol,
        side=order_data.side,
        order_type=order_data.order_type,
        quantity=order_data.quantity,
        price=order_data.price,
        status=OrderStatus.PENDING,
        filled_quantity=Decimal('0')
    )
    session.add(order)
    session.commit()
    session.refresh(order)
    
    logger.info(
        f"📝 Order created: ID={order.id}, "
        f"Type={order.order_type}, Symbol={order.symbol}"
    )
    
    # 시장가 주문: 즉시 체결
    if order.order_type == 'MARKET':
        try:
            price = await execute_market_order(order.symbol, order.side, order.quantity)
            filled_qty = order.quantity
            fee = price * filled_qty * FEE_RATE
            
            # 주문 체결 처리
            update_order_filled(session, order.id, filled_qty, price)
            update_spot_position(session, user_id, order.symbol, order.side, filled_qty, price, fee)
            record_transaction(session, user_id, order.id, order.symbol, order.side, filled_qty, price, fee)
            
            logger.info(f"✅ Market order filled: ID={order.id}, Price=${price}")
            
        except Exception as e:
            logger.error(f"❌ Market order failed: {e}")
            order.status = OrderStatus.REJECTED
            session.add(order)
            session.commit()
            raise
    
    # 지정가 주문: 비동기 모니터링
    elif order.order_type == 'LIMIT':
        async def callback(order_id: int, quantity: Decimal, price: Decimal):
            """지정가 체결 콜백"""
            try:
                # 새 세션으로 처리
                from app.core.database import engine
                with Session(engine) as new_session:
                    filled_qty = quantity
                    fee = price * filled_qty * FEE_RATE
                    
                    update_order_filled(new_session, order_id, filled_qty, price)
                    update_spot_position(new_session, user_id, order.symbol, order.side, filled_qty, price, fee)
                    record_transaction(new_session, user_id, order_id, order.symbol, order.side, filled_qty, price, fee)
                    
                    logger.info(f"✅ Limit order filled: ID={order_id}, Price=${price}")
                    
            except Exception as e:
                logger.error(f"❌ Limit order callback failed: {e}")
        
        # 비동기 모니터링 시작
        asyncio.create_task(
            monitor_limit_order(order.id, order.symbol, order.side, order.quantity, order.price, callback)
        )
        
        logger.info(f"⏳ Limit order monitoring started: ID={order.id}")
    
    return order


def update_order_filled(session: Session, order_id: int, filled_qty: Decimal, avg_price: Decimal):
    """주문 체결 정보 업데이트"""
    order = session.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="주문을 찾을 수 없습니다.")
    
    order.filled_quantity += filled_qty
    order.average_price = avg_price
    
    # 전량 체결 여부 확인
    if order.filled_quantity >= order.quantity:
        order.status = OrderStatus.FILLED
    else:
        order.status = OrderStatus.PARTIALLY_FILLED
    
    order.updated_at = datetime.utcnow()
    session.add(order)
    session.commit()


def update_spot_position(
    session: Session,
    user_id: int,
    symbol: str,
    side: str,
    quantity: Decimal,
    price: Decimal,
    fee: Decimal
):
    """현물 포지션 업데이트"""
    
    # 현물 계정 조회
    account = session.exec(
        select(SpotAccount).where(SpotAccount.user_id == user_id)
    ).first()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="현물 계정을 찾을 수 없습니다."
        )
    
    # 포지션 조회 또는 생성
    position = session.exec(
        select(SpotPosition).where(
            SpotPosition.account_id == account.id,
            SpotPosition.symbol == symbol
        )
    ).first()
    
    if not position:
        position = SpotPosition(
            account_id=account.id,
            symbol=symbol,
            quantity=Decimal('0'),
            average_price=Decimal('0'),
            current_price=price,
            current_value=Decimal('0'),
            unrealized_profit=Decimal('0')
        )
        session.add(position)
    
    # 매수 처리
    if side == OrderSide.BUY:
        cost = price * quantity + fee
        
        if account.usdt_balance < cost:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"잔액 부족: 필요 ${cost}, 보유 ${account.usdt_balance}"
            )
        
        # 평균 단가 계산
        total_cost = (position.average_price * position.quantity) + (price * quantity)
        total_quantity = position.quantity + quantity
        position.average_price = total_cost / total_quantity if total_quantity > 0 else price
        position.quantity = total_quantity
        
        account.usdt_balance -= cost
        
        logger.info(
            f"💰 BUY executed: Symbol={symbol}, "
            f"Qty={quantity}, Price=${price}, Cost=${cost}"
        )
    
    # 매도 처리
    elif side == OrderSide.SELL:
        if position.quantity < quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"수량 부족: 필요 {quantity}, 보유 {position.quantity}"
            )
        
        position.quantity -= quantity
        net_proceeds = (price * quantity) - fee
        
        # 실현 손익 계산
        profit = (price - position.average_price) * quantity - fee
        account.total_profit += profit
        account.usdt_balance += net_proceeds
        
        logger.info(
            f"💸 SELL executed: Symbol={symbol}, "
            f"Qty={quantity}, Price=${price}, Profit=${profit}"
        )
    
    # 현재 시세로 평가
    try:
        current_price = asyncio.run(get_current_price(symbol))
        position.current_price = current_price
        position.current_value = position.quantity * current_price
        position.unrealized_profit = position.quantity * (current_price - position.average_price)
    except:
        # 가격 조회 실패시 주문 가격 사용
        position.current_price = price
        position.current_value = position.quantity * price
        position.unrealized_profit = position.quantity * (price - position.average_price)
    
    position.updated_at = datetime.utcnow()
    
    session.add(position)
    session.add(account)
    session.commit()


def record_transaction(
    session: Session,
    user_id: int,
    order_id: Optional[int],
    symbol: str,
    side: str,
    quantity: Decimal,
    price: Decimal,
    fee: Decimal
):
    """거래 내역 기록"""
    transaction = Transaction(
        user_id=user_id,
        order_id=order_id,
        trading_type=TradingType.SPOT,
        symbol=symbol,
        side=side,
        quantity=quantity,
        price=price,
        fee=fee,
        timestamp=datetime.utcnow()
    )
    session.add(transaction)
    session.commit()
    
    logger.info(f"📊 Transaction recorded: Order={order_id}, {side} {quantity} {symbol}")


def get_user_orders(
    session: Session,
    user_id: int,
    limit: int = 100,
    status_filter: str = None
) -> List[Order]:
    """사용자 주문 내역 조회"""
    query = select(Order).where(Order.user_id == user_id)
    
    if status_filter:
        query = query.where(Order.status == status_filter)
    
    query = query.order_by(Order.created_at.desc()).limit(limit)
    
    return session.exec(query).all()


def get_account_summary(session: Session, user_id: int) -> dict:
    """현물 계정 요약 정보 조회"""
    account = session.exec(
        select(SpotAccount).where(SpotAccount.user_id == user_id)
    ).first()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="현물 계정을 찾을 수 없습니다."
        )
    
    # 모든 포지션 조회
    positions = session.exec(
        select(SpotPosition).where(SpotPosition.account_id == account.id)
    ).all()
    
    # 포지션 현재가 업데이트
    for pos in positions:
        if pos.quantity > 0:
            try:
                current_price = asyncio.run(get_current_price(pos.symbol))
                pos.current_price = current_price
                pos.current_value = pos.quantity * current_price
                pos.unrealized_profit = pos.quantity * (current_price - pos.average_price)
                session.add(pos)
            except:
                pass
    
    session.commit()
    
    # 총 자산 가치 계산
    total_value = account.usdt_balance + sum(p.current_value for p in positions)
    
    # 수익률 계산
    initial_balance = Decimal('1000000.00')  # 초기 자본
    if initial_balance > 0:
        profit_rate = ((total_value - initial_balance) / initial_balance) * 100
    else:
        profit_rate = Decimal('0')
    
    return {
        "balance": account.usdt_balance,
        "total_profit": account.total_profit,
        "positions": [
            {
                "symbol": p.symbol,
                "quantity": p.quantity,
                "average_price": p.average_price,
                "current_price": p.current_price,
                "current_value": p.current_value,
                "unrealized_profit": p.unrealized_profit
            }
            for p in positions if p.quantity > 0
        ],
        "profit_rate": profit_rate,
        "total_value": total_value
    }


def get_transaction_history(
    session: Session,
    user_id: int,
    limit: int = 100
) -> List[Transaction]:
    """거래 내역 조회"""
    transactions = session.exec(
        select(Transaction)
        .where(Transaction.user_id == user_id)
        .order_by(Transaction.timestamp.desc())
        .limit(limit)
    ).all()
    
    return transactions