# app/main.py
"""
FastAPI 메인 애플리케이션 - 선물 포트폴리오 추가
"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import create_db_and_tables

# ⭐ 라우터 import (선물 포트폴리오 추가)
from app.routers import (
    auth,
    futures,
    futures_portfolio,  # ⭐ NEW!
    market,
)
from app.tasks.scheduler import start_all_background_tasks

# 로깅 설정
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# FastAPI 앱 생성
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="암호화폐 선물 거래 플랫폼 (포트폴리오 포함)",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ⭐ 라우터 등록 (선물 포트폴리오 추가)
app.include_router(auth.router, prefix="/api/v1")
app.include_router(market.router, prefix="/api/v1")
app.include_router(futures.router, prefix="/api/v1")
app.include_router(futures_portfolio.router, prefix="/api/v1")  # ⭐ NEW!

logger.info("✅ 라우터 등록 완료:")
logger.info("   - /api/v1/auth (인증)")
logger.info("   - /api/v1/market (시장 데이터)")
logger.info("   - /api/v1/futures (선물 거래)")
logger.info("   - /api/v1/futures/portfolio (선물 포트폴리오) ⭐")


# 시작 이벤트
@app.on_event("startup")
async def startup_event():
    """서버 시작 시 실행"""
    logger.info("🚀 서버 시작")

    # 1. 데이터베이스 초기화
    create_db_and_tables()
    logger.info("✅ 데이터베이스 초기화 완료")

    # 2. 백그라운드 작업 시작
    start_all_background_tasks()
    logger.info("✅ 백그라운드 작업 시작")

    logger.info("✅ 서버 시작 완료")
    logger.info("📡 Docs: http://localhost:8000/docs")


# 종료 이벤트
@app.on_event("shutdown")
async def shutdown_event():
    """서버 종료 시 실행"""
    logger.info("👋 서버 종료")


# 헬스 체크
@app.get("/health")
async def health_check():
    """헬스 체크"""
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "features": ["선물 거래", "포트폴리오", "실시간 체결", "분할 체결"],
    }


# 루트 엔드포인트
@app.get("/")
async def root():
    """루트"""
    return {
        "message": "BeenCoin 선물 거래 API",
        "version": settings.VERSION,
        "docs": "/docs",
        "endpoints": {
            "auth": "/api/v1/auth",
            "market": "/api/v1/market",
            "futures": "/api/v1/futures",
            "portfolio": "/api/v1/futures/portfolio",
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
