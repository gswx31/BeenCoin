# app/routers/websocket.py
"""
WebSocket endpoints for real-time data
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from fastapi.security import HTTPBearer
from sqlmodel import Session
from typing import Dict, List, Optional
import asyncio
import json
import logging
from app.core.database import get_session
from app.services.binance_service import get_current_price, get_orderbook, get_recent_trades
from app.utils.security import decode_access_token
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["WebSocket"])

# 연결된 클라이언트 관리
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.user_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        if client_id not in self.active_connections:
            self.active_connections[client_id] = []
        self.active_connections[client_id].append(websocket)
        logger.info(f"Client {client_id} connected")
    
    def disconnect(self, websocket: WebSocket, client_id: str):
        if client_id in self.active_connections:
            self.active_connections[client_id].remove(websocket)
            if not self.active_connections[client_id]:
                del self.active_connections[client_id]
        logger.info(f"Client {client_id} disconnected")
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)
    
    async def broadcast(self, message: str, channel: str):
        if channel in self.active_connections:
            for connection in self.active_connections[channel]:
                try:
                    await connection.send_text(message)
                except:
                    pass

manager = ConnectionManager()


@router.websocket("/price/{symbol}")
async def websocket_price(
    websocket: WebSocket,
    symbol: str,
    interval: int = Query(1, description="Update interval in seconds")
):
    """
    WebSocket endpoint for real-time price updates
    
    Args:
        symbol: Trading pair symbol
        interval: Update interval in seconds
    """
    await manager.connect(websocket, f"price:{symbol}")
    
    try:
        while True:
            # Get current price
            try:
                price = await get_current_price(symbol)
                
                data = {
                    "type": "price",
                    "symbol": symbol,
                    "price": price,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                await websocket.send_json(data)
                
            except Exception as e:
                logger.error(f"Error fetching price for {symbol}: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": "Failed to fetch price"
                })
            
            await asyncio.sleep(interval)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket, f"price:{symbol}")


@router.websocket("/orderbook/{symbol}")
async def websocket_orderbook(
    websocket: WebSocket,
    symbol: str,
    limit: int = Query(10, description="Number of price levels"),
    interval: int = Query(1, description="Update interval in seconds")
):
    """
    WebSocket endpoint for real-time orderbook updates
    
    Args:
        symbol: Trading pair symbol
        limit: Number of price levels
        interval: Update interval in seconds
    """
    await manager.connect(websocket, f"orderbook:{symbol}")
    
    try:
        while True:
            try:
                orderbook = await get_orderbook(symbol, limit)
                
                data = {
                    "type": "orderbook",
                    "symbol": symbol,
                    "bids": orderbook.get("bids", []),
                    "asks": orderbook.get("asks", []),
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                await websocket.send_json(data)
                
            except Exception as e:
                logger.error(f"Error fetching orderbook for {symbol}: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": "Failed to fetch orderbook"
                })
            
            await asyncio.sleep(interval)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket, f"orderbook:{symbol}")


@router.websocket("/trades/{symbol}")
async def websocket_trades(
    websocket: WebSocket,
    symbol: str,
    limit: int = Query(50, description="Number of recent trades"),
    interval: int = Query(2, description="Update interval in seconds")
):
    """
    WebSocket endpoint for real-time trade updates
    
    Args:
        symbol: Trading pair symbol
        limit: Number of recent trades
        interval: Update interval in seconds
    """
    await manager.connect(websocket, f"trades:{symbol}")
    
    try:
        last_trade_id = None
        
        while True:
            try:
                trades = await get_recent_trades(symbol, limit)
                
                # Filter new trades only
                new_trades = []
                if last_trade_id:
                    for trade in trades:
                        if trade.get("id") > last_trade_id:
                            new_trades.append(trade)
                else:
                    new_trades = trades[:5]  # Send last 5 trades initially
                
                if new_trades:
                    last_trade_id = max(t.get("id", 0) for t in trades)
                    
                    data = {
                        "type": "trades",
                        "symbol": symbol,
                        "trades": new_trades,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    
                    await websocket.send_json(data)
                
            except Exception as e:
                logger.error(f"Error fetching trades for {symbol}: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": "Failed to fetch trades"
                })
            
            await asyncio.sleep(interval)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket, f"trades:{symbol}")


@router.websocket("/user")
async def websocket_user(
    websocket: WebSocket,
    token: str = Query(..., description="JWT token")
):
    """
    WebSocket endpoint for user-specific updates
    
    Args:
        token: JWT authentication token
    """
    try:
        # Verify token
        payload = decode_access_token(token)
        username = payload.get("sub")
        
        if not username:
            await websocket.close(code=1008, reason="Invalid token")
            return
        
        await manager.connect(websocket, f"user:{username}")
        manager.user_connections[username] = websocket
        
        # Send initial connection message
        await websocket.send_json({
            "type": "connected",
            "message": f"Connected as {username}",
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Keep connection alive and handle messages
        while True:
            try:
                # Receive message from client
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle different message types
                if message.get("type") == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                
                elif message.get("type") == "subscribe":
                    # Handle subscription requests
                    channel = message.get("channel")
                    await websocket.send_json({
                        "type": "subscribed",
                        "channel": channel,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON"
                })
                
    except WebSocketDisconnect:
        if username in manager.user_connections:
            del manager.user_connections[username]
        manager.disconnect(websocket, f"user:{username}")
    
    except Exception as e:
        logger.error(f"WebSocket error for user {username}: {e}")
        await websocket.close(code=1011, reason="Internal error")


async def send_order_update(username: str, order_data: dict):
    """
    Send order update to user via WebSocket
    
    Args:
        username: Username
        order_data: Order information
    """
    if username in manager.user_connections:
        websocket = manager.user_connections[username]
        try:
            await websocket.send_json({
                "type": "order_update",
                "data": order_data,
                "timestamp": datetime.utcnow().isoformat()
            })
        except:
            pass


async def send_position_update(username: str, position_data: dict):
    """
    Send position update to user via WebSocket
    
    Args:
        username: Username
        position_data: Position information
    """
    if username in manager.user_connections:
        websocket = manager.user_connections[username]
        try:
            await websocket.send_json({
                "type": "position_update",
                "data": position_data,
                "timestamp": datetime.utcnow().isoformat()
            })
        except:
            pass


async def broadcast_market_update(symbol: str, data: dict):
    """
    Broadcast market update to all subscribers
    
    Args:
        symbol: Symbol
        data: Market data
    """
    message = json.dumps(data)
    await manager.broadcast(message, f"market:{symbol}")