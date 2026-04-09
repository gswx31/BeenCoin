from fastapi import APIRouter, Query
from app.services.binance_service import get_client
from app.core.config import settings

router = APIRouter(prefix="/market", tags=["market"])

VALID_INTERVALS = ["1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "12h", "1d", "1w"]


@router.get("/klines")
async def get_klines(
    symbol: str = Query(default="BTCUSDT"),
    interval: str = Query(default="1h"),
    limit: int = Query(default=200, le=500),
):
    if symbol not in settings.SUPPORTED_SYMBOLS:
        return {"error": "Unsupported symbol"}
    if interval not in VALID_INTERVALS:
        return {"error": f"Invalid interval. Use: {VALID_INTERVALS}"}

    client = await get_client()
    klines = await client.get_klines(symbol=symbol, interval=interval, limit=limit)

    return [
        {
            "time": int(k[0] / 1000),  # ms → sec for lightweight-charts
            "open": float(k[1]),
            "high": float(k[2]),
            "low": float(k[3]),
            "close": float(k[4]),
            "volume": float(k[5]),
        }
        for k in klines
    ]
