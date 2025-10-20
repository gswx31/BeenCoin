# app/services/binance_service.py
import httpx
from decimal import Decimal
from typing import Dict, List
from app.core.config import settings
from app.cache.cache_manager import cache_manager  # ✅ 직접 import
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)


class BinanceAPIError(Exception):
    """Binance API 에러"""
    pass


async def get_current_price(symbol: str) -> Decimal:
    """
    현재 가격 조회 (캐싱 적용)
    캐시 TTL: 5초
    """
    cache_key = f"price:{symbol}"
    
    # 캐시 확인
    try:
        cached_price = cache_manager.get(cache_key)
        if cached_price is not None:
            logger.debug(f"💾 캐시 히트: {symbol} = ${cached_price}")
            return Decimal(str(cached_price))
    except Exception as e:
        logger.warning(f"⚠️ 캐시 읽기 실패: {e}")
    
    # API 호출
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{settings.BINANCE_API_URL}/ticker/price",
                params={"symbol": symbol}
            )
            response.raise_for_status()
            
            data = response.json()
            price = Decimal(data["price"])
            
            # 캐시 저장
            try:
                cache_manager.set(cache_key, float(price), ttl=settings.CACHE_TTL)
                logger.debug(f"📡 API 호출: {symbol} = ${price}")
            except Exception as e:
                logger.warning(f"⚠️ 캐시 저장 실패: {e}")
            
            return price
            
    except httpx.HTTPError as e:
        logger.error(f"❌ {symbol} 가격 조회 실패: {e}")
        raise HTTPException(status_code=503, detail=f"{symbol} 시장 가격 조회 실패")
    except KeyError as e:
        logger.error(f"❌ {symbol} 잘못된 응답 형식: {e}")
        raise HTTPException(status_code=500, detail="가격 데이터 파싱 실패")


async def get_multiple_prices(symbols: List[str]) -> Dict[str, Decimal]:
    """
    여러 심볼의 가격을 동시에 조회
    """
    prices = {}
    
    for symbol in symbols:
        try:
            price = await get_current_price(symbol)
            prices[symbol] = price
        except Exception as e:
            logger.warning(f"⚠️ {symbol} 가격 조회 실패: {e}")
            # 캐시된 값이라도 있으면 사용
            try:
                cached = cache_manager.get(f"price:{symbol}")
                if cached:
                    prices[symbol] = Decimal(str(cached))
                    logger.info(f"💾 캐시된 가격 사용: {symbol} = ${cached}")
            except Exception:
                pass
    
    return prices


async def execute_market_order(symbol: str, side: str, quantity: Decimal) -> Decimal:
    """
    시장가 주문 실행 (시뮬레이션)
    실제로는 현재 가격을 반환
    """
    return await get_current_price(symbol)


async def get_recent_trades(symbol: str, limit: int = 50) -> List[Dict]:
    """최근 거래 내역 조회"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{settings.BINANCE_API_URL}/trades",
                params={"symbol": symbol, "limit": limit}
            )
            response.raise_for_status()
            return response.json()
            
    except httpx.HTTPError as e:
        logger.error(f"❌ 거래 내역 조회 실패: {e}")
        return []


async def get_24h_ticker(symbol: str) -> Dict:
    """24시간 티커 정보 (캐싱 적용)"""
    cache_key = f"ticker24h:{symbol}"
    
    try:
        cached = cache_manager.get(cache_key)
        if cached:
            return cached
    except Exception as e:
        logger.warning(f"⚠️ 캐시 읽기 실패: {e}")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{settings.BINANCE_API_URL}/ticker/24hr",
                params={"symbol": symbol}
            )
            response.raise_for_status()
            data = response.json()
            
            try:
                cache_manager.set(cache_key, data, ttl=settings.CACHE_TTL)
            except Exception as e:
                logger.warning(f"⚠️ 캐시 저장 실패: {e}")
            
            return data
            
    except httpx.HTTPError as e:
        logger.error(f"❌ 24h 티커 조회 실패: {e}")
        raise HTTPException(status_code=503, detail="티커 정보 조회 실패")


async def get_coin_info(symbol: str) -> Dict:
    """코인 정보 조회 (가격 + 24h 변동)"""
    try:
        ticker = await get_24h_ticker(symbol)
        
        return {
            "symbol": symbol,
            "price": ticker.get("lastPrice", "0"),
            "change": ticker.get("priceChangePercent", "0"),
            "volume": ticker.get("volume", "0"),
            "high": ticker.get("highPrice", "0"),
            "low": ticker.get("lowPrice", "0")
        }
    except Exception as e:
        logger.error(f"❌ {symbol} 정보 조회 실패: {e}")
        raise HTTPException(status_code=503, detail="코인 정보 조회 실패")

async def get_historical_data(symbol: str, interval: str = "1h", limit: int = 100) -> List[Dict]:
    """과거 데이터 조회 (차트용)"""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f"{settings.BINANCE_API_URL}/klines",
                params={
                    "symbol": symbol,
                    "interval": interval,
                    "limit": limit
                }
            )
            response.raise_for_status()
            
            klines = response.json()
            
            # 데이터 포맷 변환
            formatted_data = []
            for k in klines:
                formatted_data.append({
                    "time": k[0],
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                    "volume": float(k[5])
                })
            
            return formatted_data
            
    except httpx.HTTPError as e:
        logger.error(f"❌ 과거 데이터 조회 실패: {e}")
        return []