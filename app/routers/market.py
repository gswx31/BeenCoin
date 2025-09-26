# app/routers/market.py
from fastapi import APIRouter, HTTPException
from app.services.binance_service import get_coin_info, get_historical_data
from app.core.config import settings
from typing import List, Dict
import json

router = APIRouter(prefix="/market", tags=["market"])

@router.get("/coins")
async def get_all_coins():
    """모든 코인 기본 정보 반환"""
    coins = [
        {
            "symbol": "BTCUSDT",
            "name": "Bitcoin",
            "icon": "₿",
            "color": "#F7931A",
            "category": "메이저"
        },
        {
            "symbol": "ETHUSDT", 
            "name": "Ethereum",
            "icon": "Ξ",
            "color": "#627EEA",
            "category": "메이저"
        },
        {
            "symbol": "BNBUSDT",
            "name": "Binance Coin", 
            "icon": "⎈",
            "color": "#F3BA2F",
            "category": "메이저"
        },
        {
            "symbol": "ADAUSDT",
            "name": "Cardano",
            "icon": "A",
            "color": "#0033AD", 
            "category": "알트코인"
        }
    ]
    return coins

@router.get("/historical/{symbol}")
async def get_historical_prices(symbol: str, interval: str = "1h", limit: int = 24):
    """과거 가격 데이터"""
    try:
        data = await get_historical_data(symbol, interval, limit)
        return data
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))