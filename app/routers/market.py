# app/routers/market.py
# =============================================================================
# 마켓 데이터 API - 호가창 엔드포인트 추가
# =============================================================================
import asyncio
from datetime import datetime, timedelta
import logging
import random

from fastapi import APIRouter, HTTPException
import httpx

from app.services.binance_service import (
    get_coin_info,
    get_historical_data,
    get_multiple_prices,
    get_order_book,  # 🆕 추가!
    get_recent_trades,  # 🆕 추가!
)

router = APIRouter(prefix="/market", tags=["market"])
logger = logging.getLogger(__name__)

# 코인 메타데이터
COINS_METADATA = {
    "BTCUSDT": {
        "symbol": "BTCUSDT",
        "name": "Bitcoin",
        "icon": "₿",
        "color": "#F7931A",
        "category": "메이저",
    },
    "ETHUSDT": {
        "symbol": "ETHUSDT",
        "name": "Ethereum",
        "icon": "Ξ",
        "color": "#627EEA",
        "category": "메이저",
    },
    "BNBUSDT": {
        "symbol": "BNBUSDT",
        "name": "Binance Coin",
        "icon": "⎈",
        "color": "#F3BA2F",
        "category": "메이저",
    },
    "ADAUSDT": {
        "symbol": "ADAUSDT",
        "name": "Cardano",
        "icon": "₳",
        "color": "#0033AD",
        "category": "알트코인",
    },
}

# =============================================================================
# 기존 엔드포인트들
# =============================================================================

@router.get("/coins")
async def get_all_coins():
    """모든 지원 코인의 실시간 정보 반환"""
    all_symbols = list(COINS_METADATA.keys())

    try:
        tasks = [get_coin_info(symbol) for symbol in all_symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        coins_with_data = []
        for i, symbol in enumerate(all_symbols):
            coin_data = COINS_METADATA[symbol].copy()

            if not isinstance(results[i], Exception) and results[i]:
                info = results[i]
                coin_data["price"] = info.get("price", "0")
                coin_data["change"] = info.get("change", "0")
                coin_data["volume"] = info.get("volume", "0")
                coin_data["high"] = info.get("high", "0")
                coin_data["low"] = info.get("low", "0")
            else:
                coin_data["price"] = "0"
                coin_data["change"] = "0"
                coin_data["volume"] = "0"
                coin_data["high"] = "0"
                coin_data["low"] = "0"

            coins_with_data.append(coin_data)

        return coins_with_data

    except Exception as e:
        logger.error(f"Error in get_all_coins: {e}")
        return [
            {**meta, "price": "0", "change": "0", "volume": "0"} for meta in COINS_METADATA.values()
        ]

@router.get("/coin/{symbol}")
async def get_coin_detail(symbol: str):
    """특정 코인의 상세 정보"""
    try:
        info = await get_coin_info(symbol)
        if not info:
            raise HTTPException(status_code=404, detail="Coin not found")

        if symbol in COINS_METADATA:
            info.update(COINS_METADATA[symbol])

        return info
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/historical/{symbol}")
async def get_historical_prices(symbol: str, interval: str = "1h", limit: int = 24):
    """과거 가격 데이터"""
    try:
        valid_binance_intervals = [
            "1m", "3m", "5m", "15m", "30m",
            "1h", "2h", "4h", "6h", "8h", "12h",
            "1d", "3d", "1w", "1M",
        ]
        simulated_intervals = ["1s", "5s", "15s", "30s"]

        actual_interval = interval
        use_simulation = False

        if interval in simulated_intervals:
            actual_interval = "1m"
            use_simulation = True
        elif interval not in valid_binance_intervals:
            actual_interval = "1h"

        if limit > 1000:
            limit = 1000

        data = await get_historical_data(symbol, actual_interval, limit)

        if use_simulation:
            data = simulate_short_intervals(data, interval, limit)

        return data

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

def simulate_short_intervals(original_data: list, target_interval: str, target_limit: int):
    """1초/5초/15초/30초 인터벌 시뮬레이션"""
    if not original_data:
        return []

    interval_seconds = {
        "1s": 1,
        "5s": 5,
        "15s": 15,
        "30s": 30,
    }

    seconds = interval_seconds.get(target_interval, 60)
    simulated = []

    for i in range(len(original_data) - 1):
        current = original_data[i]
        next_candle = original_data[i + 1]

        start_price = float(current["close"])
        end_price = float(next_candle["open"])

        steps = 60 // seconds

        for step in range(steps):
            progress = (step + 1) / steps
            interpolated_price = start_price + (end_price - start_price) * progress
            next_price = interpolated_price + random.uniform(-10, 10)

            simulated.append({
                "time": current["time"] + step * seconds * 1000,
                "open": current_price if step == 0 else simulated[-1]["close"],
                "high": max(interpolated_price, next_price),
                "low": min(interpolated_price, next_price),
                "close": next_price,
                "volume": float(current["volume"]) / steps,
            })

            current_price = next_price

            if len(simulated) >= target_limit:
                break

        if len(simulated) >= target_limit:
            break

    return simulated[-target_limit:]

@router.get("/prices")
async def get_all_prices():
    """모든 지원 코인의 현재 가격만 조회"""
    try:
        all_symbols = list(COINS_METADATA.keys())
        prices = await get_multiple_prices(all_symbols)
        return {symbol: str(price) for symbol, price in prices.items()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/trades/{symbol}")
async def get_recent_trades_api(symbol: str, limit: int = 20):
    """바이낸스 실시간 체결 내역"""
    try:
        trades = await get_recent_trades(symbol, limit)

        if not trades:
            raise HTTPException(status_code=503, detail="체결 내역을 가져올 수 없습니다")

        return trades

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Get trades failed: {e}")
        raise HTTPException(status_code=500, detail=f"체결 내역 조회 실패: {str(e)}")

# =============================================================================
# 🆕 새로운 엔드포인트: 호가창
# =============================================================================

@router.get("/orderbook/{symbol}")
async def get_orderbook_api(symbol: str, limit: int = 20):
    """
    호가창 조회

    Parameters:
    - symbol: 거래 심볼 (예: BTCUSDT)
    - limit: 호가 개수 (5, 10, 20, 50, 100, 500, 1000, 5000)

    Returns:
    - bids: 매수 호가 [[가격, 수량], ...]
    - asks: 매도 호가 [[가격, 수량], ...]
    """
    try:
        # 유효한 limit 값 체크
        valid_limits = [5, 10, 20, 50, 100, 500, 1000, 5000]
        if limit not in valid_limits:
            # 가장 가까운 유효한 값으로 조정
            limit = min(valid_limits, key=lambda x: abs(x - limit))

        # binance_service의 get_order_book 호출
        order_book = await get_order_book(symbol, limit)

        if not order_book or (not order_book.get("bids") and not order_book.get("asks")):
            raise HTTPException(status_code=503, detail="호가 데이터를 가져올 수 없습니다")

        # Decimal을 float로 변환 (JSON 직렬화 위해)
        return {
            "bids": [[float(price), float(qty)] for price, qty in order_book["bids"]],
            "asks": [[float(price), float(qty)] for price, qty in order_book["asks"]],
            "timestamp": datetime.utcnow().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Get orderbook failed: {e}")
        raise HTTPException(status_code=500, detail=f"호가창 조회 실패: {str(e)}")
