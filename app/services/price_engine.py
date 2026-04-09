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
from app.models.database import Order, Position, TradingAccount, PriceAlert
from app.services.fee_service import calculate_fee

POSITION_UPDATE_INTERVAL = 10


class PriceEngine:
    def __init__(self):
        self._running = False
        self._tasks: Dict[str, asyncio.Task] = {}
        self._latest_prices: Dict[str, Decimal] = {}
        self._ws_subscribers: Dict[str, Set] = defaultdict(set)
        self._alert_callbacks: list = []
        self._fill_lock = asyncio.Lock()  # prevent concurrent fills

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

    async def _monitor_symbol(self, symbol: str):
        from app.services.binance_service import get_client

        tick_count = 0

        while self._running:
            try:
                client = await get_client()
                from binance import BinanceSocketManager
                bsm = BinanceSocketManager(client)
                ts = bsm.kline_socket(symbol, interval='1s')  # 1s kline = less data than trade stream
                async with ts as tscm:
                    while self._running:
                        res = await tscm.recv()
                        k = res.get('k', {})
                        price_str = k.get('c')  # close price
                        if not price_str:
                            continue
                        price = Decimal(price_str)
                        self._latest_prices[symbol] = price

                        # Broadcast every tick
                        await self._broadcast(symbol, price)

                        # Check orders/alerts every 5 ticks to avoid blocking
                        tick_count += 1
                        if tick_count % 5 == 0:
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

    async def _check_orders(self, symbol: str, current_price: Decimal):
        async with self._fill_lock:  # prevent concurrent fills on same order
            with Session(engine) as session:
                pending_orders = session.exec(
                    select(Order).where(
                        Order.symbol == symbol,
                        Order.order_status == 'PENDING',
                    )
                ).all()

                for order in pending_orders:
                    fill_result = self._should_fill(order, current_price)
                    if fill_result is None:
                        continue

                    fill_price = fill_result
                    try:
                        self._execute_engine_fill(session, order, fill_price)
                        print(f"[PriceEngine] Filled #{order.id}: {order.side} {order.quantity} {order.symbol} @ {fill_price}")
                    except Exception as e:
                        print(f"[PriceEngine] Fill failed #{order.id}: {e}")
                        session.rollback()
                        try:
                            order = session.exec(select(Order).where(Order.id == order.id)).first()
                            if order and order.order_status == 'PENDING':
                                order.order_status = 'CANCELLED'
                                order.updated_at = datetime.utcnow()
                                session.add(order)
                                session.commit()
                        except Exception:
                            pass

    def _should_fill(self, order: Order, current_price: Decimal) -> Optional[Decimal]:
        """Return fill price if order should be filled, None otherwise."""

        if order.order_type == 'LIMIT':
            # Limit BUY: fill at limit price when market <= limit
            if order.side == 'BUY' and current_price <= order.price:
                return order.price
            # Limit SELL: fill at limit price when market >= limit
            if order.side == 'SELL' and current_price >= order.price:
                return order.price

        elif order.order_type == 'STOP_LOSS_LIMIT':
            # Stop-Loss SELL: triggered when price drops to stop_price
            # Then fills at limit price (order.price) — but only if market is still >= limit
            if order.side == 'SELL' and current_price <= order.stop_price:
                if order.price and current_price >= order.price:
                    return order.price  # fill at limit price
                return current_price  # market already below limit, fill at market

            # Stop-Loss BUY: triggered when price rises to stop_price
            if order.side == 'BUY' and current_price >= order.stop_price:
                if order.price and current_price <= order.price:
                    return order.price
                return current_price

        elif order.order_type == 'TAKE_PROFIT_LIMIT':
            # Take-Profit SELL: triggered when price rises to stop_price (profit target)
            if order.side == 'SELL' and current_price >= order.stop_price:
                if order.price and current_price >= order.price:
                    return order.price
                return current_price

            # Take-Profit BUY: triggered when price drops to stop_price
            if order.side == 'BUY' and current_price <= order.stop_price:
                if order.price and current_price <= order.price:
                    return order.price
                return current_price

        return None

    def _execute_engine_fill(self, session: Session, order: Order, fill_price: Decimal):
        """Fill order via engine — single atomic transaction."""
        # Re-check order status to prevent double fill
        fresh_order = session.exec(select(Order).where(Order.id == order.id)).first()
        if not fresh_order or fresh_order.order_status != 'PENDING':
            return

        account = session.exec(
            select(TradingAccount).where(TradingAccount.user_id == fresh_order.user_id)
        ).first()
        if not account:
            return

        qty = fresh_order.quantity - fresh_order.filled_quantity
        if qty <= Decimal('0'):
            return

        is_maker = fresh_order.order_type == 'LIMIT'
        fee, _, fee_asset, _ = calculate_fee(fill_price, qty, is_maker, account)

        from app.services.order_service import _apply_fill
        _apply_fill(session, fresh_order, account, qty, fill_price, fee, fee_asset, is_maker)
        session.commit()

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
                            if asyncio.iscoroutinefunction(cb):
                                await cb(alert, current_price)
                            else:
                                cb(alert, current_price)
                        except Exception as e:
                            print(f"[PriceEngine] Alert cb error: {e}")

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


price_engine = PriceEngine()
