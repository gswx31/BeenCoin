from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.services.price_engine import price_engine
from app.utils.security import decode_access_token
import asyncio

router = APIRouter(prefix="/ws", tags=["websocket"])


@router.websocket("/prices/{symbol}")
async def websocket_prices(websocket: WebSocket, symbol: str, token: str = Query(default=None)):
    if token:
        try:
            decode_access_token(token)
        except Exception:
            await websocket.close(code=4001)
            return

    await websocket.accept()
    price_engine.subscribe(symbol, websocket)
    try:
        while True:
            try:
                # Wait for client messages (ping/pong) with timeout
                await asyncio.wait_for(websocket.receive_text(), timeout=60)
            except asyncio.TimeoutError:
                # Send ping to check if client is alive
                try:
                    await websocket.send_json({"type": "ping"})
                except Exception:
                    break
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        price_engine.unsubscribe(symbol, websocket)
