# app/cache/cache_manager.py
"""
간단한 인메모리 캐시 시스템
API 호출 횟수를 줄여 성능 향상
"""
import time
from typing import Any, Optional, Dict
from threading import Lock


class CacheManager:
    """스레드 안전한 캐시 매니저"""
    
    def __init__(self):
        self._cache: Dict[str, tuple[Any, float]] = {}
        self._lock = Lock()
    
    def get(self, key: str) -> Optional[Any]:
        """캐시에서 값 가져오기"""
        with self._lock:
            if key in self._cache:
                value, expiry = self._cache[key]
                if time.time() < expiry:
                    return value
                else:
                    # 만료된 캐시 삭제
                    del self._cache[key]
            return None
    
    def set(self, key: str, value: Any, ttl: int = 5):
        """
        캐시에 값 저장
        ttl: Time To Live (초 단위, 기본 5초)
        """
        with self._lock:
            expiry = time.time() + ttl
            self._cache[key] = (value, expiry)
    
    def delete(self, key: str):
        """캐시에서 특정 키 삭제"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
    
    def clear(self):
        """전체 캐시 삭제"""
        with self._lock:
            self._cache.clear()
    
    def get_stats(self) -> Dict:
        """캐시 통계 정보"""
        with self._lock:
            total = len(self._cache)
            now = time.time()
            expired = sum(1 for _, (_, exp) in self._cache.items() if now >= exp)
            return {
                "total_keys": total,
                "active_keys": total - expired,
                "expired_keys": expired
            }


# 싱글톤 인스턴스
cache_manager = CacheManager()