# app/middleware/rate_limit.py
"""
Rate Limiting 미들웨어
- IP별 요청 제한
- DDoS 공격 방어
- 유연한 설정
"""

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate Limiting 미들웨어"""
    
    def __init__(
        self,
        app,
        max_requests: int = 100,
        window_seconds: int = 60,
        exclude_paths: List[str] = None
    ):
        super().__init__(app)
        self.max_requests = max_requests
        self.window = timedelta(seconds=window_seconds)
        self.requests: Dict[str, List[datetime]] = defaultdict(list)
        self.exclude_paths = exclude_paths or ["/health", "/docs", "/redoc", "/openapi.json"]
    
    async def dispatch(self, request: Request, call_next):
        # 제외 경로 확인
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)
        
        # 클라이언트 IP
        client_ip = request.client.host
        now = datetime.now()
        
        # 오래된 요청 제거
        self.requests[client_ip] = [
            req_time for req_time in self.requests[client_ip]
            if now - req_time < self.window
        ]
        
        # Rate Limit 확인
        if len(self.requests[client_ip]) >= self.max_requests:
            logger.warning(f"🚫 Rate limit exceeded: {client_ip}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Too many requests. Please try again later.",
                    "retry_after": self.window.seconds
                },
                headers={
                    "Retry-After": str(self.window.seconds)
                }
            )
        
        # 요청 기록
        self.requests[client_ip].append(now)
        
        # 응답 헤더에 Rate Limit 정보 추가
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(
            self.max_requests - len(self.requests[client_ip])
        )
        response.headers["X-RateLimit-Reset"] = str(
            int((now + self.window).timestamp())
        )
        
        return response


class APIKeyRateLimiter:
    """
    API Key별 Rate Limiting (더 정교한 제어)
    """
    
    def __init__(self):
        self.requests: Dict[str, List[datetime]] = defaultdict(list)
        self.limits = {
            "free": (100, 60),      # 100 req/min
            "premium": (1000, 60),  # 1000 req/min
            "enterprise": (10000, 60)  # 10000 req/min
        }
    
    async def check_limit(self, api_key: str, tier: str = "free") -> bool:
        """API Key Rate Limit 확인"""
        max_requests, window_seconds = self.limits.get(tier, self.limits["free"])
        window = timedelta(seconds=window_seconds)
        now = datetime.now()
        
        # 오래된 요청 제거
        self.requests[api_key] = [
            req_time for req_time in self.requests[api_key]
            if now - req_time < window
        ]
        
        # Limit 확인
        if len(self.requests[api_key]) >= max_requests:
            return False
        
        # 요청 기록
        self.requests[api_key].append(now)
        return True
    
    def get_remaining(self, api_key: str, tier: str = "free") -> int:
        """남은 요청 수"""
        max_requests, _ = self.limits.get(tier, self.limits["free"])
        return max_requests - len(self.requests[api_key])


# 싱글톤 인스턴스
rate_limiter = APIKeyRateLimiter()