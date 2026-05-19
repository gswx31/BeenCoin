"""
백테스팅 엔진 — 과거 캔들 데이터로 전략 시뮬레이션.

지원 전략:
- ma_crossover: 단기 MA가 장기 MA를 상향 돌파 시 매수, 하향 시 매도
- rsi: RSI < oversold 매수, RSI > overbought 매도
- buy_hold: 시작 시 풀매수 후 보유
- dca: 일정 주기로 분할 매수
"""
from typing import List, Dict, Optional
from decimal import Decimal
from app.services.indicators import sma, rsi
from app.services.binance_service import get_client
from app.core.config import settings

FEE_RATE = 0.001


class BacktestEngine:
    def __init__(self, klines: List[dict], initial_balance: float = 100000.0):
        self.klines = klines
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.position_qty = 0.0
        self.avg_cost = 0.0
        self.trades: List[dict] = []
        self.equity_curve: List[dict] = []

    def _buy_all(self, price: float, time: int, reason: str):
        # 가능한 만큼 풀매수
        max_qty = self.balance / (price * (1 + FEE_RATE))
        if max_qty <= 0:
            return
        cost = price * max_qty
        fee = cost * FEE_RATE
        # 평균가 갱신
        new_qty = self.position_qty + max_qty
        self.avg_cost = ((self.avg_cost * self.position_qty) + cost + fee) / new_qty
        self.position_qty = new_qty
        self.balance -= (cost + fee)
        self.trades.append({"time": time, "side": "BUY", "price": price, "qty": max_qty, "reason": reason})

    def _sell_all(self, price: float, time: int, reason: str):
        if self.position_qty <= 0:
            return
        proceeds = price * self.position_qty
        fee = proceeds * FEE_RATE
        pnl = proceeds - fee - (self.avg_cost * self.position_qty)
        self.balance += (proceeds - fee)
        self.trades.append({
            "time": time, "side": "SELL", "price": price,
            "qty": self.position_qty, "reason": reason, "pnl": pnl,
        })
        self.position_qty = 0.0
        self.avg_cost = 0.0

    def _record_equity(self, time: int, price: float):
        equity = self.balance + (self.position_qty * price)
        self.equity_curve.append({"time": time, "equity": equity})

    def run_ma_crossover(self, fast: int = 20, slow: int = 60) -> dict:
        closes = [k["close"] for k in self.klines]
        ma_fast = sma(closes, fast)
        ma_slow = sma(closes, slow)

        for i, k in enumerate(self.klines):
            if i == 0 or ma_fast[i] is None or ma_slow[i] is None or ma_fast[i-1] is None or ma_slow[i-1] is None:
                self._record_equity(k["time"], k["close"])
                continue

            # 골든 크로스: fast가 slow를 상향 돌파
            if ma_fast[i-1] <= ma_slow[i-1] and ma_fast[i] > ma_slow[i] and self.position_qty == 0:
                self._buy_all(k["close"], k["time"], "golden_cross")
            # 데드 크로스: fast가 slow를 하향 돌파
            elif ma_fast[i-1] >= ma_slow[i-1] and ma_fast[i] < ma_slow[i] and self.position_qty > 0:
                self._sell_all(k["close"], k["time"], "death_cross")
            self._record_equity(k["time"], k["close"])
        return self._summary()

    def run_rsi(self, period: int = 14, oversold: float = 30, overbought: float = 70) -> dict:
        closes = [k["close"] for k in self.klines]
        rsi_vals = rsi(closes, period)

        for i, k in enumerate(self.klines):
            if rsi_vals[i] is None:
                self._record_equity(k["time"], k["close"])
                continue
            r = rsi_vals[i]
            if r < oversold and self.position_qty == 0:
                self._buy_all(k["close"], k["time"], f"rsi_{r:.1f}_oversold")
            elif r > overbought and self.position_qty > 0:
                self._sell_all(k["close"], k["time"], f"rsi_{r:.1f}_overbought")
            self._record_equity(k["time"], k["close"])
        return self._summary()

    def run_buy_hold(self) -> dict:
        if not self.klines:
            return self._summary()
        first = self.klines[0]
        self._buy_all(first["close"], first["time"], "initial_buy")
        for k in self.klines:
            self._record_equity(k["time"], k["close"])
        # 마지막에 청산하지 않음 — 보유 상태 유지
        return self._summary()

    def run_dca(self, period_candles: int = 24) -> dict:
        """주기적으로 잔고의 N분의 1씩 매수."""
        if not self.klines:
            return self._summary()
        total_periods = len(self.klines) // period_candles
        if total_periods == 0:
            total_periods = 1
        installment = self.initial_balance / total_periods

        for i, k in enumerate(self.klines):
            if i % period_candles == 0 and self.balance >= installment:
                qty = installment / (k["close"] * (1 + FEE_RATE))
                cost = k["close"] * qty
                fee = cost * FEE_RATE
                new_qty = self.position_qty + qty
                self.avg_cost = ((self.avg_cost * self.position_qty) + cost + fee) / new_qty
                self.position_qty = new_qty
                self.balance -= (cost + fee)
                self.trades.append({"time": k["time"], "side": "BUY", "price": k["close"], "qty": qty, "reason": "dca"})
            self._record_equity(k["time"], k["close"])
        return self._summary()

    def _summary(self) -> dict:
        if not self.klines:
            return {}
        last_price = self.klines[-1]["close"]
        final_equity = self.balance + (self.position_qty * last_price)
        total_return = final_equity - self.initial_balance
        return_pct = (total_return / self.initial_balance) * 100

        # Buy & Hold 비교
        first_price = self.klines[0]["close"]
        bh_return_pct = ((last_price - first_price) / first_price) * 100

        closed_trades = [t for t in self.trades if t["side"] == "SELL" and "pnl" in t]
        wins = [t for t in closed_trades if t["pnl"] > 0]
        win_rate = (len(wins) / len(closed_trades) * 100) if closed_trades else 0

        # 최대 낙폭 (MDD)
        peak = self.initial_balance
        max_dd = 0
        for point in self.equity_curve:
            if point["equity"] > peak:
                peak = point["equity"]
            dd = (peak - point["equity"]) / peak * 100
            if dd > max_dd:
                max_dd = dd

        return {
            "initial_balance": self.initial_balance,
            "final_equity": round(final_equity, 2),
            "total_return": round(total_return, 2),
            "return_pct": round(return_pct, 2),
            "buy_hold_return_pct": round(bh_return_pct, 2),
            "outperformance": round(return_pct - bh_return_pct, 2),
            "trade_count": len(self.trades),
            "closed_trades": len(closed_trades),
            "win_count": len(wins),
            "win_rate": round(win_rate, 1),
            "max_drawdown_pct": round(max_dd, 2),
            "trades": self.trades[-50:],  # 최근 50개만
            "equity_curve": self.equity_curve,
        }


async def fetch_historical_klines(symbol: str, interval: str, limit: int) -> List[dict]:
    if symbol not in settings.SUPPORTED_SYMBOLS:
        raise ValueError("Unsupported symbol")
    client = await get_client()
    raw = await client.get_klines(symbol=symbol, interval=interval, limit=limit)
    return [
        {"time": int(k[0] / 1000), "open": float(k[1]), "high": float(k[2]),
         "low": float(k[3]), "close": float(k[4]), "volume": float(k[5])}
        for k in raw
    ]
