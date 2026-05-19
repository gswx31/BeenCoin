"""
Binance-style order validation: stepSize, minQty, minNotional, tickSize, slippage.
"""
from decimal import Decimal, ROUND_DOWN
from fastapi import HTTPException
from app.core.config import settings
import random


def get_symbol_rules(symbol: str) -> dict:
    rules = settings.SYMBOL_RULES.get(symbol)
    if not rules:
        raise HTTPException(status_code=400, detail=f"지원하지 않는 코인이에요: {symbol}")
    return rules


def validate_quantity(symbol: str, quantity: Decimal):
    rules = get_symbol_rules(symbol)
    min_qty = Decimal(rules["minQty"])
    step_size = Decimal(rules["stepSize"])

    if quantity < min_qty:
        raise HTTPException(
            status_code=400,
            detail=f"최소 주문 수량은 {min_qty}개 이상이에요"
        )

    remainder = (quantity - min_qty) % step_size
    if remainder != Decimal('0'):
        corrected = quantity.quantize(step_size, rounding=ROUND_DOWN)
        raise HTTPException(
            status_code=400,
            detail=f"수량 단위가 맞지 않아요. {corrected}개로 입력해주세요 (단위: {step_size})"
        )


def validate_price(symbol: str, price: Decimal):
    rules = get_symbol_rules(symbol)
    tick_size = Decimal(rules["tickSize"])

    remainder = price % tick_size
    if remainder != Decimal('0'):
        corrected = price.quantize(tick_size, rounding=ROUND_DOWN)
        raise HTTPException(
            status_code=400,
            detail=f"가격 단위가 맞지 않아요. ${corrected}로 입력해주세요 (단위: ${tick_size})"
        )


def validate_min_notional(symbol: str, price: Decimal, quantity: Decimal):
    rules = get_symbol_rules(symbol)
    min_notional = Decimal(rules["minNotional"])
    notional = price * quantity

    if notional < min_notional:
        raise HTTPException(
            status_code=400,
            detail=f"최소 주문 금액은 ${min_notional} 이상이에요"
        )


def simulate_slippage(price: Decimal, side: str) -> Decimal:
    """
    Simulate realistic market order slippage.
    Market buys get slightly worse (higher) price, sells get slightly lower.
    Random component within configured BPS range.
    """
    bps = Decimal(str(settings.SLIPPAGE_BPS))
    # Random slippage between 0 and configured max
    random_factor = Decimal(str(random.uniform(0, float(bps))))
    slippage_pct = random_factor / Decimal('10000')

    if side == 'BUY':
        return price * (Decimal('1') + slippage_pct)
    else:  # SELL
        return price * (Decimal('1') - slippage_pct)


def round_quantity(symbol: str, quantity: Decimal) -> Decimal:
    """Round quantity to valid stepSize."""
    rules = get_symbol_rules(symbol)
    step_size = Decimal(rules["stepSize"])
    return quantity.quantize(step_size, rounding=ROUND_DOWN)


def round_price(symbol: str, price: Decimal) -> Decimal:
    """Round price to valid tickSize."""
    rules = get_symbol_rules(symbol)
    tick_size = Decimal(rules["tickSize"])
    return price.quantize(tick_size, rounding=ROUND_DOWN)
