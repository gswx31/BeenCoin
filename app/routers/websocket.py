from fastapi import APIRouter, WebSocket, Depends
from app.services.binance_service import get_current_price
from app.routers.orders import get_current_user
from app.core.database import get_session
from sqlmodel import Session
import asyncio

router = APIRouter(prefix="/ws", tags=["websocket"])

@router.websocket("/prices/{symbol}")
async def websocket_prices(websocket: WebSocket, symbol: str, current_user = Depends(get_current_user), session: Session = Depends(get_session)):
    await websocket.accept()
    try:
        while True:
            # 모의 실시간 가격 데이터 전송
            price = await get_current_price(symbol)
            await websocket.send_json({"symbol": symbol, "price": str(price)})
            await asyncio.sleep(1)  # 1초 간격으로 업데이트
    except Exception as e:
        await websocket.close()