from app.core.config import settings
from fastapi import HTTPException
import asyncio
from typing import Callable
from decimal import Decimal
import random
from datetime import datetime, timedelta

# 모의(mock) 구현 - 실제 Binance API 없이 테스트 가능
async def get_current_price(symbol: str) -> Decimal:
    try:
        # 모의 가격 생성 (실제 API 대신)
        mock_prices = {
            "BTCUSDT": Decimal('50000.00'),
            "ETHUSDT": Decimal('3000.00'), 
            "BNBUSDT": Decimal('400.00')
        }
        price = mock_prices.get(symbol, Decimal('100.00'))
        # 약간의 변동성 추가
        variation = random.uniform(0.95, 1.05)
        return price * Decimal(str(variation))
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Binance API error: {str(e)}")

async def monitor_limit_order(order_id: int, symbol: str, side: str, price: Decimal, quantity: Decimal, callback: Callable):
    # 모의 구현 - 실제 웹소켓 대신 타이머 사용
    try:
        await asyncio.sleep(2)  # 2초 후에 체결되는 것으로 시뮬레이션
        await callback(order_id, quantity, price)
    except Exception as e:
        print(f"WebSocket error for order {order_id}: {str(e)}")

async def execute_market_order(symbol: str, side: str, quantity: Decimal) -> Decimal:
    price = await get_current_price(symbol)
    return price

async def get_coin_info(symbol: str):
    """코인 기본 정보 반환 (모의 구현)"""
    coin_info = {
        "BTCUSDT": {
            "symbol": "BTCUSDT",
            "name": "Bitcoin",
            "price": "50000.00",
            "change": "2.5",
            "volume": "2500000000"
        },
        "ETHUSDT": {
            "symbol": "ETHUSDT", 
            "name": "Ethereum",
            "price": "3000.00",
            "change": "1.8", 
            "volume": "1500000000"
        },
        "BNBUSDT": {
            "symbol": "BNBUSDT",
            "name": "Binance Coin",
            "price": "400.00",
            "change": "0.5",
            "volume": "500000000"
        },
        "ADAUSDT": {
            "symbol": "ADAUSDT",
            "name": "Cardano", 
            "price": "0.45",
            "change": "-0.3",
            "volume": "200000000"
        }
    }
    return coin_info.get(symbol, {})

async def get_historical_data(symbol: str, interval: str = "1h", limit: int = 24):
    """과거 가격 데이터 (모의 구현)"""
    base_price = {
        "BTCUSDT": 50000,
        "ETHUSDT": 3000,
        "BNBUSDT": 400,
        "ADAUSDT": 0.45
    }.get(symbol, 100)
    
    historical_data = []
    current_time = datetime.utcnow()
    
    for i in range(limit):
        # 랜덤 변동성으로 가격 생성
        variation = random.uniform(0.98, 1.02)
        price = base_price * variation
        
        timestamp = current_time - timedelta(hours=i)
        
        historical_data.append({
            "timestamp": timestamp.isoformat(),
            "open": float(price * random.uniform(0.99, 1.01)),
            "high": float(price * random.uniform(1.01, 1.03)),
            "low": float(price * random.uniform(0.97, 0.99)),
            "close": float(price),
            "volume": random.uniform(1000000, 5000000)
        })
    
    return historical_data[::-1]  # 시간순으로 정렬

async def get_multiple_prices(symbols: list):
    """여러 심볼의 현재 가격 한번에 조회"""
    prices = {}
    for symbol in symbols:
        prices[symbol] = await get_current_price(symbol)
    return prices