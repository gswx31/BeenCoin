# app/routers/market.py
"""
Market data routes
"""
from fastapi import APIRouter, Query, HTTPException, status
from typing import Optional, List
from app.services.binance_service import (
    get_current_price,
    get_ticker_24hr,
    get_orderbook,
    get_klines,
    get_recent_trades
)
from app.core.config import settings

router = APIRouter(tags=["Market Data"])

@router.get("/price/{symbol}")
async def get_price(symbol: str):
    """Get current price for a symbol"""
    
    if symbol not in settings.SUPPORTED_SYMBOLS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported symbol: {symbol}"
        )
    
    try:
        price = await get_current_price(symbol)
        return {
            "symbol": symbol,
            "price": price,
            "timestamp": "now"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )

@router.get("/ticker/{symbol}")
async def get_ticker(symbol: str):
    """Get 24hr ticker statistics"""
    
    if symbol not in settings.SUPPORTED_SYMBOLS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported symbol: {symbol}"
        )
    
    try:
        ticker = await get_ticker_24hr(symbol)
        return ticker
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )

@router.get("/orderbook/{symbol}")
async def get_depth(
    symbol: str,
    limit: int = Query(10, ge=5, le=100, description="Number of price levels")
):
    """Get order book depth"""
    
    if symbol not in settings.SUPPORTED_SYMBOLS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported symbol: {symbol}"
        )
    
    try:
        orderbook = await get_orderbook(symbol, limit)
        return orderbook
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )

@router.get("/klines/{symbol}")
async def get_candlesticks(
    symbol: str,
    interval: str = Query("1h", description="Kline interval"),
    limit: int = Query(100, ge=1, le=500, description="Number of klines")
):
    """Get candlestick data"""
    
    if symbol not in settings.SUPPORTED_SYMBOLS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported symbol: {symbol}"
        )
    
    valid_intervals = ["1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d", "3d", "1w", "1M"]
    if interval not in valid_intervals:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid interval. Valid intervals: {', '.join(valid_intervals)}"
        )
    
    try:
        klines = await get_klines(symbol, interval, limit)
        
        # Format klines for better readability
        formatted_klines = []
        for k in klines:
            formatted_klines.append({
                "open_time": k[0],
                "open": k[1],
                "high": k[2],
                "low": k[3],
                "close": k[4],
                "volume": k[5],
                "close_time": k[6],
                "quote_volume": k[7],
                "trades": k[8],
                "taker_buy_base": k[9],
                "taker_buy_quote": k[10]
            })
        
        return formatted_klines
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )

@router.get("/trades/{symbol}")
async def get_trades(
    symbol: str,
    limit: int = Query(100, ge=1, le=500, description="Number of trades")
):
    """Get recent trades"""
    
    if symbol not in settings.SUPPORTED_SYMBOLS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported symbol: {symbol}"
        )
    
    try:
        trades = await get_recent_trades(symbol, limit)
        return trades
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )

@router.get("/symbols")
async def get_supported_symbols():
    """Get list of supported trading symbols"""
    
    return {
        "symbols": settings.SUPPORTED_SYMBOLS,
        "count": len(settings.SUPPORTED_SYMBOLS)
    }