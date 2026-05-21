"""
파산 신청 시스템 — 자산이 거의 0이 됐을 때 재시작 기회.
"""
from decimal import Decimal
from datetime import datetime, timedelta
from sqlmodel import Session, select
from fastapi import HTTPException
from app.models.database import User, TradingAccount, Position, FuturesPosition
from app.core.config import settings

BANKRUPTCY_THRESHOLD = Decimal('10000')  # 총자산 1만 달러 미만일 때 가능
COOLDOWN_DAYS = 7


def get_bankruptcy_status(session: Session, user_id: int) -> dict:
    """파산 가능 여부."""
    user = session.exec(select(User).where(User.id == user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없어요")

    account = session.exec(
        select(TradingAccount).where(TradingAccount.user_id == user_id)
    ).first()
    if not account:
        raise HTTPException(status_code=404, detail="계좌를 찾을 수 없어요")

    # 현물 포지션 가치
    spot_value = sum(
        float(p.current_value) for p in session.exec(
            select(Position).where(Position.account_id == account.id)
        ).all()
    )
    # 선물 증거금
    futures_margin = sum(
        float(p.margin) for p in session.exec(
            select(FuturesPosition).where(
                FuturesPosition.user_id == user_id,
                FuturesPosition.is_open == True,
            )
        ).all()
    )

    total_assets = float(account.balance) + spot_value + futures_margin
    eligible_by_balance = total_assets < float(BANKRUPTCY_THRESHOLD)

    # 쿨다운 체크
    cooldown_remaining = 0
    if user.last_bankruptcy_date:
        try:
            last = datetime.fromisoformat(user.last_bankruptcy_date)
            elapsed = (datetime.utcnow() - last).days
            if elapsed < COOLDOWN_DAYS:
                cooldown_remaining = COOLDOWN_DAYS - elapsed
        except Exception:
            pass

    return {
        "total_assets": round(total_assets, 2),
        "threshold": float(BANKRUPTCY_THRESHOLD),
        "eligible_by_balance": eligible_by_balance,
        "cooldown_remaining_days": cooldown_remaining,
        "can_apply": eligible_by_balance and cooldown_remaining == 0,
        "bankruptcy_count": user.bankruptcy_count,
        "last_bankruptcy_date": user.last_bankruptcy_date,
    }


def apply_bankruptcy(session: Session, user_id: int) -> dict:
    """파산 신청 처리 — 잔고 리셋, 포지션 청산."""
    status = get_bankruptcy_status(session, user_id)
    if not status["can_apply"]:
        if status["cooldown_remaining_days"] > 0:
            raise HTTPException(
                status_code=400,
                detail=f"파산 신청은 {COOLDOWN_DAYS}일에 1번만 가능해요. {status['cooldown_remaining_days']}일 남았어요"
            )
        if not status["eligible_by_balance"]:
            raise HTTPException(
                status_code=400,
                detail=f"총 자산이 ${BANKRUPTCY_THRESHOLD:,.0f} 미만이어야 신청 가능해요 (현재 ${status['total_assets']:,.2f})"
            )

    user = session.exec(select(User).where(User.id == user_id)).first()
    account = session.exec(
        select(TradingAccount).where(TradingAccount.user_id == user_id)
    ).first()

    # 모든 현물 포지션 청산
    spot_positions = session.exec(
        select(Position).where(Position.account_id == account.id)
    ).all()
    for p in spot_positions:
        session.delete(p)

    # 모든 선물 포지션 강제 종료
    futures = session.exec(
        select(FuturesPosition).where(
            FuturesPosition.user_id == user_id,
            FuturesPosition.is_open == True,
        )
    ).all()
    for f in futures:
        f.is_open = False
        f.closed_at = datetime.utcnow()
        f.is_liquidated = True
        f.realized_pnl = -f.margin
        session.add(f)

    # 잔고 리셋 ($1M), 통계는 유지
    account.balance = Decimal(str(settings.INITIAL_BALANCE))
    user.bankruptcy_count += 1
    user.last_bankruptcy_date = datetime.utcnow().isoformat()
    session.add(account)
    session.add(user)
    session.commit()

    # 피드
    try:
        from app.services.feed_service import add_activity
        msg = f"🆘 {user.username}님이 다시 시작했어요 (파산 {user.bankruptcy_count}회)"
        add_activity(session, user_id, "BANKRUPTCY", msg)
    except Exception:
        pass

    return {
        "success": True,
        "new_balance": float(account.balance),
        "bankruptcy_count": user.bankruptcy_count,
    }
