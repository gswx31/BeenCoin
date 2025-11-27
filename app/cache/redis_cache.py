# app/cache/redis_cache.py
"""
Redis 캐시 매니저
- 가격 데이터 캐싱 (TTL: 1초)
- API 호출 90% 감소
"""

import json
import logging
from typing import Any

from redis import asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisCache:
    """Redis 캐시 관리 클래스"""

    def __init__(self):
        self.redis: aioredis.Redis | None = None
        self._connected = False

    async def connect(self):
        """Redis 연결"""
        if self._connected:
            return

        try:
            self.redis = await aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_keepalive=True,
                health_check_interval=30,
            )
            # 연결 테스트
            await self.redis.ping()
            self._connected = True
            logger.info("✅ Redis 연결 성공")
        except Exception as e:
            logger.warning(f"⚠️ Redis 연결 실패 (캐시 비활성화): {e}")
            self.redis = None
            self._connected = False

    async def disconnect(self):
        """Redis 연결 종료"""
        if self.redis:
            await self.redis.close()
            self._connected = False
            logger.info("Redis 연결 종료")

    async def get(self, key: str) -> Any | None:
        """캐시 조회"""
        if not self.redis:
            return None

        try:
            value = await self.redis.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Redis GET 오류: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: int = 60):
        """캐시 저장"""
        if not self.redis:
            return False

        try:
            serialized = json.dumps(value)
            await self.redis.setex(key, ttl, serialized)
            return True
        except Exception as e:
            logger.error(f"Redis SET 오류: {e}")
            return False

    async def delete(self, key: str):
        """캐시 삭제"""
        if not self.redis:
            return False

        try:
            await self.redis.delete(key)
            return True
        except Exception as e:
            logger.error(f"Redis DELETE 오류: {e}")
            return False

    async def get_price(self, symbol: str) -> float | None:
        """가격 캐시 조회 (전용 메서드)"""
        key = f"price:{symbol}"
        cached = await self.get(key)
        return float(cached) if cached else None

    async def set_price(self, symbol: str, price: float, ttl: int = 1):
        """가격 캐시 저장 (TTL: 1초)"""
        key = f"price:{symbol}"
        await self.set(key, price, ttl)

    async def get_multiple_prices(self, symbols: list) -> dict:
        """여러 가격 한 번에 조회"""
        if not self.redis:
            return {}

        try:
            keys = [f"price:{symbol}" for symbol in symbols]
            values = await self.redis.mget(keys)

            result = {}
            for symbol, value in zip(symbols, values, strict=False):
                if value:
                    result[symbol] = float(json.loads(value))
            return result
        except Exception as e:
            logger.error(f"Redis MGET 오류: {e}")
            return {}

    async def get_stats(self) -> dict:
        """Redis 통계"""
        if not self.redis:
            return {"status": "disconnected"}

        try:
            info = await self.redis.info("stats")
            return {
                "status": "connected",
                "total_commands": info.get("total_commands_processed", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "hit_rate": round(
                    info.get("keyspace_hits", 0)
                    / max(info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0), 1)
                    * 100,
                    2,
                ),
            }
        except Exception as e:
            logger.error(f"Redis STATS 오류: {e}")
            return {"status": "error", "error": str(e)}


# 싱글톤 인스턴스
redis_cache = RedisCache()
