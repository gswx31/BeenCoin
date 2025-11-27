# ============================================
# app/services/binance_service_optimized.py
# ============================================
"""
성능 최적화된 Binance 서비스
"""
from decimal import Decimal
import logging

import httpx

from app.cache.redis_cache import redis_cache

logger = logging.getLogger(__name__)

BINANCE_API_BASE = "https://api.binance.com"


async def get_current_price_cached(symbol: str) -> Decimal:
    """
    캐싱을 활용한 현재가 조회
    - 5초 캐싱
    """
    cache_key = f"price:{symbol}"

    # 캐시 확인
    cached_price = await redis_cache.get(cache_key)
    if cached_price:
        logger.debug(f"💾 캐시 히트: {symbol} = ${cached_price}")
        return Decimal(str(cached_price))

    # 캐시 미스 - API 호출
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BINANCE_API_BASE}/api/v3/ticker/price", params={"symbol": symbol}, timeout=10.0
        )
        response.raise_for_status()
        price = Decimal(response.json()["price"])

    # 캐시 저장 (5초)
    await redis_cache.set(cache_key, float(price), ttl=5)
    logger.debug(f"📡 API 호출: {symbol} = ${price}")

    return price


async def get_multiple_prices_batch(symbols: list[str]) -> dict[str, Decimal]:
    """
    여러 코인 가격 배치 조회
    - N+1 문제 해결
    - 단일 API 호출로 여러 가격 조회
    """
    cache_key = "prices:batch"

    # 캐시 확인
    cached_prices = await redis_cache.get(cache_key)
    if cached_prices:
        logger.debug(f"💾 배치 캐시 히트: {len(symbols)}개")
        return {k: Decimal(str(v)) for k, v in cached_prices.items() if k in symbols}

    # 캐시 미스 - 배치 API 호출
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BINANCE_API_BASE}/api/v3/ticker/price", timeout=10.0)
        response.raise_for_status()
        all_prices = response.json()

    # 딕셔너리로 변환
    price_dict = {
        item["symbol"]: Decimal(item["price"]) for item in all_prices if item["symbol"] in symbols
    }

    # 캐시 저장 (3초)
    await redis_cache.set(cache_key, {k: float(v) for k, v in price_dict.items()}, ttl=3)
    logger.debug(f"📡 배치 API 호출: {len(price_dict)}개")

    return price_dict
