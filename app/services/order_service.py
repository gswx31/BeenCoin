from sqlmodel import Session, select
from app.models.database import Order, Position, TradingAccount, TransactionHistory
from app.services.binance_service import get_current_price, monitor_limit_order, execute_market_order
from decimal import Decimal
import asyncio
from app.schemas.order import OrderCreate
from fastapi import HTTPException
from app.core.config import settings
from typing import Optional, List
from datetime import datetime

FEE_RATE = Decimal('0.001')

async def create_order(session: Session, user_id: str, order_data: OrderCreate) -> Order:
    if order_data.symbol not in settings.SUPPORTED_SYMBOLS:
        raise HTTPException(status_code=400, detail="Unsupported symbol")
    
    order = Order(user_id=user_id, **order_data.dict())
    session.add(order)
    session.commit()
    session.refresh(order)
    
    if order.order_type == 'MARKET':
        price = await execute_market_order(order.symbol, order.side, order.quantity)
        filled_qty = order.quantity
        fee = price * filled_qty * FEE_RATE
        update_order_filled(session, order.id, filled_qty, price)
        update_position(session, user_id, order.symbol, order.side, filled_qty, price, fee)
        record_transaction(session, user_id, order.id, order.symbol, order.side, filled_qty, price, fee)
    elif order.order_type == 'LIMIT':
        async def callback(order_id: int, quantity: Decimal, price: Decimal):
            with session.begin():
                filled_qty = quantity
                fee = price * filled_qty * FEE_RATE
                update_order_filled(session, order_id, filled_qty, price)
                update_position(session, user_id, order.symbol, order.side, filled_qty, price, fee)
                record_transaction(session, user_id, order_id, order.symbol, order.side, filled_qty, price, fee)
        asyncio.create_task(monitor_limit_order(order.id, order.symbol, order.side, order.price, order.quantity, callback))
    
    return order

def update_order_filled(session: Session, order_id: int, filled_qty: Decimal, price: Decimal):
    order = session.exec(select(Order).where(Order.id == order_id)).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    order.filled_quantity += filled_qty
    order.price = price if order.price is None else order.price
    order.order_status = 'FILLED' if order.filled_quantity >= order.quantity else 'PARTIALLY_FILLED'
    order.updated_at = datetime.utcnow()
    session.add(order)
    session.commit()

def update_position(session: Session, user_id: str, symbol: str, side: str, quantity: Decimal, price: Decimal, fee: Decimal):
    account = session.exec(select(TradingAccount).where(TradingAccount.user_id == user_id)).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    position = session.exec(select(Position).where(Position.account_id == account.id, Position.symbol == symbol)).first()
    
    if not position:
        position = Position(account_id=account.id, symbol=symbol, quantity=Decimal('0'), average_price=Decimal('0'), current_value=Decimal('0'), unrealized_profit=Decimal('0'))
        session.add(position)
        session.commit()
        session.refresh(position)
    
    cost = price * quantity
    net_cost = cost + fee if side == 'BUY' else cost - fee
    
    if side == 'BUY':
        if account.balance < net_cost:
            raise HTTPException(status_code=400, detail="Insufficient balance")
        new_qty = position.quantity + quantity
        new_avg_price = ((position.average_price * position.quantity) + cost) / new_qty if new_qty > 0 else Decimal('0')
        position.quantity = new_qty
        position.average_price = new_avg_price
        account.balance -= net_cost
    elif side == 'SELL':
        if position.quantity < quantity:
            raise HTTPException(status_code=400, detail="Insufficient quantity to sell")
        position.quantity -= quantity
        profit = (price - position.average_price) * quantity - fee
        account.total_profit += profit
        account.balance += net_cost
    
    current_price = asyncio.run(get_current_price(symbol))
    position.current_value = position.quantity * current_price
    position.unrealized_profit = position.quantity * (current_price - position.average_price)
    session.add(position)
    session.add(account)
    session.commit()

def record_transaction(session: Session, user_id: str, order_id: Optional[int], symbol: str, side: str, quantity: Decimal, price: Decimal, fee: Decimal):
    transaction = TransactionHistory(user_id=user_id, order_id=order_id, symbol=symbol, side=side, quantity=quantity, price=price, fee=fee)
    session.add(transaction)
    session.commit()

def get_user_orders(session: Session, user_id: int) -> List[Order]:
    return session.exec(select(Order).where(Order.user_id == user_id).order_by(Order.created_at.desc())).all()

def get_account_summary(session: Session, user_id: int) -> dict:
    account = session.exec(select(TradingAccount).where(TradingAccount.user_id == user_id)).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    positions = session.exec(select(Position).where(Position.account_id == account.id)).all()
    total_value = account.balance + sum(p.current_value for p in positions)
    initial_balance = Decimal(str(settings.INITIAL_BALANCE))
    profit_rate = ((total_value - initial_balance) / initial_balance * 100) if initial_balance > 0 else Decimal('0')
    return {
        "balance": account.balance,
        "total_profit": account.total_profit,
        "positions": [p.dict() for p in positions],
        "profit_rate": profit_rate,
        "total_value": total_value
    }

def get_transaction_history(session: Session, user_id: int) -> List[TransactionHistory]:
    return session.exec(select(TransactionHistory).where(TransactionHistory.user_id == user_id).order_by(TransactionHistory.timestamp.desc())).all()
