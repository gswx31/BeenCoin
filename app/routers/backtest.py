from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from app.services.backtest import BacktestEngine, fetch_historical_klines
from app.routers.orders import get_current_user
from typing import Optional

router = APIRouter(prefix="/backtest", tags=["backtest"])


class BacktestRequest(BaseModel):
    symbol: str = "BTCUSDT"
    interval: str = "1h"
    limit: int = Field(default=500, ge=50, le=1000)
    strategy: str  # ma_crossover | rsi | buy_hold | dca
    initial_balance: float = Field(default=100000.0, ge=1000)
    # ma_crossover params
    ma_fast: Optional[int] = 20
    ma_slow: Optional[int] = 60
    # rsi params
    rsi_period: Optional[int] = 14
    rsi_oversold: Optional[float] = 30
    rsi_overbought: Optional[float] = 70
    # dca params
    dca_period_candles: Optional[int] = 24


@router.post("/run")
async def run_backtest(body: BacktestRequest, _=Depends(get_current_user)):
    try:
        klines = await fetch_historical_klines(body.symbol, body.interval, body.limit)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    engine = BacktestEngine(klines, body.initial_balance)

    if body.strategy == "ma_crossover":
        result = engine.run_ma_crossover(body.ma_fast, body.ma_slow)
    elif body.strategy == "rsi":
        result = engine.run_rsi(body.rsi_period, body.rsi_oversold, body.rsi_overbought)
    elif body.strategy == "buy_hold":
        result = engine.run_buy_hold()
    elif body.strategy == "dca":
        result = engine.run_dca(body.dca_period_candles)
    else:
        raise HTTPException(status_code=400, detail="알 수 없는 전략이에요")

    return {
        "strategy": body.strategy,
        "symbol": body.symbol,
        "interval": body.interval,
        **result,
    }


@router.get("/strategies")
async def list_strategies():
    return {
        "strategies": [
            {
                "key": "buy_hold", "name": "단순 보유",
                "description": "시작 시 풀매수 후 종료까지 보유 (벤치마크)",
            },
            {
                "key": "ma_crossover", "name": "이동평균 크로스",
                "description": "단기 MA가 장기 MA를 상향 돌파 시 매수, 하향 시 매도",
                "params": ["ma_fast", "ma_slow"],
            },
            {
                "key": "rsi", "name": "RSI 역추세",
                "description": "RSI 과매도 구간에서 매수, 과매수에서 매도",
                "params": ["rsi_period", "rsi_oversold", "rsi_overbought"],
            },
            {
                "key": "dca", "name": "DCA (적립식 매수)",
                "description": "일정 주기로 잔고를 분할 매수",
                "params": ["dca_period_candles"],
            },
        ]
    }
