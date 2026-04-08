"""
Trading Analytics — win rate, risk/reward, best/worst trades, streaks.
"""
from decimal import Decimal
from sqlmodel import Session, select
from app.models.database import TransactionHistory, TradingAccount, Position, Order, User
from app.core.config import settings
from datetime import datetime, timedelta
from collections import defaultdict


def get_analytics(session: Session, user_id: int) -> dict:
    txs = session.exec(
        select(TransactionHistory)
        .where(TransactionHistory.user_id == user_id)
        .order_by(TransactionHistory.timestamp.asc())
    ).all()

    account = session.exec(
        select(TradingAccount).where(TradingAccount.user_id == user_id)
    ).first()

    if not txs or not account:
        return _empty_analytics()

    # -- Sell trades only for PnL analysis --
    sells = [t for t in txs if t.side == 'SELL']
    wins = [t for t in sells if t.realized_pnl > 0]
    losses = [t for t in sells if t.realized_pnl < 0]

    win_count = len(wins)
    loss_count = len(losses)
    total_closed = win_count + loss_count
    win_rate = (win_count / total_closed * 100) if total_closed > 0 else 0

    avg_win = sum(float(t.realized_pnl) for t in wins) / win_count if win_count else 0
    avg_loss = abs(sum(float(t.realized_pnl) for t in losses) / loss_count) if loss_count else 0
    risk_reward = (avg_win / avg_loss) if avg_loss > 0 else 0

    # -- Best / Worst trades --
    sells_sorted = sorted(sells, key=lambda t: float(t.realized_pnl), reverse=True)
    best_trades = [_tx_summary(t) for t in sells_sorted[:5]]
    worst_trades = [_tx_summary(t) for t in sells_sorted[-5:]]

    # -- Total fees paid --
    total_fees = sum(float(t.fee) for t in txs)

    # -- Trade count by symbol --
    symbol_stats = defaultdict(lambda: {"buys": 0, "sells": 0, "volume": 0, "pnl": 0})
    for t in txs:
        s = symbol_stats[t.symbol]
        s["buys" if t.side == "BUY" else "sells"] += 1
        s["volume"] += float(t.price * t.quantity)
        s["pnl"] += float(t.realized_pnl)

    # -- Daily PnL for chart --
    daily_pnl = defaultdict(float)
    for t in sells:
        day = t.timestamp.strftime("%Y-%m-%d")
        daily_pnl[day] += float(t.realized_pnl)

    # Cumulative PnL
    cumulative = []
    running = 0
    for day in sorted(daily_pnl.keys()):
        running += daily_pnl[day]
        cumulative.append({"date": day, "pnl": round(running, 2), "daily": round(daily_pnl[day], 2)})

    # -- Profit factor --
    gross_profit = sum(float(t.realized_pnl) for t in wins)
    gross_loss = abs(sum(float(t.realized_pnl) for t in losses))
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 0

    # -- Drawdown --
    peak = 0
    max_drawdown = 0
    for entry in cumulative:
        if entry["pnl"] > peak:
            peak = entry["pnl"]
        dd = peak - entry["pnl"]
        if dd > max_drawdown:
            max_drawdown = dd

    # -- Streak info --
    user = session.exec(select(User).where(User.id == user_id)).first()

    return {
        "total_trades": len(txs),
        "total_closed": total_closed,
        "win_count": win_count,
        "loss_count": loss_count,
        "win_rate": round(win_rate, 1),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "risk_reward_ratio": round(risk_reward, 2),
        "profit_factor": round(profit_factor, 2),
        "total_fees_paid": round(total_fees, 2),
        "max_drawdown": round(max_drawdown, 2),
        "best_trades": best_trades,
        "worst_trades": worst_trades,
        "symbol_stats": dict(symbol_stats),
        "daily_pnl": cumulative[-30:] if cumulative else [],
        "current_streak": user.current_streak if user else 0,
        "best_streak": user.best_streak if user else 0,
    }


def _tx_summary(t: TransactionHistory) -> dict:
    return {
        "id": t.id,
        "symbol": t.symbol,
        "quantity": str(t.quantity),
        "price": str(t.price),
        "pnl": str(t.realized_pnl),
        "fee": str(t.fee),
        "timestamp": str(t.timestamp),
    }


def _empty_analytics() -> dict:
    return {
        "total_trades": 0, "total_closed": 0,
        "win_count": 0, "loss_count": 0, "win_rate": 0,
        "avg_win": 0, "avg_loss": 0, "risk_reward_ratio": 0,
        "profit_factor": 0, "total_fees_paid": 0, "max_drawdown": 0,
        "best_trades": [], "worst_trades": [],
        "symbol_stats": {}, "daily_pnl": [],
        "current_streak": 0, "best_streak": 0,
    }


def update_streak(session: Session, user_id: int, realized_pnl: Decimal):
    """Call after every SELL trade to update profit streak."""
    user = session.exec(select(User).where(User.id == user_id)).first()
    if not user:
        return
    today = datetime.utcnow().strftime("%Y-%m-%d")
    if realized_pnl > 0:
        if user.last_profit_date == today:
            return  # already counted today
        yesterday = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
        if user.last_profit_date == yesterday:
            user.current_streak += 1
        else:
            user.current_streak = 1
        user.last_profit_date = today
        if user.current_streak > user.best_streak:
            user.best_streak = user.current_streak
    else:
        user.current_streak = 0
    session.add(user)
