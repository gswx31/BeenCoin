from sqlmodel import Session, select
from app.models.database import Order, Position, TradingAccount
from app.services.binance_service import get_current_price, monitor_limit_order, execute_market_order
from decimal import Decimal
import asyncio

async def create_order(session: Session, user_id: int, order_data):
    order = Order(user_id=user_id, **order_data.dict())
    session.add(order)
    session.commit()
    session.refresh(order)
    
    if order.order_type == 'market':
        price = execute_market_order(order.symbol, order.side, order.quantity)
        update_order_filled(session, order.id, order.quantity, Decimal(str(price)))
        update_position(session, user_id, order.symbol, order.side, order.quantity, Decimal(str(price)))
    elif order.order_type == 'limit':
        async def callback(order_id, quantity, price):
            update_order_filled(session, order_id, Decimal(str(quantity)), Decimal(str(price)))
            update_position(session, user_id, order.symbol, order.side, Decimal(str(quantity)), Decimal(str(price)))
        asyncio.create_task(monitor_limit_order(order.id, order.symbol, order.side, float(order.price), float(order.quantity), callback))
    
    return order

def update_order_filled(session: Session, order_id: int, filled_qty: Decimal, price: Decimal):
    order = session.exec(select(Order).where(Order.id == order_id)).first()
    order.filled_quantity += filled_qty
    order.price = price if order.price is None else order.price
    order.order_status = 'filled' if order.filled_quantity == order.quantity else 'partially_filled'
    session.add(order)
    session.commit()

def update_position(session: Session, user_id: int, symbol: str, side: str, quantity: Decimal, price: Decimal):
    account = session.exec(select(TradingAccount).where(TradingAccount.user_id == user_id)).first()
    position = session.exec(select(Position).where(Position.account_id == account.id, Position.symbol == symbol)).first()
    
    if not position:
        position = Position(account_id=account.id, symbol=symbol, quantity=0, average_price=0, current_value=0)
        session.add(position)
    
    if side == 'buy':
        new_qty = position.quantity + quantity
        new_avg_price = (position.average_price * position.quantity + price * quantity) / new_qty if new_qty > 0 else 0
        position.quantity = new_qty
        position.average_price = new_avg_price
        account.balance -= price * quantity
    elif side == 'sell':
        if position.quantity < quantity:
            raise ValueError("Insufficient quantity to sell")
        position.quantity -= quantity
        profit = (price - position.average_price) * quantity
        account.total_profit += profit
        account.balance += price * quantity
    
    current_price = Decimal(str(asyncio.run(get_current_price(symbol))))
    position.current_value = position.quantity * current_price
    position.unrealized_profit = position.quantity * (current_price - position.average_price)
    session.add(position)
    session.add(account)
    session.commit()

def get_account_summary(session: Session, user_id: int) -> dict:
    account = session.exec(select(TradingAccount).where(TradingAccount.user_id == user_id)).first()
    positions = session.exec(select(Position).where(Position.account_id == account.id)).all()
    total_value = account.balance + sum(p.current_value for p in positions)
    initial_balance = Decimal(str(settings.INITIAL_BALANCE))
    profit_rate = ((total_value - initial_balance) / initial_balance * 100) if initial_balance > 0 else 0
    return {
        "balance": account.balance,
        "total_profit": account.total_profit,
        "positions": positions,
        "profit_rate": profit_rate
    }
