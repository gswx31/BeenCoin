from binance import AsyncClient, BinanceSocketManager
from app.core.config import settings
from fastapi import HTTPException
from decimal import Decimal
import asyncio
from typing import Callable, Optional

_client: Optional[AsyncClient] = None

async def get_client() -> AsyncClient:
    global _client
    if _client is None:
        _client = await AsyncClient.create(
            api_key=settings.BINANCE_API_KEY or "",
            api_secret=settings.BINANCE_API_SECRET or "",
        )
    return _client

async def close_client():
    global _client
    if _client:
        await _client.close_connection()
        _client = None

async def get_current_price(symbol: str) -> Decimal:
    try:
        client = await get_client()
        ticker = await client.get_symbol_ticker(symbol=symbol)
        return Decimal(ticker['price'])
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Binance API error: {str(e)}")

async def monitor_limit_order(order_id: int, symbol: str, side: str, target_price: Decimal, quantity: Decimal, callback: Callable):
    try:
        client = await get_client()
        bsm = BinanceSocketManager(client)
        ts = bsm.trade_socket(symbol)
        async with ts as tscm:
            while True:
                res = await tscm.recv()
                if 'p' not in res:
                    continue
                current_price = Decimal(res['p'])
                if (side == 'BUY' and current_price <= target_price) or \
                   (side == 'SELL' and current_price >= target_price):
                    await callback(order_id, quantity, current_price)
                    break
    except Exception as e:
        print(f"WebSocket error for order {order_id}: {str(e)}")

async def execute_market_order(symbol: str, side: str, quantity: Decimal) -> Decimal:
    return await get_current_price(symbol)
