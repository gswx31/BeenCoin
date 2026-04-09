"""
Daily Mission system — rotating challenges with bonus rewards.
"""
from decimal import Decimal
from datetime import datetime
from sqlmodel import Session, select
from app.models.database import UserMission, TradingAccount, TransactionHistory
import hashlib

# -- Mission Definitions --
# key: (title, description, target_value, reward_usd)
MISSIONS = {
    "trade_3":       ("Triple Threat",    "Execute 3 trades today",                      3,  500),
    "trade_5":       ("High Volume",      "Execute 5 trades today",                      5,  1000),
    "profit_trade":  ("Green Day",        "Close at least 1 profitable trade today",     1,  300),
    "profit_500":    ("Profit Hunter",    "Earn $500+ in realized profit today",         500, 1500),
    "buy_eth":       ("ETH Believer",     "Buy ETH today",                               1,  200),
    "buy_bnb":       ("BNB Fan",          "Buy BNB today",                               1,  200),
    "limit_order":   ("Patient Trader",   "Place a limit order today",                   1,  300),
    "sell_profit":   ("Take Profit",      "Sell a position at profit today",             1,  400),
    "trade_all":     ("Full Rotation",    "Trade all 3 coins today",                     3,  2000),
    "volume_10k":    ("Whale Day",        "Trade $10,000+ in volume today",              10000, 800),
}

# Each day, pick 3 missions using date as seed
DAILY_MISSION_COUNT = 3


def _get_daily_keys(date_str: str) -> list:
    """Deterministic daily mission selection based on date."""
    keys = sorted(MISSIONS.keys())
    seed = int(hashlib.md5(date_str.encode()).hexdigest(), 16)
    selected = []
    remaining = list(keys)
    for i in range(DAILY_MISSION_COUNT):
        idx = (seed + i * 7) % len(remaining)
        selected.append(remaining.pop(idx))
    return selected


def get_daily_missions(session: Session, user_id: int) -> list:
    """Get today's missions for user, creating them if needed."""
    today = datetime.utcnow().strftime("%Y-%m-%d")
    daily_keys = _get_daily_keys(today)

    existing = session.exec(
        select(UserMission).where(
            UserMission.user_id == user_id,
            UserMission.mission_date == today,
        )
    ).all()
    existing_map = {m.mission_key: m for m in existing}

    # Create missing missions for today
    for key in daily_keys:
        if key not in existing_map:
            title, desc, target, reward = MISSIONS[key]
            mission = UserMission(
                user_id=user_id,
                mission_key=key,
                mission_date=today,
                target_value=target,
                reward_amount=Decimal(str(reward)),
            )
            session.add(mission)
    if len(existing_map) < len(daily_keys):
        session.commit()

    # Re-fetch
    missions = session.exec(
        select(UserMission).where(
            UserMission.user_id == user_id,
            UserMission.mission_date == today,
        )
    ).all()

    result = []
    for m in missions:
        if m.mission_key in MISSIONS:
            title, desc, target, reward = MISSIONS[m.mission_key]
            result.append({
                "id": m.id,
                "key": m.mission_key,
                "title": title,
                "description": desc,
                "target": m.target_value,
                "current": m.current_value,
                "completed": m.is_completed,
                "reward_claimed": m.reward_claimed,
                "reward": float(m.reward_amount),
            })
    return result


def progress_missions(session: Session, user_id: int, trade_symbol: str, trade_side: str,
                      trade_notional: float, realized_pnl: float, order_type: str):
    """Update mission progress after a trade."""
    today = datetime.utcnow().strftime("%Y-%m-%d")
    missions = session.exec(
        select(UserMission).where(
            UserMission.user_id == user_id,
            UserMission.mission_date == today,
            UserMission.is_completed == False,
        )
    ).all()

    # Today's unique symbols traded (filtered in SQL)
    from datetime import datetime as dt
    today_start = dt.strptime(today, "%Y-%m-%d")
    today_txs = session.exec(
        select(TransactionHistory).where(
            TransactionHistory.user_id == user_id,
            TransactionHistory.timestamp >= today_start,
        )
    ).all()
    today_symbols = set(t.symbol for t in today_txs)

    for m in missions:
        updated = False

        if m.mission_key in ("trade_3", "trade_5"):
            m.current_value += 1
            updated = True

        elif m.mission_key == "profit_trade" and trade_side == "SELL" and realized_pnl > 0:
            m.current_value = 1
            updated = True

        elif m.mission_key == "profit_500" and trade_side == "SELL" and realized_pnl > 0:
            m.current_value += int(realized_pnl)
            updated = True

        elif m.mission_key == "buy_eth" and trade_side == "BUY" and trade_symbol == "ETHUSDT":
            m.current_value = 1
            updated = True

        elif m.mission_key == "buy_bnb" and trade_side == "BUY" and trade_symbol == "BNBUSDT":
            m.current_value = 1
            updated = True

        elif m.mission_key == "limit_order" and order_type in ("LIMIT", "STOP_LOSS_LIMIT", "TAKE_PROFIT_LIMIT"):
            m.current_value = 1
            updated = True

        elif m.mission_key == "sell_profit" and trade_side == "SELL" and realized_pnl > 0:
            m.current_value = 1
            updated = True

        elif m.mission_key == "trade_all":
            today_symbols.add(trade_symbol)
            m.current_value = len(today_symbols)
            updated = True

        elif m.mission_key == "volume_10k":
            m.current_value += int(trade_notional)
            updated = True

        if updated:
            if m.current_value >= m.target_value:
                m.is_completed = True
            session.add(m)

    session.commit()


def claim_mission_reward(session: Session, user_id: int, mission_id: int) -> dict:
    """Claim reward for completed mission."""
    mission = session.exec(
        select(UserMission).where(
            UserMission.id == mission_id,
            UserMission.user_id == user_id,
        )
    ).first()

    if not mission:
        return {"error": "Mission not found"}
    if not mission.is_completed:
        return {"error": "Mission not completed yet"}
    if mission.reward_claimed:
        return {"error": "Reward already claimed"}

    account = session.exec(
        select(TradingAccount).where(TradingAccount.user_id == user_id)
    ).first()
    if not account:
        return {"error": "Account not found"}

    account.balance += mission.reward_amount
    mission.reward_claimed = True
    session.add(mission)
    session.add(account)
    session.commit()

    return {
        "claimed": True,
        "reward": float(mission.reward_amount),
        "new_balance": float(account.balance),
    }
