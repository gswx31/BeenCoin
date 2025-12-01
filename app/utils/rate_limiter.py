# app/utils/rate_limiter.py
"""
🔐 Rate Limiting 유틸리티

Brute Force 공격 방지를 위한 요청 제한 기능
- IP 기반 제한
- 엔드포인트별 차등 제한
- Redis 지원 (선택적)
"""
import time
from collections import defaultdict
from datetime import datetime, timedelta
from functools import wraps
import logging
from threading import Lock
from typing import Callable, Dict, Optional

from fastapi import HTTPException, Request, Response, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


# =============================================================================
# 인메모리 Rate Limiter (Redis 없이 동작)
# =============================================================================

class InMemoryRateLimiter:
    """
    인메모리 Rate Limiter
    
    단일 인스턴스에서 동작하는 간단한 구현
    프로덕션에서는 Redis 기반 구현 권장
    """
    
    def __init__(self):
        # IP별 요청 기록: {ip: [(timestamp, endpoint), ...]}
        self._requests: Dict[str, list] = defaultdict(list)
        self._lock = Lock()
        self._cleanup_interval = 60  # 60초마다 정리
        self._last_cleanup = time.time()
    
    def _parse_rate_limit(self, rate_limit: str) -> tuple[int, int]:
        """
        Rate limit 문자열 파싱
        
        Args:
            rate_limit: "5/minute", "100/hour" 등
            
        Returns:
            (max_requests, window_seconds)
        """
        try:
            count, period = rate_limit.split("/")
            count = int(count)
            
            period_seconds = {
                "second": 1,
                "minute": 60,
                "hour": 3600,
                "day": 86400,
            }
            
            window = period_seconds.get(period.lower(), 60)
            return count, window
        except Exception:
            logger.warning(f"Rate limit 파싱 실패: {rate_limit}, 기본값 사용")
            return 100, 60  # 기본: 분당 100회
    
    def _cleanup_old_requests(self):
        """오래된 요청 기록 정리"""
        current_time = time.time()
        
        if current_time - self._last_cleanup < self._cleanup_interval:
            return
        
        with self._lock:
            cutoff_time = current_time - 3600  # 1시간 이전 기록 삭제
            
            for ip in list(self._requests.keys()):
                self._requests[ip] = [
                    req for req in self._requests[ip]
                    if req[0] > cutoff_time
                ]
                
                # 빈 리스트 제거
                if not self._requests[ip]:
                    del self._requests[ip]
            
            self._last_cleanup = current_time
    
    def is_allowed(
        self, 
        key: str, 
        rate_limit: str,
        endpoint: str = "default"
    ) -> tuple[bool, dict]:
        """
        요청 허용 여부 확인
        
        Args:
            key: 식별자 (보통 IP)
            rate_limit: "5/minute" 형식
            endpoint: 엔드포인트 구분용
            
        Returns:
            (is_allowed, info_dict)
        """
        self._cleanup_old_requests()
        
        max_requests, window_seconds = self._parse_rate_limit(rate_limit)
        current_time = time.time()
        window_start = current_time - window_seconds
        
        with self._lock:
            # 현재 윈도우 내 요청 수 계산
            recent_requests = [
                req for req in self._requests[key]
                if req[0] > window_start and req[1] == endpoint
            ]
            
            remaining = max_requests - len(recent_requests)
            
            # 가장 오래된 요청이 만료되는 시간
            if recent_requests and remaining <= 0:
                oldest = min(req[0] for req in recent_requests)
                reset_time = oldest + window_seconds
            else:
                reset_time = current_time + window_seconds
            
            info = {
                "limit": max_requests,
                "remaining": max(0, remaining),
                "reset": int(reset_time),
                "retry_after": max(0, int(reset_time - current_time)) if remaining <= 0 else 0
            }
            
            if remaining > 0:
                # 요청 기록 추가
                self._requests[key].append((current_time, endpoint))
                return True, info
            else:
                return False, info
    
    def get_client_ip(self, request: Request) -> str:
        """
        클라이언트 IP 추출
        
        X-Forwarded-For 헤더 우선 확인 (프록시/로드밸런서 뒤에 있는 경우)
        """
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # 첫 번째 IP가 실제 클라이언트
            return forwarded.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"


# 전역 Rate Limiter 인스턴스
rate_limiter = InMemoryRateLimiter()


# =============================================================================
# FastAPI 미들웨어 및 데코레이터
# =============================================================================

async def rate_limit_middleware(request: Request, call_next):
    """
    전역 Rate Limiting 미들웨어
    
    모든 요청에 기본 Rate Limit 적용
    """
    # 설정에서 Rate Limiting 활성화 여부 확인
    try:
        from app.core.config_secure import settings
        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)
        default_limit = settings.RATE_LIMIT_API
    except ImportError:
        # 기존 config 사용
        from app.core.config import settings
        default_limit = getattr(settings, "RATE_LIMIT_API", "100/minute")
    
    # 헬스체크 등 제외
    if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json"]:
        return await call_next(request)
    
    client_ip = rate_limiter.get_client_ip(request)
    is_allowed, info = rate_limiter.is_allowed(
        key=client_ip,
        rate_limit=default_limit,
        endpoint="global"
    )
    
    if not is_allowed:
        logger.warning(
            f"🚫 Rate limit 초과: IP={client_ip}, "
            f"endpoint={request.url.path}"
        )
        
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "detail": "요청이 너무 많습니다. 잠시 후 다시 시도해주세요.",
                "retry_after": info["retry_after"]
            },
            headers={
                "Retry-After": str(info["retry_after"]),
                "X-RateLimit-Limit": str(info["limit"]),
                "X-RateLimit-Remaining": str(info["remaining"]),
                "X-RateLimit-Reset": str(info["reset"])
            }
        )
    
    # 요청 처리
    response = await call_next(request)
    
    # Rate Limit 헤더 추가
    response.headers["X-RateLimit-Limit"] = str(info["limit"])
    response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
    response.headers["X-RateLimit-Reset"] = str(info["reset"])
    
    return response


def rate_limit(limit: str):
    """
    엔드포인트별 Rate Limiting 데코레이터
    
    사용법:
        @router.post("/login")
        @rate_limit("5/minute")
        async def login(...):
            ...
    
    Args:
        limit: "5/minute", "100/hour" 형식의 제한
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, request: Request = None, **kwargs):
            # Request 객체 찾기
            if request is None:
                # kwargs에서 찾기
                request = kwargs.get("request")
                
            if request is None:
                # args에서 찾기
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break
            
            if request is None:
                logger.warning("Rate limit: Request 객체를 찾을 수 없습니다.")
                return await func(*args, **kwargs)
            
            client_ip = rate_limiter.get_client_ip(request)
            endpoint = f"{func.__module__}.{func.__name__}"
            
            is_allowed, info = rate_limiter.is_allowed(
                key=client_ip,
                rate_limit=limit,
                endpoint=endpoint
            )
            
            if not is_allowed:
                logger.warning(
                    f"🚫 Rate limit 초과: IP={client_ip}, "
                    f"endpoint={endpoint}, limit={limit}"
                )
                
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "message": "요청이 너무 많습니다. 잠시 후 다시 시도해주세요.",
                        "retry_after": info["retry_after"]
                    },
                    headers={
                        "Retry-After": str(info["retry_after"])
                    }
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


# =============================================================================
# 로그인 실패 추적 (Brute Force 방지)
# =============================================================================

class LoginAttemptTracker:
    """
    로그인 시도 추적기
    
    연속 실패 시 점진적 지연/차단
    """
    
    def __init__(self):
        # {username: [(timestamp, success), ...]}
        self._attempts: Dict[str, list] = defaultdict(list)
        self._blocked_until: Dict[str, float] = {}
        self._lock = Lock()
        
        # 설정
        self.max_attempts = 5  # 최대 시도 횟수
        self.window_seconds = 300  # 5분 윈도우
        self.block_duration = 900  # 15분 차단
    
    def record_attempt(self, username: str, success: bool) -> None:
        """로그인 시도 기록"""
        with self._lock:
            current_time = time.time()
            self._attempts[username].append((current_time, success))
            
            # 오래된 기록 정리
            cutoff = current_time - self.window_seconds
            self._attempts[username] = [
                a for a in self._attempts[username]
                if a[0] > cutoff
            ]
            
            # 성공 시 차단 해제
            if success and username in self._blocked_until:
                del self._blocked_until[username]
    
    def is_blocked(self, username: str) -> tuple[bool, int]:
        """
        차단 여부 확인
        
        Returns:
            (is_blocked, remaining_seconds)
        """
        with self._lock:
            current_time = time.time()
            
            # 기존 차단 확인
            if username in self._blocked_until:
                if current_time < self._blocked_until[username]:
                    remaining = int(self._blocked_until[username] - current_time)
                    return True, remaining
                else:
                    del self._blocked_until[username]
            
            # 실패 횟수 확인
            cutoff = current_time - self.window_seconds
            recent_failures = [
                a for a in self._attempts[username]
                if a[0] > cutoff and not a[1]
            ]
            
            if len(recent_failures) >= self.max_attempts:
                # 차단 설정
                self._blocked_until[username] = current_time + self.block_duration
                logger.warning(
                    f"🔒 계정 임시 차단: username={username}, "
                    f"failures={len(recent_failures)}, "
                    f"duration={self.block_duration}s"
                )
                return True, self.block_duration
            
            return False, 0
    
    def get_remaining_attempts(self, username: str) -> int:
        """남은 시도 횟수 반환"""
        with self._lock:
            current_time = time.time()
            cutoff = current_time - self.window_seconds
            
            recent_failures = [
                a for a in self._attempts[username]
                if a[0] > cutoff and not a[1]
            ]
            
            return max(0, self.max_attempts - len(recent_failures))


# 전역 로그인 추적기
login_tracker = LoginAttemptTracker()