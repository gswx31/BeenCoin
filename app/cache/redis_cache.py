# ============================================
# app/cache/redis_cache.py - Redis 캐싱
# ============================================
"""
Redis 기반 캐싱 시스템
"""
import redis.asyncio as redis
from typing import Optional, Any
import json
import logging
from decimal import Decimal

logger = logging.getLogger(__name__)


class RedisCache:
    """Redis 캐시 매니저"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.redis_url = redis_url
        self.redis: Optional[redis.Redis] = None
    
    async def connect(self):
        """Redis 연결"""
        try:
            self.redis = await redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            await self.redis.ping()
            logger.info("✅ Redis 연결 성공")
        except Exception as e:
            logger.error(f"❌ Redis 연결 실패: {e}")
            self.redis = None
    
    async def disconnect(self):
        """Redis 연결 종료"""
        if self.redis:
            await self.redis.close()
            logger.info("🔌 Redis 연결 종료")
    
    async def get(self, key: str) -> Optional[Any]:
        """캐시에서 값 가져오기"""
        if not self.redis:
            return None
        
        try:
            value = await self.redis.get(key)
            if value:
                return json.loads(value, parse_float=Decimal)
            return None
        except Exception as e:
            logger.error(f"❌ 캐시 읽기 실패 [{key}]: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: int = 300):
        """
        캐시에 값 저장
        ttl: Time To Live (초 단위, 기본 5분)
        """
        if not self.redis:
            return False
        
        try:
            # Decimal을 float로 변환하여 저장
            serialized = json.dumps(value, default=float)
            await self.redis.setex(key, ttl, serialized)
            logger.debug(f"💾 캐시 저장: {key} (TTL: {ttl}s)")
            return True
        except Exception as e:
            logger.error(f"❌ 캐시 저장 실패 [{key}]: {e}")
            return False
    
    async def delete(self, key: str):
        """캐시에서 키 삭제"""
        if not self.redis:
            return False
        
        try:
            await self.redis.delete(key)
            logger.debug(f"🗑️ 캐시 삭제: {key}")
            return True
        except Exception as e:
            logger.error(f"❌ 캐시 삭제 실패 [{key}]: {e}")
            return False
    
    async def clear_pattern(self, pattern: str):
        """패턴에 맞는 모든 키 삭제"""
        if not self.redis:
            return 0
        
        try:
            keys = []
            async for key in self.redis.scan_iter(match=pattern):
                keys.append(key)
            
            if keys:
                deleted = await self.redis.delete(*keys)
                logger.info(f"🗑️ 패턴 캐시 삭제: {pattern} ({deleted}개)")
                return deleted
            return 0
        except Exception as e:
            logger.error(f"❌ 패턴 삭제 실패 [{pattern}]: {e}")
            return 0


# 전역 Redis 캐시 인스턴스
redis_cache = RedisCache()