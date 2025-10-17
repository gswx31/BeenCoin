# app/main.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import create_db_and_tables
from app.routers import auth, orders, account, market
from app.services.binance_service import get_multiple_prices
from app.cache import cache_manager
import asyncio
import logging
from datetime import datetime

# 로깅 설정
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FastAPI 앱 생성
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="암호화폐 모의투자 플랫폼 - 리팩토링 버전",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 시작 이벤트
@app.on_event("startup")
async def startup_event():
    """서버 시작 시 실행"""
    logger.info("=" * 60)
    logger.info(f"🚀 Starting {settings.PROJECT_NAME} v{settings.VERSION}")
    logger.info("=" * 60)
    
    # 데이터베이스 초기화
    try:
        create_db_and_tables()
        logger.info("✅ Database initialized")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise
    
    # 캐시 통계
    logger.info(f"💾 Cache system initialized (TTL: {settings.CACHE_TTL}s)")
    
    # 설정 출력
    logger.info(f"📊 Supported symbols: {', '.join(settings.SUPPORTED_SYMBOLS)}")
    logger.info(f"💰 Initial balance: ${settings.INITIAL_BALANCE:,.2f}")
    logger.info(f"🌐 CORS origins: {', '.join(settings.CORS_ORIGINS)}")
    logger.info(f"🔧 DB Pool size: {settings.DB_POOL_SIZE}")
    
    logger.info("=" * 60)
    logger.info("✅ Server ready!")
    logger.info(f"📚 API Docs: http://{settings.API_HOST}:{settings.API_PORT}/docs")
    logger.info("=" * 60)


@app.on_event("shutdown")
async def shutdown_event():
    """서버 종료 시 실행"""
    logger.info("🛑 Shutting down...")
    
    # 캐시 정리
    stats = cache_manager.get_stats()
    logger.info(f"💾 Cache stats: {stats}")
    cache_manager.clear()
    
    logger.info("✅ Shutdown complete")


# 라우터 등록
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(orders.router, prefix=settings.API_V1_STR)
app.include_router(account.router, prefix=settings.API_V1_STR)
app.include_router(market.router, prefix=settings.API_V1_STR)


# 루트 엔드포인트
@app.get("/")
def root():
    """API 정보"""
    return {
        "message": f"{settings.PROJECT_NAME} v{settings.VERSION}",
        "status": "running",
        "timestamp": datetime.utcnow().isoformat(),
        "docs": "/docs",
        "features": [
            "실시간 암호화폐 거래",
            "시장가/지정가 주문",
            "포트폴리오 관리",
            "WebSocket 실시간 시세"
        ]
    }


# 헬스체크
@app.get("/health")
def health_check():
    """서버 상태 확인"""
    cache_stats = cache_manager.get_stats()
    
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.VERSION,
        "cache": cache_stats
    }


# WebSocket 연결 관리자
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"✅ WebSocket connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"❌ WebSocket disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """모든 연결에 브로드캐스트"""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"❌ Broadcast error: {e}")


manager = ConnectionManager()


# WebSocket 엔드포인트
@app.websocket("/ws/realtime")
async def websocket_realtime(websocket: WebSocket):
    """
    실시간 가격 스트리밍
    모든 지원 심볼의 가격을 2초마다 업데이트
    """
    await manager.connect(websocket)
    
    try:
        while True:
            # 모든 코인 가격 조회
            prices = await get_multiple_prices(settings.SUPPORTED_SYMBOLS)
            
            # 데이터 포맷
            data = {
                "type": "price_update",
                "timestamp": datetime.utcnow().isoformat(),
                "prices": {
                    symbol: float(price) 
                    for symbol, price in prices.items()
                }
            }
            
            # 브로드캐스트
            await manager.broadcast(data)
            
            # 2초 대기
            await asyncio.sleep(2)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocket disconnected normally")
    except Exception as e:
        logger.error(f"❌ WebSocket error: {e}")
        manager.disconnect(websocket)


# 에러 핸들러
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return {
        "error": "Not Found",
        "message": "요청하신 리소스를 찾을 수 없습니다",
        "path": str(request.url)
    }


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    logger.error(f"❌ Internal Server Error: {exc}")
    return {
        "error": "Internal Server Error",
        "message": "서버 내부 오류가 발생했습니다"
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        app,
        host=settings.API_HOST,
        port=settings.API_PORT,
        log_level=settings.LOG_LEVEL.lower()
    )