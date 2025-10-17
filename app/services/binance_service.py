from binance.client import AsyncClient, BinanceSocketManager
from app.core.config import settings
from fastapi import HTTPException
import asyncio
from typing import Callable
from decimal import Decimal

async_client = AsyncClient(settings.BINANCE_API_KEY, settings.BINANCE_API_SECRET)

async def get_current_price(symbol: str) -> Decimal:
    try:
        ticker = await async_client.get_symbol_ticker(symbol=symbol)
        return Decimal(ticker['price'])
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Binance API error: {str(e)}")

async def monitor_limit_order(order_id: int, symbol: str, side: str, price: Decimal, quantity: Decimal, callback: Callable):
    try:
        async with BinanceSocketManager(async_client) as bsm:
            ts = bsm.trade_socket(symbol)
            async with ts as tscm:
                while True:
                    res = await tscm.recv()
                    if 'p' not in res:
                        continue
                    current_price = Decimal(res['p'])
                    if (side == 'BUY' and current_price <= price) or (side == 'SELL' and current_price >= price):
                        await callback(order_id, quantity, current_price)
                        break
    except Exception as e:
        print(f"WebSocket error for order {order_id}: {str(e)}")

async def execute_market_order(symbol: str, side: str, quantity: Decimal) -> Decimal:
    price = await get_current_price(symbol)
    return price
