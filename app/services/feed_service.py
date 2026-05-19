"""
실시간 활동 피드.
"""
import json
from decimal import Decimal
from sqlmodel import Session, select
from app.models.database import ActivityFeed, User


def add_activity(session: Session, user_id: int, activity_type: str, message: str,
                 symbol: str = None, metadata: dict = None):
    """활동 추가."""
    user = session.exec(select(User).where(User.id == user_id)).first()
    if not user:
        return
    activity = ActivityFeed(
        user_id=user_id,
        username=user.username,
        activity_type=activity_type,
        symbol=symbol,
        message=message,
        metadata_json=json.dumps(metadata or {}, ensure_ascii=False, default=str),
    )
    session.add(activity)
    session.commit()


def get_feed(session: Session, limit: int = 50) -> list:
    """최근 활동 피드 (전체 유저)."""
    activities = session.exec(
        select(ActivityFeed).order_by(ActivityFeed.created_at.desc())
    ).all()[:limit]
    return [
        {
            "id": a.id, "username": a.username,
            "activity_type": a.activity_type,
            "symbol": a.symbol, "message": a.message,
            "metadata": json.loads(a.metadata_json or "{}"),
            "created_at": str(a.created_at),
        }
        for a in activities
    ]


def emit_trade(session: Session, user_id: int, symbol: str, side: str, qty: Decimal, price: Decimal, notional: float):
    """매매 시 호출 — 중요한 매매만 피드에 등록."""
    if notional < 1000:  # 너무 작은 거래는 무시
        return
    side_kr = "매수" if side == "BUY" else "매도"
    coin = symbol.replace("USDT", "")

    if notional >= 100000:
        emoji = "🐋"
        activity_type = "BIG_WIN"
    elif notional >= 10000:
        emoji = "💸"
        activity_type = "TRADE"
    else:
        emoji = "📊"
        activity_type = "TRADE"

    msg = f"{emoji} {coin} {qty:.4f}개 {side_kr} (${notional:,.0f})"
    add_activity(session, user_id, activity_type, msg, symbol, {
        "side": side, "qty": str(qty), "price": str(price), "notional": notional,
    })


def emit_achievement(session: Session, user_id: int, achievement_title: str, rarity: str):
    """업적 달성 시."""
    emoji_map = {"common": "🏆", "uncommon": "✨", "rare": "💎", "epic": "👑", "legendary": "⭐"}
    emoji = emoji_map.get(rarity, "🏆")
    msg = f"{emoji} 업적 달성: {achievement_title}"
    add_activity(session, user_id, "ACHIEVEMENT", msg, metadata={"rarity": rarity})


def emit_tier_up(session: Session, user_id: int, new_tier_label: str, emoji: str):
    msg = f"{emoji} {new_tier_label} 티어 승급!"
    add_activity(session, user_id, "TIER_UP", msg, metadata={"tier": new_tier_label})
