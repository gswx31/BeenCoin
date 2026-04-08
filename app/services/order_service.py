from sqlmodel import Session, select
from app.models.database import Order, Position, TradingAccount, TransactionHistory, PriceAlert
from app.services.price_engine import price_engine
from app.services.binance_service import get_current_price
from app.services.fee_service import calculate_fee, update_trading_volume, get_fee_info
from app.services.order_validator import (
    validate_quantity, validate_price, validate_min_notional,
    simulate_slippage, round_price, get_symbol_rules,
)
from decimal import Decimal
from app.schemas.order import OrderCreate
from fastapi import HTTPException
from app.core.config import settings
from typing import Optional, List
from datetime import datetime


async def create_order(session: Session, user_id: int, order_data: OrderCreate) -> Order:
    if order_data.symbol not in settings.SUPPORTED_SYMBOLS:
        raise HTTPException(status_code=400, detail="Unsupported symbol")

    account = session.exec(
        select(TradingAccount).where(TradingAccount.user_id == user_id)
    ).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    # -- Binance-style validation --
    validate_quantity(order_data.symbol, order_data.quantity)

    if order_data.price is not None:
        validate_price(order_data.symbol, order_data.price)

    # Estimate price for notional check
    if order_data.order_type == 'MARKET':
        est_price = price_engine.get_price(order_data.symbol)
        if est_price is None:
            est_price = await get_current_price(order_data.symbol)
    else:
        est_price = order_data.price

    if est_price:
        validate_min_notional(order_data.symbol, est_price, order_data.quantity)

    # -- Pre-validate balance / position --
    if order_data.side == 'BUY':
        is_maker = order_data.order_type != 'MARKET'
        est_fee, _, _, _ = calculate_fee(est_price, order_data.quantity, is_maker, account)
        est_cost = est_price * order_data.quantity + est_fee
        if account.balance < est_cost:
            raise HTTPException(status_code=400, detail="Insufficient balance")

    if order_data.side == 'SELL':
        position = session.exec(
            select(Position).where(
                Position.account_id == account.id,
                Position.symbol == order_data.symbol,
            )
        ).first()
        if not position or position.quantity < order_data.quantity:
            raise HTTPException(status_code=400, detail="Insufficient quantity to sell")

    # -- Create order --
    order = Order(
        user_id=user_id,
        symbol=order_data.symbol,
        side=order_data.side,
        order_type=order_data.order_type,
        quantity=order_data.quantity,
        price=order_data.price,
        stop_price=order_data.stop_price,
    )
    session.add(order)
    session.commit()
    session.refresh(order)

    # -- Execute market orders immediately --
    if order.order_type == 'MARKET':
        current = price_engine.get_price(order.symbol) or await get_current_price(order.symbol)
        # Apply slippage
        fill_price = simulate_slippage(current, order.side)
        fill_price = round_price(order.symbol, fill_price)

        is_maker = False  # market orders are always taker
        fee, fee_rate, fee_asset, _ = calculate_fee(fill_price, order.quantity, is_maker, account)

        _execute_fill(session, order, account, order.quantity, fill_price, fee, fee_asset, is_maker)
        session.refresh(order)

    # LIMIT / STOP orders stay PENDING — PriceEngine fills them

    return order


def _execute_fill(
    session: Session, order: Order, account: TradingAccount,
    qty: Decimal, fill_price: Decimal, fee: Decimal, fee_asset: str, is_maker: bool,
):
    """Core fill logic used by both order_service and price_engine."""
    notional = fill_price * qty

    # -- Update order --
    order.filled_quantity += qty
    order.filled_price = fill_price
    order.commission += fee
    order.commission_asset = fee_asset
    order.order_status = 'FILLED' if order.filled_quantity >= order.quantity else 'PARTIALLY_FILLED'
    order.updated_at = datetime.utcnow()
    session.add(order)

    # -- Update position --
    position = session.exec(
        select(Position).where(Position.account_id == account.id, Position.symbol == order.symbol)
    ).first()
    if not position:
        position = Position(
            account_id=account.id, symbol=order.symbol,
            quantity=Decimal('0'), average_price=Decimal('0'),
            current_value=Decimal('0'), unrealized_profit=Decimal('0'),
            total_cost=Decimal('0'),
        )
        session.add(position)
        session.flush()

    realized_pnl = Decimal('0')

    if order.side == 'BUY':
        total_buy_cost = notional + fee  # fee included in cost basis
        if account.balance < total_buy_cost:
            order.order_status = 'CANCELLED'
            session.add(order)
            session.commit()
            return

        new_qty = position.quantity + qty
        # Average price includes fee: total_cost / total_qty
        position.total_cost += total_buy_cost
        position.quantity = new_qty
        position.average_price = position.total_cost / new_qty if new_qty > 0 else Decimal('0')
        account.balance -= total_buy_cost

    elif order.side == 'SELL':
        if position.quantity < qty:
            order.order_status = 'CANCELLED'
            session.add(order)
            session.commit()
            return

        # Realized PnL = (sell_price * qty - fee) - (avg_cost * qty)
        sell_proceeds = notional - fee
        cost_basis = position.average_price * qty
        realized_pnl = sell_proceeds - cost_basis
        account.total_profit += realized_pnl
        account.balance += sell_proceeds

        position.quantity -= qty
        position.total_cost = position.average_price * position.quantity if position.quantity > 0 else Decimal('0')

    # Update current value
    position.current_value = position.quantity * fill_price
    position.unrealized_profit = position.quantity * (fill_price - position.average_price) if position.quantity > 0 else Decimal('0')

    if position.quantity <= Decimal('0'):
        session.delete(position)
    else:
        session.add(position)

    # Update trading volume for fee tier
    update_trading_volume(session, account, notional)
    session.add(account)

    # -- Record transaction --
    tx = TransactionHistory(
        user_id=order.user_id, order_id=order.id, symbol=order.symbol,
        side=order.side, quantity=qty, price=fill_price,
        fee=fee, fee_asset=fee_asset, is_maker=is_maker,
        realized_pnl=realized_pnl,
    )
    session.add(tx)
    session.commit()


def cancel_order(session: Session, user_id: int, order_id: int) -> Order:
    order = session.exec(
        select(Order).where(Order.id == order_id, Order.user_id == user_id)
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.order_status != 'PENDING':
        raise HTTPException(status_code=400, detail="Only pending orders can be cancelled")
    order.order_status = 'CANCELLED'
    order.updated_at = datetime.utcnow()
    session.add(order)
    session.commit()
    session.refresh(order)
    return order


# -- Query helpers --

def get_user_orders(session: Session, user_id: int) -> List[Order]:
    return session.exec(
        select(Order).where(Order.user_id == user_id).order_by(Order.created_at.desc())
    ).all()


def get_account_summary(session: Session, user_id: int) -> dict:
    account = session.exec(
        select(TradingAccount).where(TradingAccount.user_id == user_id)
    ).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    positions = session.exec(
        select(Position).where(Position.account_id == account.id)
    ).all()
    total_value = account.balance + sum(p.current_value for p in positions)
    initial = Decimal(str(settings.INITIAL_BALANCE))
    profit_rate = ((total_value - initial) / initial * 100) if initial > 0 else Decimal('0')
    fee_info = get_fee_info(account)
    return {
        "balance": account.balance,
        "total_profit": account.total_profit,
        "positions": [p.dict() for p in positions],
        "profit_rate": profit_rate,
        "total_value": total_value,
        "fee_info": fee_info,
    }


def get_transaction_history(session: Session, user_id: int) -> List[TransactionHistory]:
    return session.exec(
        select(TransactionHistory).where(TransactionHistory.user_id == user_id)
        .order_by(TransactionHistory.timestamp.desc())
    ).all()


def toggle_bnb_fee(session: Session, user_id: int, use_bnb: bool) -> dict:
    account = session.exec(
        select(TradingAccount).where(TradingAccount.user_id == user_id)
    ).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    account.use_bnb_fee = use_bnb
    session.add(account)
    session.commit()
    return get_fee_info(account)


# -- Price Alert helpers --

def create_price_alert(session: Session, user_id: int, symbol: str, target_price: Decimal, condition: str, memo: str = "") -> PriceAlert:
    if symbol not in settings.SUPPORTED_SYMBOLS:
        raise HTTPException(status_code=400, detail="Unsupported symbol")
    if condition not in ('ABOVE', 'BELOW'):
        raise HTTPException(status_code=400, detail="Condition must be ABOVE or BELOW")
    alert = PriceAlert(
        user_id=user_id, symbol=symbol,
        target_price=target_price, condition=condition, memo=memo,
    )
    session.add(alert)
    session.commit()
    session.refresh(alert)
    return alert


def get_user_alerts(session: Session, user_id: int) -> List[PriceAlert]:
    return session.exec(
        select(PriceAlert).where(PriceAlert.user_id == user_id)
        .order_by(PriceAlert.created_at.desc())
    ).all()


def delete_price_alert(session: Session, user_id: int, alert_id: int):
    alert = session.exec(
        select(PriceAlert).where(PriceAlert.id == alert_id, PriceAlert.user_id == user_id)
    ).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    session.delete(alert)
    session.commit()
