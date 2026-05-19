from app.services.backtest import BacktestEngine


def _gen_klines(prices):
    return [{"time": i * 3600, "open": p, "high": p, "low": p, "close": p, "volume": 100} for i, p in enumerate(prices)]


def test_buy_hold_uptrend():
    klines = _gen_klines([100, 110, 120, 130, 140])
    engine = BacktestEngine(klines, 10000)
    result = engine.run_buy_hold()
    assert result["return_pct"] > 0
    assert result["trade_count"] == 1


def test_buy_hold_downtrend():
    klines = _gen_klines([100, 90, 80, 70, 60])
    engine = BacktestEngine(klines, 10000)
    result = engine.run_buy_hold()
    assert result["return_pct"] < 0


def test_ma_crossover_no_signals_short_data():
    # MA20/MA60에 필요한 데이터 부족 → 거래 없음
    klines = _gen_klines([100] * 10)
    engine = BacktestEngine(klines, 10000)
    result = engine.run_ma_crossover()
    assert result["trade_count"] == 0


def test_dca_creates_multiple_buys():
    klines = _gen_klines([100 + i for i in range(48)])
    engine = BacktestEngine(klines, 10000)
    result = engine.run_dca(period_candles=12)
    assert result["trade_count"] >= 3


def test_summary_includes_required_keys():
    klines = _gen_klines([100, 105, 110])
    engine = BacktestEngine(klines, 10000)
    result = engine.run_buy_hold()
    for key in ["initial_balance", "final_equity", "return_pct", "buy_hold_return_pct",
                "trade_count", "max_drawdown_pct", "equity_curve"]:
        assert key in result
