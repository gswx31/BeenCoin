"""
Centralized Price Engine
- ONE WebSocket per symbol
- Checks ALL pending limit/stop orders on each price tick
- Checks ALL active price alerts on each tick
- Updates position current_value periodically
- Broadcasts prices to connected frontend clients
"""
import asyncio
import json
from decimal import Decimal
from datetime import datetime
from typing import Dict, Set, Callable, Optional
from collections import defaultdict
from sqlmodel import Session, select
from app.core.database import engine
from app.core.config import settings
from app.models.database import Order, Position, TradingAccount, PriceAlert, TransactionHistory
from app.services.fee_service import calculate_fee, update_trading_volume
from app.services.order_validator import round_price

POSITION_UPDATE_INTERVAL = 10  # seconds


class PriceEngine:
    def __init__(self):
        self._running = False
        self._tasks: Dict[str, asyncio.Task] = {}
        self._latest_prices: Dict[str, Decimal] = {}
        self._ws_subscribers: Dict[str, Set] = defaultdict(set)
        self._alert_callbacks: list = []

    @property
    def latest_prices(self):
        return dict(self._latest_prices)

    def get_price(self, symbol: str) -> Optional[Decimal]:
        return self._latest_prices.get(symbol)

    def subscribe(self, symbol: str, ws):
        self._ws_subscribers[symbol].add(ws)

    def unsubscribe(self, symbol: str, ws):
        self._ws_subscribers[symbol].discard(ws)

    def on_alert_trigger(self, callback: Callable):
        self._alert_callbacks.append(callback)

    # -- Lifecycle --
    async def start(self):
        if self._running:
            return
        self._running = True
        for symbol in settings.SUPPORTED_SYMBOLS:
            self._tasks[symbol] = asyncio.create_task(self._monitor_symbol(symbol))
        self._tasks['_position_updater'] = asyncio.create_task(self._position_update_loop())
        print(f"[PriceEngine] Started monitoring {settings.SUPPORTED_SYMBOLS}")

    async def stop(self):
        self._running = False
        for task in self._tasks.values():
            task.cancel()
        self._tasks.clear()
        print("[PriceEngine] Stopped")

    # -- Core: per-symbol WebSocket loop --
    async def _monitor_symbol(self, symbol: str):
        from app.services.binance_service import get_client

        while self._running:
            try:
                client = await get_client()
                from binance import BinanceSocketManager
                bsm = BinanceSocketManager(client)
                ts = bsm.trade_socket(symbol)
                async with ts as tscm:
                    while self._running:
                        res = await tscm.recv()
                        if 'p' not in res:
                            continue
                        price = Decimal(res['p'])
                        self._latest_prices[symbol] = price

                        await self._broadcast(symbol, price)
                        await self._check_orders(symbol, price)
                        await self._check_price_alerts(symbol, price)

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[PriceEngine] {symbol} WS error: {e}, reconnecting in 5s...")
                await asyncio.sleep(5)

    async def _broadcast(self, symbol: str, price: Decimal):
        dead = set()
        msg = json.dumps({"symbol": symbol, "price": str(price)})
        for ws in self._ws_subscribers[symbol]:
            try:
                await ws.send_text(msg)
            except Exception:
                dead.add(ws)
        self._ws_subscribers[symbol] -= dead

    # -- Order Matching (Limit + Stop-Loss + Take-Profit) --
    async def _check_orders(self, symbol: str, current_price: Decimal):
        with Session(engine) as session:
            pending_orders = session.exec(
                select(Order).where(
                    Order.symbol == symbol,
                    Order.order_status == 'PENDING',
                )
            ).all()

            for order in pending_orders:
                should_fill = False
                fill_price = current_price

                if order.order_type == 'LIMIT':
                    # Limit BUY: fill when price <= limit price, at limit price (maker)
                    # Limit SELL: fill when price >= limit price, at limit price (maker)
                    if order.side == 'BUY' and current_price <= order.price:
                        fill_price = order.price  # Limit orders fill at limit price
                        should_fill = True
                    elif order.side == 'SELL' and current_price >= order.price:
                        fill_price = order.price
                        should_fill = True

                elif order.order_type == 'STOP_LOSS_LIMIT':
                    # Triggered when price crosses stop_price, then becomes limit at order.price
                    if order.side == 'SELL' and current_price <= order.stop_price:
                        fill_price = order.price if order.price and current_price >= order.price else current_price
                        should_fill = True
                    elif order.side == 'BUY' and current_price >= order.stop_price:
                        fill_price = order.price if order.price and current_price <= order.price else current_price
                        should_fill = True

                elif order.order_type == 'TAKE_PROFIT_LIMIT':
                    # Triggered when price reaches profit target
                    if order.side == 'SELL' and current_price >= order.stop_price:
                        fill_price = order.price if order.price and current_price >= order.price else current_price
                        should_fill = True
                    elif order.side == 'BUY' and current_price <= order.stop_price:
                        fill_price = order.price if order.price and current_price <= order.price else current_price
                        should_fill = True

                if should_fill:
                    try:
                        self._execute_engine_fill(session, order, fill_price)
                        print(f"[PriceEngine] Filled #{order.id}: {order.side} {order.quantity} {order.symbol} @ {fill_price}")
                    except Exception as e:
                        print(f"[PriceEngine] Fill failed #{order.id}: {e}")
                        order.order_status = 'CANCELLED'
                        order.updated_at = datetime.utcnow()
                        session.add(order)
                        session.commit()

    def _execute_engine_fill(self, session: Session, order: Order, fill_price: Decimal):
        """Fill order via engine (used for limit/stop orders)."""
        account = session.exec(
            select(TradingAccount).where(TradingAccount.user_id == order.user_id)
        ).first()
        if not account:
            return

        qty = order.quantity - order.filled_quantity
        is_maker = order.order_type == 'LIMIT'  # Limit = maker, Stop = taker
        fee, fee_rate, fee_asset, _ = calculate_fee(fill_price, qty, is_maker, account)

        # Use shared fill logic from order_service
        from app.services.order_service import _execute_fill
        _execute_fill(session, order, account, qty, fill_price, fee, fee_asset, is_maker)

    # -- Price Alert Matching --
    async def _check_price_alerts(self, symbol: str, current_price: Decimal):
        with Session(engine) as session:
            alerts = session.exec(
                select(PriceAlert).where(
                    PriceAlert.symbol == symbol,
                    PriceAlert.is_active == True,
                )
            ).all()

            for alert in alerts:
                triggered = False
                if alert.condition == 'ABOVE' and current_price >= alert.target_price:
                    triggered = True
                elif alert.condition == 'BELOW' and current_price <= alert.target_price:
                    triggered = True

                if triggered:
                    alert.is_active = False
                    alert.triggered_at = datetime.utcnow()
                    session.add(alert)
                    session.commit()
                    print(f"[PriceEngine] Alert #{alert.id}: {symbol} {alert.condition} {alert.target_price}")

                    for cb in self._alert_callbacks:
                        try:
                            await cb(alert, current_price)
                        except Exception as e:
                            print(f"[PriceEngine] Alert cb error: {e}")

    # -- Periodic Position Value Update --
    async def _position_update_loop(self):
        while self._running:
            await asyncio.sleep(POSITION_UPDATE_INTERVAL)
            try:
                with Session(engine) as session:
                    positions = session.exec(select(Position)).all()
                    for pos in positions:
                        price = self._latest_prices.get(pos.symbol)
                        if price and pos.quantity > 0:
                            pos.current_value = pos.quantity * price
                            pos.unrealized_profit = pos.quantity * (price - pos.average_price)
                            session.add(pos)
                    session.commit()
            except Exception as e:
                print(f"[PriceEngine] Position update error: {e}")


# Singleton
price_engine = PriceEngine()
