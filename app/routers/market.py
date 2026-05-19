from fastapi import APIRouter, Query, HTTPException
from app.services.binance_service import get_client
from app.services.indicators import calculate_all
from app.core.config import settings

router = APIRouter(prefix="/market", tags=["market"])

VALID_INTERVALS = ["1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "12h", "1d", "1w"]


async def _fetch_klines(symbol: str, interval: str, limit: int):
    if symbol not in settings.SUPPORTED_SYMBOLS:
        raise HTTPException(status_code=400, detail="Unsupported symbol")
    if interval not in VALID_INTERVALS:
        raise HTTPException(status_code=400, detail=f"Invalid interval")

    client = await get_client()
    klines = await client.get_klines(symbol=symbol, interval=interval, limit=limit)
    return [
        {
            "time": int(k[0] / 1000),
            "open": float(k[1]),
            "high": float(k[2]),
            "low": float(k[3]),
            "close": float(k[4]),
            "volume": float(k[5]),
        }
        for k in klines
    ]


@router.get("/klines")
async def get_klines(
    symbol: str = Query(default="BTCUSDT"),
    interval: str = Query(default="1h"),
    limit: int = Query(default=200, le=500),
):
    return await _fetch_klines(symbol, interval, limit)


@router.get("/indicators")
async def get_indicators(
    symbol: str = Query(default="BTCUSDT"),
    interval: str = Query(default="1h"),
    limit: int = Query(default=300, le=500),
):
    """캔들 데이터 기반 기술적 지표 — MA, RSI, MACD, 볼린저밴드."""
    klines = await _fetch_klines(symbol, interval, limit)
    indicators = calculate_all(klines)
    return {"klines": klines, "indicators": indicators}
