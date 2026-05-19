"""
티어 시스템 — 수익률 + 거래 횟수 복합 평가.
"""
from decimal import Decimal
from sqlmodel import Session, select, func
from app.models.database import User, TradingAccount, Position, TransactionHistory
from app.core.config import settings

# (key, label, emoji, color, min_return_pct, min_trades, fee_discount_pct)
TIERS = [
    {"key": "bronze",   "label": "브론즈",   "emoji": "🥉", "color": "#cd7f32", "min_return": -100, "min_trades": 0,   "fee_discount": 0},
    {"key": "silver",   "label": "실버",     "emoji": "🥈", "color": "#c0c0c0", "min_return": 5,    "min_trades": 5,   "fee_discount": 5},
    {"key": "gold",     "label": "골드",     "emoji": "🥇", "color": "#ffd700", "min_return": 20,   "min_trades": 20,  "fee_discount": 10},
    {"key": "platinum", "label": "플래티넘", "emoji": "💠", "color": "#7fc8ff", "min_return": 50,   "min_trades": 50,  "fee_discount": 20},
    {"key": "diamond",  "label": "다이아",   "emoji": "💎", "color": "#7ee8c7", "min_return": 100,  "min_trades": 100, "fee_discount": 35},
    {"key": "master",   "label": "마스터",   "emoji": "👑", "color": "#f0b90b", "min_return": 300,  "min_trades": 200, "fee_discount": 50},
]


def calculate_tier(return_pct: float, trade_count: int) -> dict:
    """현재 수익률 + 거래 횟수 → 티어."""
    current = TIERS[0]
    for tier in TIERS:
        if return_pct >= tier["min_return"] and trade_count >= tier["min_trades"]:
            current = tier
    return current


def get_user_tier(session: Session, user_id: int) -> dict:
    """유저의 티어 + 다음 티어 진행도."""
    account = session.exec(
        select(TradingAccount).where(TradingAccount.user_id == user_id)
    ).first()
    if not account:
        return {"tier": TIERS[0], "next_tier": TIERS[1], "progress": 0, "trade_count": 0, "return_pct": 0}

    positions = session.exec(
        select(Position).where(Position.account_id == account.id)
    ).all()
    total_value = float(account.balance) + sum(float(p.current_value) for p in positions)
    initial = float(settings.INITIAL_BALANCE)
    return_pct = ((total_value - initial) / initial) * 100 if initial > 0 else 0

    trade_count = session.exec(
        select(func.count(TransactionHistory.id))
        .where(TransactionHistory.user_id == user_id)
    ).one()

    current = calculate_tier(return_pct, trade_count)
    current_idx = next(i for i, t in enumerate(TIERS) if t["key"] == current["key"])
    next_tier = TIERS[current_idx + 1] if current_idx < len(TIERS) - 1 else None

    # 다음 티어까지 진행도 (수익률 기준)
    progress = 0
    if next_tier:
        return_needed = next_tier["min_return"] - current["min_return"]
        if return_needed > 0:
            progress = min(100, max(0, (return_pct - current["min_return"]) / return_needed * 100))

    return {
        "tier": current,
        "next_tier": next_tier,
        "progress": round(progress, 1),
        "trade_count": trade_count,
        "return_pct": round(return_pct, 2),
    }


def get_tier_list():
    return TIERS
