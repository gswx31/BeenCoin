# app/services/binance_service.py
"""
Binance API service for market data
"""
import httpx
import logging
from typing import Dict, List, Optional
from app.core.config import settings
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

class BinanceService:
    """Binance API integration service"""
    
    BASE_URL = "https://api.binance.com"
    
    @staticmethod
    async def get_current_price(symbol: str) -> float:
        """
        Get current market price for a symbol
        
        Args:
            symbol: Trading pair symbol (e.g., "BTCUSDT")
        
        Returns:
            float: Current price
        
        Raises:
            HTTPException: If API call fails
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{BinanceService.BASE_URL}/api/v3/ticker/price",
                    params={"symbol": symbol}
                )
                
                if response.status_code != 200:
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail=f"Failed to fetch price for {symbol}"
                    )
                
                data = response.json()
                return float(data["price"])
        
        except httpx.RequestError as e:
            logger.error(f"Binance API request failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Market data service unavailable"
            )
    
    @staticmethod
    async def get_ticker_24hr(symbol: str) -> Dict:
        """
        Get 24hr ticker statistics
        
        Args:
            symbol: Trading pair symbol
        
        Returns:
            Dict: 24hr ticker data
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{BinanceService.BASE_URL}/api/v3/ticker/24hr",
                    params={"symbol": symbol}
                )
                
                if response.status_code != 200:
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail=f"Failed to fetch ticker for {symbol}"
                    )
                
                return response.json()
        
        except httpx.RequestError as e:
            logger.error(f"Binance API request failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Market data service unavailable"
            )
    
    @staticmethod
    async def get_orderbook(symbol: str, limit: int = 10) -> Dict:
        """
        Get order book depth
        
        Args:
            symbol: Trading pair symbol
            limit: Number of bids/asks to return
        
        Returns:
            Dict: Order book data
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{BinanceService.BASE_URL}/api/v3/depth",
                    params={"symbol": symbol, "limit": limit}
                )
                
                if response.status_code != 200:
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail=f"Failed to fetch orderbook for {symbol}"
                    )
                
                return response.json()
        
        except httpx.RequestError as e:
            logger.error(f"Binance API request failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Market data service unavailable"
            )
    
    @staticmethod
    async def get_klines(
        symbol: str,
        interval: str = "1h",
        limit: int = 100
    ) -> List[List]:
        """
        Get candlestick data
        
        Args:
            symbol: Trading pair symbol
            interval: Kline interval (1m, 5m, 15m, 1h, 1d, etc.)
            limit: Number of klines to return
        
        Returns:
            List[List]: Kline data
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{BinanceService.BASE_URL}/api/v3/klines",
                    params={
                        "symbol": symbol,
                        "interval": interval,
                        "limit": limit
                    }
                )
                
                if response.status_code != 200:
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail=f"Failed to fetch klines for {symbol}"
                    )
                
                return response.json()
        
        except httpx.RequestError as e:
            logger.error(f"Binance API request failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Market data service unavailable"
            )
    
    @staticmethod
    async def get_recent_trades(symbol: str, limit: int = 100) -> List[Dict]:
        """
        Get recent trades
        
        Args:
            symbol: Trading pair symbol
            limit: Number of trades to return
        
        Returns:
            List[Dict]: Recent trades
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{BinanceService.BASE_URL}/api/v3/trades",
                    params={"symbol": symbol, "limit": limit}
                )
                
                if response.status_code != 200:
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail=f"Failed to fetch trades for {symbol}"
                    )
                
                return response.json()
        
        except httpx.RequestError as e:
            logger.error(f"Binance API request failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Market data service unavailable"
            )

# Export functions for convenience
get_current_price = BinanceService.get_current_price
get_ticker_24hr = BinanceService.get_ticker_24hr
get_orderbook = BinanceService.get_orderbook
get_klines = BinanceService.get_klines
get_recent_trades = BinanceService.get_recent_trades