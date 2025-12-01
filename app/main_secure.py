# app/main_secure.py
"""
🔐 보안 강화된 FastAPI 메인 애플리케이션

개선 사항:
1. 보안 헤더 미들웨어
2. Rate Limiting 미들웨어
3. 요청 ID 추적
4. 상세한 로깅
"""
from contextlib import asynccontextmanager
import logging
import secrets
import time
from typing import Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# =============================================================================
# 로깅 설정
# =============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)8s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

logger = logging.getLogger(__name__)


# =============================================================================
# 설정 로드 (보안 설정 우선)
# =============================================================================

try:
    from app.core.config_secure import settings, validate_settings
    # 설정 유효성 검증
    validate_settings()
    logger.info("✅ 보안 강화 설정 로드 완료")
except ImportError:
    from app.core.config import settings
    logger.warning("⚠️ 기본 설정 사용 (보안 강화 설정 없음)")
except ValueError as e:
    logger.error(f"❌ 설정 검증 실패: {e}")
    raise


# =============================================================================
# 데이터베이스 초기화
# =============================================================================

from app.core.database import create_db_and_tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 라이프사이클"""
    logger.info("🚀 애플리케이션 시작...")
    
    # 데이터베이스 초기화
    create_db_and_tables()
    
    # 백그라운드 작업 시작 (선택적)
    # await start_background_tasks()
    
    logger.info("✅ 초기화 완료")
    
    yield
    
    # 종료 시 정리
    logger.info("👋 애플리케이션 종료...")


# =============================================================================
# FastAPI 앱 생성
# =============================================================================

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=getattr(settings, "VERSION", "2.1.0"),
    description="🔐 보안 강화된 암호화폐 모의투자 API",
    lifespan=lifespan,
    docs_url="/docs" if getattr(settings, "DEBUG", False) or getattr(settings, "ENVIRONMENT", "development") != "production" else None,
    redoc_url="/redoc" if getattr(settings, "DEBUG", False) or getattr(settings, "ENVIRONMENT", "development") != "production" else None,
)


# =============================================================================
# 미들웨어: 요청 ID 추가
# =============================================================================

@app.middleware("http")
async def add_request_id(request: Request, call_next: Callable):
    """
    각 요청에 고유 ID 추가
    - 로그 추적용
    - 디버깅 용이
    """
    request_id = secrets.token_hex(8)
    request.state.request_id = request_id
    
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    
    return response


# =============================================================================
# 미들웨어: 요청 로깅
# =============================================================================

@app.middleware("http")
async def log_requests(request: Request, call_next: Callable):
    """요청/응답 로깅"""
    start_time = time.time()
    
    # 클라이언트 IP
    forwarded = request.headers.get("X-Forwarded-For")
    client_ip = forwarded.split(",")[0].strip() if forwarded else (
        request.client.host if request.client else "unknown"
    )
    
    # 민감한 경로 로깅 제외
    sensitive_paths = ["/api/v1/auth/login", "/api/v1/auth/register"]
    should_log_body = request.url.path not in sensitive_paths
    
    response = await call_next(request)
    
    # 처리 시간
    process_time = (time.time() - start_time) * 1000
    
    # 로그 레벨 결정
    if response.status_code >= 500:
        log_level = logging.ERROR
    elif response.status_code >= 400:
        log_level = logging.WARNING
    else:
        log_level = logging.INFO
    
    logger.log(
        log_level,
        f"{request.method} {request.url.path} "
        f"| IP: {client_ip} "
        f"| Status: {response.status_code} "
        f"| Time: {process_time:.2f}ms"
    )
    
    # 처리 시간 헤더 추가
    response.headers["X-Process-Time"] = f"{process_time:.2f}ms"
    
    return response


# =============================================================================
# 미들웨어: 보안 헤더
# =============================================================================

@app.middleware("http")
async def add_security_headers(request: Request, call_next: Callable):
    """보안 헤더 추가"""
    response = await call_next(request)
    
    # 기본 보안 헤더
    security_headers = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Cache-Control": "no-store, no-cache, must-revalidate",
        "Pragma": "no-cache",
    }
    
    # 프로덕션 환경에서 추가 헤더
    if getattr(settings, "ENVIRONMENT", "development") == "production":
        security_headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        security_headers["Content-Security-Policy"] = "default-src 'self'"
    
    # 사용자 정의 헤더 추가
    custom_headers = getattr(settings, "SECURITY_HEADERS", {})
    security_headers.update(custom_headers)
    
    for header, value in security_headers.items():
        response.headers[header] = value
    
    return response


# =============================================================================
# 미들웨어: Rate Limiting
# =============================================================================

try:
    from app.utils.rate_limiter import rate_limit_middleware
    
    if getattr(settings, "RATE_LIMIT_ENABLED", True):
        app.middleware("http")(rate_limit_middleware)
        logger.info("✅ Rate Limiting 활성화")
except ImportError:
    logger.warning("⚠️ Rate Limiter 모듈 없음")


# =============================================================================
# CORS 설정
# =============================================================================

cors_origins = getattr(settings, "CORS_ORIGINS", ["*"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=getattr(settings, "CORS_ALLOW_CREDENTIALS", True),
    allow_methods=getattr(settings, "CORS_ALLOW_METHODS", ["*"]),
    allow_headers=getattr(settings, "CORS_ALLOW_HEADERS", ["*"]),
    expose_headers=["X-Request-ID", "X-Process-Time", "X-RateLimit-Remaining"],
)


# =============================================================================
# 전역 예외 처리
# =============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """전역 예외 처리"""
    request_id = getattr(request.state, "request_id", "unknown")
    
    # 민감한 정보 로깅 방지
    logger.error(
        f"❌ Unhandled exception | Request ID: {request_id} | "
        f"Path: {request.url.path} | Error: {type(exc).__name__}"
    )
    
    # 프로덕션에서는 상세 에러 숨김
    if getattr(settings, "ENVIRONMENT", "development") == "production":
        return JSONResponse(
            status_code=500,
            content={
                "detail": "서버 오류가 발생했습니다.",
                "request_id": request_id
            }
        )
    else:
        return JSONResponse(
            status_code=500,
            content={
                "detail": str(exc),
                "type": type(exc).__name__,
                "request_id": request_id
            }
        )


# =============================================================================
# 헬스체크
# =============================================================================

@app.get("/health", tags=["health"])
async def health_check():
    """
    헬스체크 엔드포인트
    
    - 로드밸런서, 모니터링 시스템에서 사용
    - Rate Limit 제외
    """
    return {
        "status": "healthy",
        "version": getattr(settings, "VERSION", "2.1.0"),
        "environment": getattr(settings, "ENVIRONMENT", "development")
    }


@app.get("/", tags=["root"])
async def root():
    """루트 엔드포인트"""
    return {
        "message": f"🪙 {settings.PROJECT_NAME}에 오신 것을 환영합니다!",
        "docs": "/docs",
        "health": "/health"
    }


# =============================================================================
# 라우터 등록
# =============================================================================

# 보안 강화 라우터 우선 시도
try:
    from app.routers.auth_secure import router as auth_secure_router
    app.include_router(auth_secure_router, prefix="/api/v1")
    logger.info("✅ 보안 강화 인증 라우터 등록")
except ImportError:
    from app.routers.auth import router as auth_router
    app.include_router(auth_router, prefix="/api/v1")
    logger.warning("⚠️ 기본 인증 라우터 사용")

# 기존 라우터
try:
    from app.routers.futures import router as futures_router
    app.include_router(futures_router, prefix="/api/v1")
except ImportError:
    logger.warning("⚠️ Futures 라우터 없음")

try:
    from app.routers.market import router as market_router
    app.include_router(market_router, prefix="/api/v1")
except ImportError:
    logger.warning("⚠️ Market 라우터 없음")

try:
    from app.routers.portfolio import router as portfolio_router
    app.include_router(portfolio_router, prefix="/api/v1")
except ImportError:
    logger.warning("⚠️ Portfolio 라우터 없음")

try:
    from app.routers.alerts import router as alerts_router
    app.include_router(alerts_router, prefix="/api/v1")
except ImportError:
    logger.debug("Alerts 라우터 없음 (선택적)")


# =============================================================================
# 개발 서버 실행
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main_secure:app",
        host=getattr(settings, "API_HOST", "0.0.0.0"),
        port=getattr(settings, "API_PORT", 8000),
        reload=getattr(settings, "ENVIRONMENT", "development") != "production",
        log_level="info"
    )