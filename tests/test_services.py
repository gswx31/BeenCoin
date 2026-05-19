"""서비스 레이어 단위 테스트 — DB/API 없이 순수 로직만."""
from decimal import Decimal
from app.services.fee_service import get_fee_tier, calculate_fee
from app.services.order_validator import (
    validate_quantity, validate_price, validate_min_notional, simulate_slippage, round_price,
)
from app.models.database import TradingAccount
from fastapi import HTTPException
import pytest


def test_fee_tier_regular():
    tier = get_fee_tier(Decimal("0"))
    assert tier["label"] == "Regular"


def test_fee_tier_vip1():
    tier = get_fee_tier(Decimal("2000000"))
    assert tier["label"] == "VIP 1"


def test_fee_tier_max():
    tier = get_fee_tier(Decimal("200000000"))
    assert tier["label"] == "VIP 5"


def test_calculate_fee_taker():
    acc = TradingAccount(user_id=1, balance=Decimal("1000000"))
    fee, rate, asset, bnb = calculate_fee(Decimal("100"), Decimal("10"), is_maker=False, account=acc)
    # 100 * 10 * 0.001 = 1
    assert fee == Decimal("1.00000000")
    assert asset == "USDT"


def test_calculate_fee_bnb_discount():
    acc = TradingAccount(user_id=1, balance=Decimal("1000000"), use_bnb_fee=True)
    fee, _, asset, _ = calculate_fee(Decimal("100"), Decimal("10"), is_maker=False, account=acc)
    # 100 * 10 * 0.001 * 0.75 = 0.75
    assert fee == Decimal("0.75000000")
    assert "BNB" in asset


def test_validate_quantity_below_min():
    with pytest.raises(HTTPException) as exc:
        validate_quantity("BTCUSDT", Decimal("0.00000001"))
    assert exc.value.status_code == 400


def test_validate_quantity_valid():
    validate_quantity("BTCUSDT", Decimal("0.001"))  # no exception


def test_validate_min_notional_below():
    with pytest.raises(HTTPException):
        validate_min_notional("BTCUSDT", Decimal("100"), Decimal("0.00001"))  # 0.001 << 10


def test_validate_min_notional_ok():
    validate_min_notional("BTCUSDT", Decimal("50000"), Decimal("0.001"))  # 50 >= 10


def test_slippage_buy_increases_price():
    base = Decimal("100")
    slipped = simulate_slippage(base, "BUY")
    assert slipped >= base  # buy always pays more (or same with random=0)


def test_slippage_sell_decreases_price():
    base = Decimal("100")
    slipped = simulate_slippage(base, "SELL")
    assert slipped <= base


def test_round_price_btc():
    rounded = round_price("BTCUSDT", Decimal("50123.456789"))
    # BTC tickSize: 0.01
    assert rounded == Decimal("50123.45")
