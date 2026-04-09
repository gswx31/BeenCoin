from binance import AsyncClient, BinanceSocketManager
from app.core.config import settings
from fastapi import HTTPException
from decimal import Decimal
import asyncio
from typing import Optional

_client: Optional[AsyncClient] = None
_client_lock = asyncio.Lock()


async def get_client() -> AsyncClient:
    global _client
    if _client is not None:
        return _client
    async with _client_lock:
        # Double-check after acquiring lock
        if _client is not None:
            return _client
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
