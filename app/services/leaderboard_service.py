"""
Leaderboard — rank users by profit, win rate, streak.
"""
from decimal import Decimal
from sqlmodel import Session, select, func
from app.models.database import User, TradingAccount, Position, TransactionHistory, UserAchievement
from app.core.config import settings


def get_leaderboard(session: Session, sort_by: str = "profit") -> list:
    """
    Rank all users. sort_by: profit | return_rate | streak | achievements
    """
    users = session.exec(select(User).where(User.is_active == True)).all()
    initial = Decimal(str(settings.INITIAL_BALANCE))

    entries = []
    for user in users:
        account = session.exec(
            select(TradingAccount).where(TradingAccount.user_id == user.id)
        ).first()
        if not account:
            continue

        positions = session.exec(
            select(Position).where(Position.account_id == account.id)
        ).all()
        total_value = account.balance + sum(p.current_value for p in positions)
        return_rate = float((total_value - initial) / initial * 100) if initial > 0 else 0

        trade_count = session.exec(
            select(func.count(TransactionHistory.id))
            .where(TransactionHistory.user_id == user.id)
        ).one()

        sell_txs = session.exec(
            select(TransactionHistory).where(
                TransactionHistory.user_id == user.id,
                TransactionHistory.side == "SELL",
            )
        ).all()
        wins = sum(1 for t in sell_txs if t.realized_pnl > 0)
        win_rate = (wins / len(sell_txs) * 100) if sell_txs else 0

        achievement_count = session.exec(
            select(func.count(UserAchievement.id))
            .where(UserAchievement.user_id == user.id)
        ).one()

        entries.append({
            "user_id": user.id,
            "username": user.username,
            "total_profit": float(account.total_profit),
            "total_value": float(total_value),
            "return_rate": round(return_rate, 2),
            "trade_count": trade_count,
            "win_rate": round(win_rate, 1),
            "current_streak": user.current_streak,
            "best_streak": user.best_streak,
            "achievement_count": achievement_count,
        })

    # Sort
    sort_keys = {
        "profit": lambda e: e["total_profit"],
        "return_rate": lambda e: e["return_rate"],
        "streak": lambda e: e["best_streak"],
        "achievements": lambda e: e["achievement_count"],
        "win_rate": lambda e: e["win_rate"],
    }
    key_fn = sort_keys.get(sort_by, sort_keys["profit"])
    entries.sort(key=key_fn, reverse=True)

    # Add rank
    for i, entry in enumerate(entries):
        entry["rank"] = i + 1

    return entries
