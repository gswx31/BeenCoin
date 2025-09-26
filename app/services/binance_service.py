# app/services/binance_service.py - 개선된 버전
from binance.client import AsyncClient
from app.core.config import settings
from fastapi import HTTPException
import asyncio
from typing import Callable, Dict, List
from decimal import Decimal
import aiohttp
import json
from datetime import datetime, timedelta

async_client = AsyncClient(settings.BINANCE_API_KEY, settings.BINANCE_API_SECRET)

async def get_current_price(symbol: str) -> Decimal:
    try:
        ticker = await async_client.get_symbol_ticker(symbol=symbol)
        return Decimal(ticker['price'])
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Binance API error: {str(e)}")

async def get_multiple_prices(symbols: List[str]) -> Dict[str, Decimal]:
    """여러 코인의 현재 가격을 한번에 조회"""
    prices = {}
    for symbol in symbols:
        try:
            price = await get_current_price(symbol)
            prices[symbol] = float(price)
        except:
            prices[symbol] = 0.0
    return prices

async def get_historical_data(symbol: str, interval: str = "1h", limit: int = 24):
    """과거 차트 데이터 조회"""
    try:
        klines = await async_client.get_klines(
            symbol=symbol,
            interval=interval,
            limit=limit
        )
        
        historical_data = []
        for kline in klines:
            historical_data.append({
                "time": kline[0] / 1000,  # Unix timestamp
                "open": float(kline[1]),
                "high": float(kline[2]), 
                "low": float(kline[3]),
                "close": float(kline[4]),
                "volume": float(kline[5])
            })
        return historical_data
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Historical data error: {str(e)}")

async def get_24h_ticker(symbol: str):
    """24시간 티커 정보"""
    try:
        ticker = await async_client.get_24hr_ticker(symbol=symbol)
        return {
            "symbol": symbol,
            "priceChange": float(ticker['priceChange']),
            "priceChangePercent": float(ticker['priceChangePercent']),
            "volume": float(ticker['volume']),
            "quoteVolume": float(ticker['quoteVolume']),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))