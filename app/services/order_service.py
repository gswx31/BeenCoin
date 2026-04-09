from sqlmodel import Session, select
from app.models.database import Order, Position, TradingAccount, TransactionHistory, PriceAlert
from app.services.price_engine import price_engine
from app.services.binance_service import get_current_price
from app.services.fee_service import calculate_fee, update_trading_volume, get_fee_info
from app.services.order_validator import (
    validate_quantity, validate_price, validate_min_notional,
    simulate_slippage, round_price,
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

    # -- Pre-validate balance / position BEFORE creating order --
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

    # -- Create order + execute in single transaction --
    order = Order(
        user_id=user_id,
        symbol=order_data.symbol,
        side=order_data.side,
        order_type=order_data.order_type,
        quantity=order_data.quantity,
        price=order_data.price,
        stop_price=order_data.stop_price,
    )

    if order.order_type == 'MARKET':
        current = price_engine.get_price(order.symbol) or await get_current_price(order.symbol)
        fill_price = simulate_slippage(current, order.side)
        fill_price = round_price(order.symbol, fill_price)
        is_maker = False
        fee, _, fee_asset, _ = calculate_fee(fill_price, order.quantity, is_maker, account)

        # All state changes in one commit
        session.add(order)
        session.flush()  # get order.id
        _apply_fill(session, order, account, order.quantity, fill_price, fee, fee_asset, is_maker)
        session.commit()
        session.refresh(order)
    else:
        # LIMIT / STOP orders stay PENDING
        session.add(order)
        session.commit()
        session.refresh(order)

    return order


def _apply_fill(
    session: Session, order: Order, account: TradingAccount,
    qty: Decimal, fill_price: Decimal, fee: Decimal, fee_asset: str, is_maker: bool,
):
    """
    Core fill logic — applies all state changes WITHOUT committing.
    Caller is responsible for session.commit().
    """
    notional = fill_price * qty

    # -- Update order --
    order.filled_quantity += qty
    order.filled_price = fill_price
    order.commission += fee
    order.commission_asset = fee_asset
    order.order_status = 'FILLED' if order.filled_quantity >= order.quantity else 'PARTIALLY_FILLED'
    order.updated_at = datetime.utcnow()
    session.add(order)

    # -- Get or create position --
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
        total_buy_cost = notional + fee
        # Balance already validated before this point, but double-check
        if account.balance < total_buy_cost:
            raise HTTPException(status_code=400, detail="Insufficient balance")

        new_qty = position.quantity + qty
        position.total_cost += total_buy_cost
        position.quantity = new_qty
        position.average_price = position.total_cost / new_qty if new_qty > 0 else Decimal('0')
        account.balance -= total_buy_cost

    elif order.side == 'SELL':
        if position.quantity < qty:
            raise HTTPException(status_code=400, detail="Insufficient quantity to sell")

        sell_proceeds = notional - fee
        cost_basis = position.average_price * qty
        realized_pnl = sell_proceeds - cost_basis
        account.total_profit += realized_pnl
        account.balance += sell_proceeds

        position.quantity -= qty
        # Reduce total_cost proportionally
        if position.quantity > Decimal('0'):
            position.total_cost = position.average_price * position.quantity
        else:
            position.total_cost = Decimal('0')

    # Update current value
    position.current_value = position.quantity * fill_price
    position.unrealized_profit = (
        position.quantity * (fill_price - position.average_price)
        if position.quantity > 0 else Decimal('0')
    )

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

    # -- Post-trade hooks (streak, achievements, missions) --
    _run_post_trade_hooks(session, order, notional, realized_pnl)


def _run_post_trade_hooks(session: Session, order: Order, notional: Decimal, realized_pnl: Decimal):
    """Run streak/achievement/mission updates. Errors here don't break the trade."""
    try:
        from app.services.analytics_service import update_streak
        from app.services.achievement_service import check_and_award
        from app.services.mission_service import progress_missions

        if order.side == 'SELL':
            update_streak(session, order.user_id, realized_pnl)

        check_and_award(session, order.user_id, {
            "trade_notional": float(notional),
            "trade_hour": datetime.utcnow().hour,
        })

        progress_missions(
            session, order.user_id,
            trade_symbol=order.symbol, trade_side=order.side,
            trade_notional=float(notional), realized_pnl=float(realized_pnl),
            order_type=order.order_type,
        )
    except Exception as e:
        print(f"[PostTrade] Hook error: {e}")


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


def _position_to_dict(p: Position) -> dict:
    return {
        "symbol": p.symbol,
        "quantity": p.quantity,
        "average_price": p.average_price,
        "current_value": p.current_value,
        "unrealized_profit": p.unrealized_profit,
        "total_cost": p.total_cost,
    }


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
    return {
        "balance": account.balance,
        "total_profit": account.total_profit,
        "positions": [_position_to_dict(p) for p in positions],
        "profit_rate": profit_rate,
        "total_value": total_value,
        "fee_info": get_fee_info(account),
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

def create_price_alert(session, user_id, symbol, target_price, condition, memo=""):
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


def get_user_alerts(session, user_id):
    return session.exec(
        select(PriceAlert).where(PriceAlert.user_id == user_id)
        .order_by(PriceAlert.created_at.desc())
    ).all()


def delete_price_alert(session, user_id, alert_id):
    alert = session.exec(
        select(PriceAlert).where(PriceAlert.id == alert_id, PriceAlert.user_id == user_id)
    ).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    session.delete(alert)
    session.commit()
