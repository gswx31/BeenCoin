# app/main.py - 개선된 버전
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.core.config import settings
from app.models.database import create_db_and_tables
from app.routers import auth, orders, account, websocket, market
from app.api.v1.endpoints import auth as v1_auth, orders as v1_orders, account as v1_account, market as v1_market
from app.background_tasks.celery_app import celery_app
import asyncio
import json
from typing import Dict, List
from app.services.binance_service import get_multiple_prices

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="실시간 코인 모의투자 플랫폼 - BeenCoin",
    version="2.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 확장된 심볼 리스트
app.extra_symbols = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "DOTUSDT", 
    "LINKUSDT", "LTCUSDT", "BCHUSDT", "XRPUSDT", "EOSUSDT",
    "XLMUSDT", "TRXUSDT", "ETCUSDT", "XTZUSDT", "ATOMUSDT"
]

# 실시간 가격 저장소
app.realtime_prices: Dict[str, float] = {}

# v1 라우터 등록
app.include_router(v1_auth.router, prefix=settings.API_V1_STR)
app.include_router(v1_orders.router, prefix=settings.API_V1_STR)
app.include_router(v1_account.router, prefix=settings.API_V1_STR)
app.include_router(v1_market.router, prefix=settings.API_V1_STR)

# 정적 파일 서빙 (React 빌드 파일)
app.mount("/static", StaticFiles(directory="client/build/static"), name="static")

@app.get("/")
async def serve_frontend():
    return FileResponse("client/build/index.html")

@app.on_event("startup")
async def startup_event():
    create_db_and_tables()
    # 실시간 가격 업데이트 태스크 시작
    asyncio.create_task(update_realtime_prices())

async def update_realtime_prices():
    """실시간으로 모든 코인 가격 업데이트"""
    while True:
        try:
            prices = await get_multiple_prices(app.extra_symbols)
            app.realtime_prices.update(prices)
            await asyncio.sleep(2)  # 2초마다 업데이트
        except Exception as e:
            print(f"가격 업데이트 오류: {e}")
            await asyncio.sleep(5)

@app.get("/health")
async def health_check():
    return {
        "status": "healthy", 
        "realtime_symbols": len(app.realtime_prices),
        "version": "2.0.0"
    }

# 실시간 웹소켓 연결 관리
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast_prices(self, prices: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json({
                    "type": "price_update",
                    "data": prices,
                    "timestamp": datetime.utcnow().isoformat()
                })
            except:
                self.disconnect(connection)

manager = ConnectionManager()

@app.websocket("/ws/realtime")
async def websocket_realtime(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # 최초 연결 시 현재 가격 전송
        await websocket.send_json({
            "type": "initial_prices",
            "data": app.realtime_prices
        })
        
        while True:
            # 클라이언트로부터 메시지 수신 대기
            data = await websocket.receive_text()
            # 하트비트 등 처리 가능
            await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)