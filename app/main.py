# app/main.py - 선물 거래 라우터 추가
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.models.database import create_db_and_tables
from app.routers import auth, orders, account, market, futures
from app.services.binance_service import get_multiple_prices
import asyncio

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(orders.router, prefix=settings.API_V1_STR)
app.include_router(account.router, prefix=settings.API_V1_STR)
app.include_router(market.router, prefix=settings.API_V1_STR)
app.include_router(futures.router, prefix=settings.API_V1_STR)  # 선물 거래 라우터 추가

# WebSocket 연결 관리
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"✅ WebSocket connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        print(f"❌ WebSocket disconnected. Total: {len(self.active_connections)}")

    async def send_to_connection(self, websocket: WebSocket, message: dict):
        """단일 연결에 메시지 전송 (에러 처리 포함)"""
        try:
            await websocket.send_json(message)
            return True
        except Exception as e:
            print(f"Error sending to connection: {e}")
            return False

manager = ConnectionManager()

@app.websocket("/ws/realtime")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    
    try:
        while True:
            # 실시간 가격 업데이트
            try:
                all_symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT"]
                prices = await get_multiple_prices(all_symbols)
                
                message = {
                    "type": "price_update",
                    "data": {symbol: str(price) for symbol, price in prices.items()}
                }
                
                # 메시지 전송 성공 여부 확인
                success = await manager.send_to_connection(websocket, message)
                if not success:
                    break
                    
            except Exception as e:
                print(f"Error fetching prices: {e}")
            
            # 2초 대기
            await asyncio.sleep(2)
            
    except WebSocketDisconnect:
        print("Client disconnected normally")
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        manager.disconnect(websocket)

@app.on_event("startup")
async def startup_event():
    create_db_and_tables()
    print("=" * 60)
    print("🚀 BeenCoin Futures Trading API Started!")
    print("=" * 60)
    print(f"📚 API Docs: http://localhost:8000/docs")
    print(f"🔌 WebSocket: ws://localhost:8000/ws/realtime")
    print(f"📊 Market API: http://localhost:8000/api/v1/market/coins")
    print(f"💰 Futures API: http://localhost:8000/api/v1/futures/")
    print("=" * 60)

@app.get("/")
async def root():
    return {
        "message": "BeenCoin Futures Trading API 서버가 실행 중입니다!",
        "docs": "/docs",
        "websocket": "/ws/realtime",
        "market": "/api/v1/market/coins",
        "futures": "/api/v1/futures/"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy", 
        "version": "2.0.0",
        "active_websockets": len(manager.active_connections),
        "features": ["futures_trading", "real_time_chart", "liquidation_system"]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)