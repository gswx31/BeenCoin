from app.services.indicators import sma, ema, rsi, macd, bollinger_bands


def test_sma_basic():
    result = sma([1, 2, 3, 4, 5], 3)
    assert result == [None, None, 2.0, 3.0, 4.0]


def test_sma_insufficient_data():
    result = sma([1, 2], 5)
    assert all(v is None for v in result)


def test_ema_returns_correct_length():
    prices = list(range(1, 30))
    result = ema(prices, 10)
    assert len(result) == len(prices)


def test_rsi_all_gains_returns_100():
    # 계속 상승 → RSI 100
    prices = list(range(1, 30))
    result = rsi(prices, 14)
    assert result[-1] == 100.0


def test_rsi_range():
    import random
    random.seed(42)
    prices = [100 + random.uniform(-5, 5) for _ in range(50)]
    result = rsi(prices, 14)
    # 모든 비-None 값이 0~100 사이
    for v in result:
        if v is not None:
            assert 0 <= v <= 100


def test_macd_output_structure():
    prices = list(range(1, 50))
    result = macd(prices)
    assert "macd" in result
    assert "signal" in result
    assert "histogram" in result
    assert len(result["macd"]) == len(prices)


def test_bollinger_upper_above_lower():
    import random
    random.seed(42)
    prices = [100 + random.uniform(-10, 10) for _ in range(30)]
    bb = bollinger_bands(prices, 20, 2)
    for u, l in zip(bb["upper"], bb["lower"]):
        if u is not None and l is not None:
            assert u > l
