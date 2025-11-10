from fastapi import APIRouter, WebSocket, Depends
from app.services.binance_service import async_client
from binance import BinanceSocketManager
from app.routers.orders import get_current_user
from app.core.database import get_session
from sqlmodel import Session

router = APIRouter(prefix="/ws", tags=["websocket"])

@router.websocket("/prices/{symbol}")
async def websocket_prices(websocket: WebSocket, symbol: str, current_user = Depends(get_current_user), session: Session = Depends(get_session)):
    await websocket.accept()
    async with BinanceSocketManager(async_client) as bsm:
        ts = bsm.trade_socket(symbol)
        async with ts as tscm:
            while True:
                try:
                    res = await tscm.recv()
                    if 'p' in res:
                        await websocket.send_json({"symbol": symbol, "price": res['p']})
                except Exception as e:
                    await websocket.close()
                    break
