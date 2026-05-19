"""
요청 로깅 + correlation ID 미들웨어.
"""
import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from app.core.logging import generate_correlation_id, set_correlation_id

log = logging.getLogger("api")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 클라이언트가 보낸 correlation ID 사용, 없으면 생성
        cid = request.headers.get("X-Correlation-ID") or generate_correlation_id()
        set_correlation_id(cid)

        start = time.time()
        try:
            response = await call_next(request)
            duration_ms = int((time.time() - start) * 1000)
            log.info(
                "request",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "duration_ms": duration_ms,
                    "client": request.client.host if request.client else None,
                },
            )
            response.headers["X-Correlation-ID"] = cid
            return response
        except Exception as e:
            duration_ms = int((time.time() - start) * 1000)
            log.exception(
                "request_failed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": duration_ms,
                    "error": str(e),
                },
            )
            raise
