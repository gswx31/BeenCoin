
# ============================================
# app/middleware/cache_middleware.py
# ============================================
"""
HTTP 응답 캐싱 미들웨어
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from app.cache.redis_cache import redis_cache
import json
import hashlib


class HTTPCacheMiddleware(BaseHTTPMiddleware):
    """
    GET 요청 응답 캐싱
    """
    
    CACHEABLE_PATHS = [
        "/api/v1/market/coins",
        "/api/v1/market/coin/",
    ]
    
    CACHE_TTL = {
        "/api/v1/market/coins": 10,  # 10초
        "/api/v1/market/coin/": 5,   # 5초
    }
    
    async def dispatch(self, request: Request, call_next):
        # GET 요청만 캐싱
        if request.method != "GET":
            return await call_next(request)
        
        # 캐싱 대상 경로 확인
        path = request.url.path
        should_cache = any(path.startswith(p) for p in self.CACHEABLE_PATHS)
        
        if not should_cache:
            return await call_next(request)
        
        # 캐시 키 생성 (경로 + 쿼리 파라미터)
        cache_key = f"http:{hashlib.md5(str(request.url).encode()).hexdigest()}"
        
        # 캐시 확인
        cached = await redis_cache.get(cache_key)
        if cached:
            return Response(
                content=json.dumps(cached),
                media_type="application/json",
                headers={"X-Cache": "HIT"}
            )
        
        # 요청 처리
        response = await call_next(request)
        
        # 응답 캐싱 (200 OK만)
        if response.status_code == 200:
            # TTL 결정
            ttl = next(
                (self.CACHE_TTL[p] for p in self.CACHEABLE_PATHS if path.startswith(p)),
                10
            )
            
            # 응답 본문 읽기
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            
            try:
                response_data = json.loads(body)
                await redis_cache.set(cache_key, response_data, ttl=ttl)
            except:
                pass
            
            # 새 응답 생성
            return Response(
                content=body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type
            )
        
        return response

