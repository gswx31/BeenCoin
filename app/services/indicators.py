"""
기술적 지표 계산 — 이동평균, RSI, MACD, 볼린저밴드.
순수 파이썬 (numpy/pandas 의존 없음).
"""
from typing import List, Optional


def sma(prices: List[float], period: int) -> List[Optional[float]]:
    """단순 이동평균 (Simple Moving Average)."""
    result = []
    for i in range(len(prices)):
        if i < period - 1:
            result.append(None)
        else:
            window = prices[i - period + 1: i + 1]
            result.append(sum(window) / period)
    return result


def ema(prices: List[float], period: int) -> List[Optional[float]]:
    """지수 이동평균 (Exponential Moving Average)."""
    if not prices:
        return []
    k = 2 / (period + 1)
    result = [None] * (period - 1)
    if len(prices) < period:
        return [None] * len(prices)
    # 첫 EMA는 SMA로 시작
    sma_first = sum(prices[:period]) / period
    result.append(sma_first)
    for i in range(period, len(prices)):
        prev = result[-1]
        result.append(prices[i] * k + prev * (1 - k))
    return result


def rsi(prices: List[float], period: int = 14) -> List[Optional[float]]:
    """RSI (Relative Strength Index, 0~100)."""
    if len(prices) < period + 1:
        return [None] * len(prices)

    deltas = [prices[i + 1] - prices[i] for i in range(len(prices) - 1)]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]

    result = [None] * (period)  # first `period` values undefined

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    if avg_loss == 0:
        result.append(100.0)
    else:
        rs = avg_gain / avg_loss
        result.append(100 - (100 / (1 + rs)))

    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0:
            result.append(100.0)
        else:
            rs = avg_gain / avg_loss
            result.append(100 - (100 / (1 + rs)))

    return result


def macd(prices: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> dict:
    """MACD = EMA(fast) - EMA(slow), Signal = EMA(MACD, signal)."""
    fast_ema = ema(prices, fast)
    slow_ema = ema(prices, slow)
    macd_line = [
        (f - s) if (f is not None and s is not None) else None
        for f, s in zip(fast_ema, slow_ema)
    ]
    # Signal line: EMA of macd_line (None 제외하고 계산)
    valid_macd = [v for v in macd_line if v is not None]
    signal_calc = ema(valid_macd, signal) if len(valid_macd) >= signal else []
    # 앞쪽 None 패딩
    pad = len(macd_line) - len(signal_calc)
    signal_line = [None] * pad + signal_calc

    histogram = [
        (m - s) if (m is not None and s is not None) else None
        for m, s in zip(macd_line, signal_line)
    ]
    return {"macd": macd_line, "signal": signal_line, "histogram": histogram}


def bollinger_bands(prices: List[float], period: int = 20, num_std: float = 2.0) -> dict:
    """볼린저 밴드: 중심선(SMA) ± num_std * 표준편차."""
    middle = sma(prices, period)
    upper, lower = [], []
    for i in range(len(prices)):
        if i < period - 1:
            upper.append(None)
            lower.append(None)
        else:
            window = prices[i - period + 1: i + 1]
            mean = middle[i]
            variance = sum((x - mean) ** 2 for x in window) / period
            std = variance ** 0.5
            upper.append(mean + num_std * std)
            lower.append(mean - num_std * std)
    return {"middle": middle, "upper": upper, "lower": lower}


def calculate_all(klines: List[dict]) -> dict:
    """캔들 데이터에서 모든 지표를 한번에 계산."""
    closes = [k["close"] for k in klines]
    times = [k["time"] for k in klines]

    def to_series(values):
        return [
            {"time": t, "value": v}
            for t, v in zip(times, values)
            if v is not None
        ]

    ma20 = sma(closes, 20)
    ma60 = sma(closes, 60)
    ma120 = sma(closes, 120)
    rsi_vals = rsi(closes, 14)
    macd_data = macd(closes)
    bb = bollinger_bands(closes, 20, 2)

    return {
        "ma20": to_series(ma20),
        "ma60": to_series(ma60),
        "ma120": to_series(ma120),
        "rsi": to_series(rsi_vals),
        "macd": to_series(macd_data["macd"]),
        "macd_signal": to_series(macd_data["signal"]),
        "macd_histogram": to_series(macd_data["histogram"]),
        "bb_upper": to_series(bb["upper"]),
        "bb_middle": to_series(bb["middle"]),
        "bb_lower": to_series(bb["lower"]),
    }
