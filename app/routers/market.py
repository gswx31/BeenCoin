# app/routers/market.py
import asyncio
from datetime import datetime, timedelta
import logging  # ✅ 추가
import random

from fastapi import APIRouter, HTTPException
import httpx  # ✅ 추가

from app.services.binance_service import get_coin_info, get_historical_data, get_multiple_prices

router = APIRouter(prefix="/market", tags=["market"])
logger = logging.getLogger(__name__)  # ✅ 추가

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
            "1m",
            "3m",
            "5m",
            "15m",
            "30m",
            "1h",
            "2h",
            "4h",
            "6h",
            "8h",
            "12h",
            "1d",
            "3d",
            "1w",
            "1M",
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
        elif limit < 1:
            limit = 24

        data = await get_historical_data(symbol, actual_interval, limit)

        if not data:
            raise HTTPException(status_code=404, detail="No historical data found")

        if use_simulation:
            data = simulate_sub_minute_data(data, interval, limit)

        return data

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


def simulate_sub_minute_data(
    minute_data: list[dict], target_interval: str, target_limit: int
) -> list[dict]:
    """1분 데이터를 기반으로 초 단위 데이터 시뮬레이션"""
    seconds_map = {"1s": 1, "5s": 5, "15s": 15, "30s": 30}
    seconds = seconds_map.get(target_interval, 1)

    simulated = []

    for candle in minute_data:
        num_sub_candles = 60 // seconds
        base_timestamp = datetime.fromisoformat(candle["timestamp"])

        price_range = candle["high"] - candle["low"]
        current_price = candle["open"]

        for i in range(num_sub_candles):
            price_change = random.uniform(-price_range * 0.1, price_range * 0.1)
            next_price = max(candle["low"], min(candle["high"], current_price + price_change))

            if i == num_sub_candles - 1:
                next_price = candle["close"]

            sub_candle = {
                "timestamp": (base_timestamp + timedelta(seconds=i * seconds)).isoformat(),
                "open": current_price,
                "high": max(current_price, next_price) + random.uniform(0, price_range * 0.05),
                "low": min(current_price, next_price) - random.uniform(0, price_range * 0.05),
                "close": next_price,
                "volume": candle["volume"] / num_sub_candles,
            }

            simulated.append(sub_candle)
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
async def get_recent_trades(symbol: str, limit: int = 20):
    """바이낸스 실시간 체결 내역"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://api.binance.com/api/v3/trades", params={"symbol": symbol, "limit": limit}
            )

            if response.status_code == 200:
                trades = response.json()
                return [
                    {
                        "id": trade["id"],
                        "price": float(trade["price"]),
                        "quantity": float(trade["qty"]),
                        "time": datetime.fromtimestamp(trade["time"] / 1000).isoformat(),
                        "isBuyerMaker": trade["isBuyerMaker"],
                    }
                    for trade in trades
                ]
            else:
                raise HTTPException(status_code=503, detail="Binance API 오류")

    except httpx.TimeoutException:
        logger.error(f"❌ Binance trades timeout: {symbol}")
        raise HTTPException(status_code=503, detail="Binance API 타임아웃")
    except Exception as e:
        logger.error(f"❌ Get trades failed: {e}")
        raise HTTPException(status_code=500, detail=f"체결 내역 조회 실패: {str(e)}")
