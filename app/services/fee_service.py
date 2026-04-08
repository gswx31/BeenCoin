"""
Binance-realistic fee calculation service.

Fee tiers: Based on 30-day trading volume.
Maker/Taker: Limit orders = maker (add liquidity), Market orders = taker (remove liquidity).
BNB discount: 25% off when user opts in to pay fees in BNB.
"""
from decimal import Decimal, ROUND_DOWN
from sqlmodel import Session, select
from app.models.database import TradingAccount
from app.core.config import settings


def get_fee_tier(volume_30d: Decimal) -> dict:
    """Determine fee tier based on 30-day trading volume."""
    tier = settings.FEE_TIERS[0]
    for t in settings.FEE_TIERS:
        if volume_30d >= Decimal(str(t["min_volume"])):
            tier = t
    return tier


def calculate_fee(
    price: Decimal,
    quantity: Decimal,
    is_maker: bool,
    account: TradingAccount,
) -> tuple:
    """
    Calculate fee like Binance.
    Returns: (fee_amount, fee_rate, fee_asset, is_bnb_discount)
    """
    tier = get_fee_tier(account.trading_volume_30d)
    rate_str = tier["maker"] if is_maker else tier["taker"]
    fee_rate = Decimal(rate_str) / Decimal('100')  # Convert percentage to decimal

    notional = price * quantity
    fee = notional * fee_rate

    # BNB discount
    is_bnb_discount = False
    fee_asset = "USDT"
    if account.use_bnb_fee:
        discount = Decimal(str(settings.BNB_FEE_DISCOUNT))
        fee = fee * (Decimal('1') - discount)
        is_bnb_discount = True
        fee_asset = "BNB"

    fee = fee.quantize(Decimal('0.00000001'), rounding=ROUND_DOWN)
    return fee, fee_rate, fee_asset, is_bnb_discount


def update_trading_volume(session: Session, account: TradingAccount, notional: Decimal):
    """Add trade notional to 30-day rolling volume and update fee tier."""
    account.trading_volume_30d += notional
    tier = get_fee_tier(account.trading_volume_30d)
    account.fee_tier = tier["label"]
    session.add(account)


def get_fee_info(account: TradingAccount) -> dict:
    """Return current fee tier info for display."""
    tier = get_fee_tier(account.trading_volume_30d)
    maker = Decimal(tier["maker"])
    taker = Decimal(tier["taker"])
    if account.use_bnb_fee:
        discount = Decimal(str(settings.BNB_FEE_DISCOUNT))
        maker = maker * (Decimal('1') - discount)
        taker = taker * (Decimal('1') - discount)
    return {
        "tier": tier["label"],
        "maker_fee": str(maker) + "%",
        "taker_fee": str(taker) + "%",
        "bnb_discount": account.use_bnb_fee,
        "volume_30d": str(account.trading_volume_30d),
    }
