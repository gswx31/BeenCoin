"""
시즌 시스템 — 주간 리셋, 명예의 전당 스냅샷.
"""
from datetime import datetime, timedelta
from decimal import Decimal
from sqlmodel import Session, select
from app.models.database import Season, SeasonRanking, User, TradingAccount, Position
from app.services.leaderboard_service import get_leaderboard


def get_or_create_current_season(session: Session) -> Season:
    """현재 활성 시즌 반환, 없으면 새 시즌 생성 (주간)."""
    active = session.exec(
        select(Season).where(Season.is_active == True)
    ).first()
    now = datetime.utcnow()

    if active and active.end_date > now:
        return active

    # 기존 활성 시즌이 끝났으면 비활성화 + 스냅샷
    if active:
        _snapshot_season(session, active)
        active.is_active = False
        session.add(active)

    # 새 시즌 시작 (이번 주 월요일 00:00 ~ 다음 주 월요일 00:00)
    monday = now - timedelta(days=now.weekday())
    monday = monday.replace(hour=0, minute=0, second=0, microsecond=0)
    next_monday = monday + timedelta(days=7)

    new_season = Season(
        name=f"Season {monday.strftime('%Y-W%U')}",
        start_date=monday,
        end_date=next_monday,
        is_active=True,
    )
    session.add(new_season)
    session.commit()
    session.refresh(new_season)
    return new_season


def _snapshot_season(session: Session, season: Season):
    """시즌 종료 시 상위 100명 스냅샷."""
    rankings = get_leaderboard(session, sort_by="return_rate")[:100]
    for r in rankings:
        snapshot = SeasonRanking(
            season_id=season.id,
            user_id=r["user_id"],
            username=r["username"],
            rank=r["rank"],
            return_pct=Decimal(str(r["return_rate"])),
            total_profit=Decimal(str(r["total_profit"])),
            trade_count=r["trade_count"],
        )
        session.add(snapshot)
    session.commit()


def get_current_season_info(session: Session) -> dict:
    season = get_or_create_current_season(session)
    now = datetime.utcnow()
    seconds_remaining = (season.end_date - now).total_seconds()
    return {
        "id": season.id,
        "name": season.name,
        "start_date": str(season.start_date),
        "end_date": str(season.end_date),
        "seconds_remaining": int(seconds_remaining),
    }


def get_hall_of_fame(session: Session, limit: int = 20) -> list:
    """역대 시즌 1위들."""
    seasons = session.exec(
        select(Season).where(Season.is_active == False).order_by(Season.end_date.desc())
    ).all()

    result = []
    for s in seasons[:limit]:
        winner = session.exec(
            select(SeasonRanking)
            .where(SeasonRanking.season_id == s.id, SeasonRanking.rank == 1)
        ).first()
        if winner:
            result.append({
                "season_id": s.id,
                "season_name": s.name,
                "end_date": str(s.end_date),
                "winner": {
                    "username": winner.username,
                    "return_pct": float(winner.return_pct),
                    "total_profit": float(winner.total_profit),
                    "trade_count": winner.trade_count,
                },
            })
    return result


def get_season_rankings(session: Session, season_id: int, limit: int = 50) -> list:
    rankings = session.exec(
        select(SeasonRanking)
        .where(SeasonRanking.season_id == season_id)
        .order_by(SeasonRanking.rank.asc())
    ).all()
    return [
        {
            "rank": r.rank, "username": r.username,
            "return_pct": float(r.return_pct),
            "total_profit": float(r.total_profit),
            "trade_count": r.trade_count,
        }
        for r in rankings[:limit]
    ]
