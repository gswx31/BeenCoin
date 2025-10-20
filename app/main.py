# app/main.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import create_db_and_tables
from app.routers import auth, orders, account, market
from app.services.binance_service import get_multiple_prices
from app.cache.cache_manager import cache_manager  # ✅ 직접 import
import asyncio
import logging
from datetime import datetime, timezone  # ✅ timezone 추가
from app.middleware.rate_limit import RateLimitMiddleware, rate_limiter
from app.middleware.cache_middleware import HTTPCacheMiddleware
from app.cache.redis_cache import redis_cache
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

app.add_middleware(RateLimitMiddleware)
# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    await redis_cache.connect()
    print("✅ 서버 시작")

# 시작 이벤트
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
    
    # 캐시 시스템 확인
    try:
        test_key = "startup_test"
        cache_manager.set(test_key, "test_value", ttl=1)
        test_value = cache_manager.get(test_key)
        if test_value == "test_value":
            logger.info("✅ Cache system verified")
        else:
            logger.warning("⚠️ Cache system verification failed")
    except Exception as e:
        logger.error(f"❌ Cache system error: {e}")
    
    logger.info(f"💾 Cache TTL: {settings.CACHE_TTL}s")
    
    # 설정 출력
    logger.info(f"📊 Supported symbols: {', '.join(settings.SUPPORTED_SYMBOLS)}")
    logger.info(f"💰 Initial balance: ${settings.INITIAL_BALANCE:,.2f}")
    logger.info(f"🌐 CORS origins: {', '.join(settings.CORS_ORIGINS)}")
    logger.info(f"🔧 DB Pool size: {settings.DB_POOL_SIZE}")
    
    logger.info("=" * 60)
    logger.info("✅ Server ready!")
    logger.info(f"📚 API Docs: http://{settings.API_HOST}:{settings.API_PORT}/docs")
    logger.info("=" * 60)

    asyncio.create_task(rate_limiter.cleanup_old_entries())

@app.on_event("shutdown")
async def shutdown_event():
    """서버 종료 시 실행"""
    logger.info("🛑 Shutting down...")
    
    # 활성 WebSocket 연결 정리
    logger.info(f"🔌 Closing {len(manager.active_connections)} WebSocket connections...")
    await manager.disconnect_all()
    
    # 캐시 정리
    stats = cache_manager.get_stats()
    logger.info(f"💾 Cache stats: {stats}")
    cache_manager.clear()
    await redis_cache.disconnect()
    
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
        "timestamp": datetime.now(timezone.utc).isoformat(),  # ✅ 수정
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
    try:
        cache_stats = cache_manager.get_stats()
    except Exception as e:
        logger.error(f"Cache stats error: {e}")
        cache_stats = {"error": str(e)}
    
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),  # ✅ 수정
        "version": settings.VERSION,
        "cache": cache_stats,
        "websocket_connections": len(manager.active_connections)
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

    async def disconnect_all(self):
        """모든 WebSocket 연결 종료"""
        for connection in self.active_connections[:]:
            try:
                await connection.close()
            except Exception as e:
                logger.debug(f"Error closing connection: {e}")
        self.active_connections.clear()

    async def broadcast(self, message: dict):
        """모든 연결에 브로드캐스트 (연결 상태 확인 포함)"""
        disconnected = []
        
        for connection in self.active_connections:
            try:
                # 연결이 열려있는지 확인
                if hasattr(connection, 'client_state') and connection.client_state.name == "CONNECTED":
                    await connection.send_json(message)
                elif hasattr(connection, 'application_state'):
                    # 다른 WebSocket 구현의 경우
                    await connection.send_json(message)
                else:
                    disconnected.append(connection)
            except Exception as e:
                logger.debug(f"Broadcast error: {e}")
                disconnected.append(connection)
        
        # 끊어진 연결 제거
        for conn in disconnected:
            self.disconnect(conn)


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
            try:
                prices = await get_multiple_prices(settings.SUPPORTED_SYMBOLS)
                
                # 데이터 포맷
                data = {
                    "type": "price_update",
                    "timestamp": datetime.now(timezone.utc).isoformat(),  # ✅ 수정
                    "prices": {
                        symbol: float(price) 
                        for symbol, price in prices.items()
                    }
                }
                
                # 브로드캐스트
                await manager.broadcast(data)
                
            except Exception as e:
                logger.error(f"❌ Error fetching prices: {e}")
            
            # 2초 대기
            await asyncio.sleep(2)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocket disconnected normally")
    except asyncio.CancelledError:
        manager.disconnect(websocket)
        logger.info("WebSocket cancelled during shutdown")
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
