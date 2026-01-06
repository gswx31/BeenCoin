# app/cache/cache_manager.py
"""
간단한 인메모리 캐시 시스템
API 호출 횟수를 줄여 성능 향상
"""
import logging
from threading import Lock
import time
from typing import Any

logger = logging.getLogger(__name__)

class CacheManager:
    """스레드 안전한 캐시 매니저"""

    def __init__(self):
        self._cache: dict[str, tuple[Any, float]] = {}
        self._lock = Lock()
        logger.info("💾 CacheManager 초기화 완료")

    def get(self, key: str) -> Any | None:
        """캐시에서 값 가져오기"""
        try:
            with self._lock:
                if key in self._cache:
                    value, expiry = self._cache[key]
                    if time.time() < expiry:
                        return value
                    else:
                        # 만료된 캐시 삭제
                        del self._cache[key]
                        logger.debug(f"🗑️ 만료된 캐시 삭제: {key}")
                return None
        except Exception as e:
            logger.error(f"❌ 캐시 읽기 오류 [{key}]: {e}")
            return None

    def set(self, key: str, value: Any, ttl: int = 5):
        """
        캐시에 값 저장
        ttl: Time To Live (초 단위, 기본 5초)
        """
        try:
            with self._lock:
                expiry = time.time() + ttl
                self._cache[key] = (value, expiry)
                logger.debug(f"💾 캐시 저장: {key} (TTL: {ttl}s)")
        except Exception as e:
            logger.error(f"❌ 캐시 저장 오류 [{key}]: {e}")

    def delete(self, key: str):
        """캐시에서 특정 키 삭제"""
        try:
            with self._lock:
                if key in self._cache:
                    del self._cache[key]
                    logger.debug(f"🗑️ 캐시 삭제: {key}")
        except Exception as e:
            logger.error(f"❌ 캐시 삭제 오류 [{key}]: {e}")

    def clear(self):
        """전체 캐시 삭제"""
        try:
            with self._lock:
                count = len(self._cache)
                self._cache.clear()
                logger.info(f"🗑️ 전체 캐시 삭제: {count}개 항목")
        except Exception as e:
            logger.error(f"❌ 캐시 삭제 오류: {e}")

    def get_stats(self) -> dict:
        """캐시 통계 정보"""
        try:
            with self._lock:
                total = len(self._cache)
                now = time.time()
                expired = sum(1 for _, (_, exp) in self._cache.items() if now >= exp)
                return {
                    "total_keys": total,
                    "active_keys": total - expired,
                    "expired_keys": expired,
                }
        except Exception as e:
            logger.error(f"❌ 캐시 통계 오류: {e}")
            return {"total_keys": 0, "active_keys": 0, "expired_keys": 0, "error": str(e)}

    def cleanup_expired(self):
        """만료된 캐시 항목 정리"""
        try:
            with self._lock:
                now = time.time()
                expired_keys = [key for key, (_, exp) in self._cache.items() if now >= exp]
                for key in expired_keys:
                    del self._cache[key]
                if expired_keys:
                    logger.info(f"🗑️ 만료 캐시 정리: {len(expired_keys)}개")
        except Exception as e:
            logger.error(f"❌ 캐시 정리 오류: {e}")

# 싱글톤 인스턴스
cache_manager = CacheManager()
