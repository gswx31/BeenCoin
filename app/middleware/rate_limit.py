# app/middleware/rate_limit.py
"""
Rate Limiting 미들웨어 - 주문 남용 방지
"""
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, Tuple
import asyncio


class RateLimiter:
    """
    간단한 Rate Limiter 구현
    
    실제 프로덕션에서는 Redis 사용 권장
    """
    
    def __init__(self):
        # user_id -> (요청 횟수, 윈도우 시작 시간)
        self.requests: Dict[str, Tuple[int, datetime]] = {}
        self.lock = asyncio.Lock()
    
    async def is_allowed(
        self, 
        key: str, 
        max_requests: int, 
        window_seconds: int
    ) -> bool:
        """
        요청이 허용되는지 확인
        
        Args:
            key: 사용자 식별자 (user_id 등)
            max_requests: 윈도우 내 최대 요청 수
            window_seconds: 시간 윈도우 (초)
        
        Returns:
            허용 여부
        """
        async with self.lock:
            now = datetime.utcnow()
            
            if key not in self.requests:
                self.requests[key] = (1, now)
                return True
            
            count, window_start = self.requests[key]
            window_end = window_start + timedelta(seconds=window_seconds)
            
            # 윈도우가 만료되었으면 리셋
            if now > window_end:
                self.requests[key] = (1, now)
                return True
            
            # 윈도우 내에서 요청 수 확인
            if count >= max_requests:
                return False
            
            # 요청 수 증가
            self.requests[key] = (count + 1, window_start)
            return True
    
    async def cleanup_old_entries(self):
        """오래된 엔트리 정리 (메모리 누수 방지)"""
        while True:
            await asyncio.sleep(300)  # 5분마다
            
            async with self.lock:
                now = datetime.utcnow()
                expired_keys = [
                    key for key, (_, window_start) in self.requests.items()
                    if now - window_start > timedelta(hours=1)
                ]
                
                for key in expired_keys:
                    del self.requests[key]
                
                if expired_keys:
                    print(f"🧹 Rate Limiter 정리: {len(expired_keys)}개 엔트리 제거")


# 전역 Rate Limiter 인스턴스
rate_limiter = RateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate Limiting 미들웨어
    
    특정 엔드포인트에 대한 요청 제한
    """
    
    # 엔드포인트별 제한 설정
    LIMITS = {
        "/api/v1/orders/": {
            "max_requests": 10,
            "window_seconds": 60,  # 1분에 10개
            "message": "주문 요청이 너무 많습니다. 잠시 후 다시 시도해주세요."
        },
        "/api/v1/auth/login": {
            "max_requests": 5,
            "window_seconds": 300,  # 5분에 5번
            "message": "로그인 시도가 너무 많습니다. 잠시 후 다시 시도해주세요."
        },
        "/api/v1/auth/register": {
            "max_requests": 3,
            "window_seconds": 3600,  # 1시간에 3번
            "message": "회원가입 시도가 너무 많습니다. 잠시 후 다시 시도해주세요."
        }
    }
    
    async def dispatch(self, request: Request, call_next):
        # Rate Limit 적용 대상인지 확인
        path = request.url.path
        
        # POST 요청만 제한
        if request.method != "POST":
            return await call_next(request)
        
        # 제한 설정 확인
        limit_config = None
        for endpoint, config in self.LIMITS.items():
            if path.startswith(endpoint):
                limit_config = config
                break
        
        if not limit_config:
            return await call_next(request)
        
        # 사용자 식별 (IP 또는 user_id)
        user_id = request.state.user.id if hasattr(request.state, 'user') and request.state.user else None
        client_ip = request.client.host if request.client else "unknown"
        rate_key = f"{user_id or client_ip}:{path}"
        
        # Rate Limit 확인
        is_allowed = await rate_limiter.is_allowed(
            rate_key,
            limit_config["max_requests"],
            limit_config["window_seconds"]
        )
        
        if not is_allowed:
            raise HTTPException(
                status_code=429,
                detail=limit_config["message"]
            )
        
        # 요청 처리
        response = await call_next(request)
        
        # Rate Limit 정보 헤더 추가
        response.headers["X-RateLimit-Limit"] = str(limit_config["max_requests"])
        response.headers["X-RateLimit-Window"] = str(limit_config["window_seconds"])
        
        return response


# ========================================
# app/main.py에 추가할 코드
# ========================================
"""
from app.middleware.rate_limit import RateLimitMiddleware, rate_limiter
import asyncio

app = FastAPI(...)

# Rate Limiting 미들웨어 추가
app.add_middleware(RateLimitMiddleware)

# Rate Limiter 정리 태스크 시작
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(rate_limiter.cleanup_old_entries())
"""