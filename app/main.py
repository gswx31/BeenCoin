# app/main.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.models.database import create_db_and_tables
from app.routers import auth, orders, account, market
from app.services.binance_service import get_multiple_prices
import asyncio
import logging

# 로거 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
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

# API v1 라우터 등록
app.include_router(auth.router, prefix=settings.API_V1_STR, tags=["auth"])
app.include_router(orders.router, prefix=settings.API_V1_STR, tags=["orders"])
app.include_router(account.router, prefix=settings.API_V1_STR, tags=["account"])
app.include_router(market.router, prefix=settings.API_V1_STR, tags=["market"])

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

    async def send_to_connection(self, websocket: WebSocket, message: dict):
        """단일 연결에 메시지 전송"""
        try:
            await websocket.send_json(message)
            return True
        except Exception as e:
            logger.error(f"Error sending to connection: {e}")
            return False

manager = ConnectionManager()

@app.websocket("/ws/realtime")
async def websocket_realtime(websocket: WebSocket):
    """실시간 가격 업데이트 WebSocket"""
    await manager.connect(websocket)
    
    try:
        while True:
            try:
                # 모든 지원 코인의 가격 가져오기
                prices = await get_multiple_prices(settings.SUPPORTED_SYMBOLS)
                
                message = {
                    "type": "price_update",
                    "data": {symbol: str(price) for symbol, price in prices.items()}
                }
                
                # 메시지 전송
                success = await manager.send_to_connection(websocket, message)
                if not success:
                    break
                    
            except Exception as e:
                logger.error(f"Error fetching prices: {e}")
            
            # 2초 대기
            await asyncio.sleep(2)
            
    except WebSocketDisconnect:
        logger.info("Client disconnected normally")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        manager.disconnect(websocket)

@app.on_event("startup")
async def startup_event():
    """서버 시작 이벤트"""
    create_db_and_tables()
    logger.info("=" * 60)
    logger.info("🚀 BeenCoin API Server Started!")
    logger.info("=" * 60)
    logger.info(f"📚 API Docs: http://localhost:8000/docs")
    logger.info(f"🔌 WebSocket: ws://localhost:8000/ws/realtime")
    logger.info(f"📊 Market API: http://localhost:8000{settings.API_V1_STR}/market/coins")
    logger.info("=" * 60)

@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "message": "BeenCoin API 서버가 실행 중입니다!",
        "version": "1.0.0",
        "docs": "/docs",
        "websocket": "/ws/realtime",
        "market": f"{settings.API_V1_STR}/market/coins"
    }

@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    return {
        "status": "healthy", 
        "version": "1.0.0",
        "active_websockets": len(manager.active_connections)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True,
        log_level="info"
    )