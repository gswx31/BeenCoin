"""
Achievement system — define achievements, check conditions, award.
"""
from decimal import Decimal
from sqlmodel import Session, select, func
from app.models.database import (
    UserAchievement, TransactionHistory, TradingAccount, Position, Order, User,
)

# -- Achievement Definitions --
ACHIEVEMENTS = {
    # Key: (title, description, icon, rarity)
    "first_trade":       ("First Blood",        "Execute your first trade",                   "zap",    "common"),
    "trade_10":          ("Getting Started",     "Complete 10 trades",                         "chart",  "common"),
    "trade_50":          ("Active Trader",       "Complete 50 trades",                         "chart",  "uncommon"),
    "trade_100":         ("Trading Machine",     "Complete 100 trades",                        "chart",  "rare"),
    "first_profit":      ("In The Green",        "Close your first profitable trade",          "dollar", "common"),
    "profit_1k":         ("Thousandaire",        "Earn $1,000 in total profit",                "dollar", "uncommon"),
    "profit_10k":        ("Money Maker",         "Earn $10,000 in total profit",               "dollar", "rare"),
    "profit_100k":       ("Big Leagues",         "Earn $100,000 in total profit",              "dollar", "epic"),
    "millionaire":       ("Millionaire",         "Total assets exceed $2,000,000",             "crown",  "legendary"),
    "diamond_hands":     ("Diamond Hands",       "Hold a position for 7+ days",                "gem",    "uncommon"),
    "diversified":       ("Diversified",         "Hold 3+ different coins simultaneously",     "pie",    "uncommon"),
    "sniper":            ("Sniper",              "5 limit orders filled in a row",             "target", "rare"),
    "streak_3":          ("On Fire",             "3-day profit streak",                        "fire",   "common"),
    "streak_7":          ("Unstoppable",         "7-day profit streak",                        "fire",   "uncommon"),
    "streak_14":         ("Legendary Streak",    "14-day profit streak",                       "fire",   "rare"),
    "loss_recovery":     ("Comeback Kid",        "Recover from $10K+ loss to profit",          "arrow",  "rare"),
    "whale":             ("Whale Alert",         "Single trade worth $100,000+",               "whale",  "epic"),
    "night_owl":         ("Night Owl",           "Trade between 12AM-5AM",                     "moon",   "common"),
    "early_bird":        ("Early Bird",          "Trade between 5AM-7AM",                      "sun",    "common"),
    "all_coins":         ("Collector",           "Trade all available coins at least once",    "grid",   "uncommon"),
    "smart_fees":        ("Fee Saver",           "Reach VIP 1 fee tier",                       "percent","uncommon"),
    "stop_loss_save":    ("Risk Manager",        "A stop-loss order saves you from bigger loss","shield","rare"),
    "perfect_week":      ("Perfect Week",        "7 profitable trades in a row",               "star",   "epic"),
}

RARITY_ORDER = {"common": 0, "uncommon": 1, "rare": 2, "epic": 3, "legendary": 4}


def get_achievement_list() -> list:
    """Return all possible achievements with metadata."""
    return [
        {"key": k, "title": v[0], "description": v[1], "icon": v[2], "rarity": v[3]}
        for k, v in ACHIEVEMENTS.items()
    ]


def get_user_achievements(session: Session, user_id: int) -> dict:
    """Return all achievements with unlock status."""
    unlocked = session.exec(
        select(UserAchievement).where(UserAchievement.user_id == user_id)
    ).all()
    unlocked_map = {a.achievement_key: str(a.unlocked_at) for a in unlocked}

    result = []
    for key, (title, desc, icon, rarity) in ACHIEVEMENTS.items():
        result.append({
            "key": key,
            "title": title,
            "description": desc,
            "icon": icon,
            "rarity": rarity,
            "unlocked": key in unlocked_map,
            "unlocked_at": unlocked_map.get(key),
        })

    result.sort(key=lambda a: (0 if a["unlocked"] else 1, RARITY_ORDER.get(a["rarity"], 0)))
    return {
        "achievements": result,
        "unlocked_count": len(unlocked_map),
        "total_count": len(ACHIEVEMENTS),
    }


def check_and_award(session: Session, user_id: int, context: dict = None) -> list:
    """
    Check all achievement conditions and award new ones.
    Call this after trades, on login, etc.
    Returns list of newly unlocked achievement keys.
    """
    context = context or {}
    existing = set(
        a.achievement_key for a in session.exec(
            select(UserAchievement).where(UserAchievement.user_id == user_id)
        ).all()
    )

    newly_unlocked = []

    def _award(key):
        if key not in existing and key in ACHIEVEMENTS:
            session.add(UserAchievement(user_id=user_id, achievement_key=key))
            newly_unlocked.append(key)
            existing.add(key)

    # Gather stats
    trade_count = session.exec(
        select(func.count(TransactionHistory.id))
        .where(TransactionHistory.user_id == user_id)
    ).one()

    account = session.exec(
        select(TradingAccount).where(TradingAccount.user_id == user_id)
    ).first()

    user = session.exec(select(User).where(User.id == user_id)).first()

    # -- Trade count milestones --
    if trade_count >= 1:
        _award("first_trade")
    if trade_count >= 10:
        _award("trade_10")
    if trade_count >= 50:
        _award("trade_50")
    if trade_count >= 100:
        _award("trade_100")

    # -- Profit milestones --
    if account:
        total_profit = float(account.total_profit)
        if total_profit > 0:
            _award("first_profit")
        if total_profit >= 1000:
            _award("profit_1k")
        if total_profit >= 10000:
            _award("profit_10k")
        if total_profit >= 100000:
            _award("profit_100k")

        total_value = float(account.balance) + sum(
            float(p.current_value) for p in session.exec(
                select(Position).where(Position.account_id == account.id)
            ).all()
        )
        if total_value >= 2000000:
            _award("millionaire")

        # VIP tier
        if account.fee_tier != "Regular":
            _award("smart_fees")

    # -- Diversification --
    if account:
        position_count = session.exec(
            select(func.count(Position.id))
            .where(Position.account_id == account.id)
        ).one()
        if position_count >= 3:
            _award("diversified")

    # -- Streak --
    if user:
        if user.current_streak >= 3:
            _award("streak_3")
        if user.current_streak >= 7:
            _award("streak_7")
        if user.current_streak >= 14:
            _award("streak_14")

    # -- All coins traded --
    traded_symbols = set(
        t.symbol for t in session.exec(
            select(TransactionHistory).where(TransactionHistory.user_id == user_id)
        ).all()
    )
    from app.core.config import settings
    if traded_symbols >= set(settings.SUPPORTED_SYMBOLS):
        _award("all_coins")

    # -- Whale trade --
    if context.get("trade_notional", 0) >= 100000:
        _award("whale")

    # -- Time-based --
    hour = context.get("trade_hour")
    if hour is not None:
        if 0 <= hour < 5:
            _award("night_owl")
        if 5 <= hour < 7:
            _award("early_bird")

    # -- Sniper (5 consecutive limit fills) --
    recent_orders = session.exec(
        select(Order)
        .where(Order.user_id == user_id, Order.order_type == "LIMIT", Order.order_status.in_(["FILLED", "CANCELLED"]))
        .order_by(Order.updated_at.desc())
    ).all()
    if len(recent_orders) >= 5:
        last_5 = recent_orders[:5]
        if all(o.order_status == "FILLED" for o in last_5):
            _award("sniper")

    # -- Perfect week (7 profitable trades in a row) --
    recent_sells = session.exec(
        select(TransactionHistory)
        .where(TransactionHistory.user_id == user_id, TransactionHistory.side == "SELL")
        .order_by(TransactionHistory.timestamp.desc())
    ).all()
    if len(recent_sells) >= 7:
        if all(t.realized_pnl > 0 for t in recent_sells[:7]):
            _award("perfect_week")

    if newly_unlocked:
        session.commit()

    return newly_unlocked
