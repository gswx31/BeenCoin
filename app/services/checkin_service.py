"""
출석 체크 + 연속 보상 + 럭키박스.
"""
import random
from decimal import Decimal
from datetime import datetime, timedelta
from sqlmodel import Session, select
from app.models.database import DailyCheckIn, TradingAccount, User
from fastapi import HTTPException

# 연속 출석 보상 (1~6일은 고정, 7일은 럭키박스)
CHECKIN_REWARDS = {
    1: 100,
    2: 200,
    3: 500,
    4: 1000,
    5: 2000,
    6: 5000,
    7: "lucky_box",  # 7일차는 럭키박스 (랜덤)
}

# 럭키박스 결과 (확률 가중치)
LUCKY_BOX_PRIZES = [
    (10000, 50),   # 1만 (50%)
    (30000, 25),   # 3만 (25%)
    (100000, 15),  # 10만 (15%)
    (500000, 8),   # 50만 (8%)
    (1000000, 2),  # 100만 (2%) — 잭팟
]


def _draw_lucky_box() -> int:
    total = sum(w for _, w in LUCKY_BOX_PRIZES)
    pick = random.uniform(0, total)
    acc = 0
    for prize, weight in LUCKY_BOX_PRIZES:
        acc += weight
        if pick <= acc:
            return prize
    return LUCKY_BOX_PRIZES[0][0]


def get_checkin_status(session: Session, user_id: int) -> dict:
    """오늘 출석 가능 여부 + 연속일 + 다음 보상."""
    user = session.exec(select(User).where(User.id == user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    today = datetime.utcnow().strftime("%Y-%m-%d")
    yesterday = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
    already = user.last_checkin_date == today

    # 어제 안 했으면 streak 리셋 표시
    streak = user.checkin_streak
    if user.last_checkin_date and user.last_checkin_date != today and user.last_checkin_date != yesterday:
        streak = 0

    next_day = ((streak if already else streak) + (0 if already else 1))
    cycle_day = ((next_day - 1) % 7) + 1
    next_reward = CHECKIN_REWARDS.get(cycle_day, 100)

    return {
        "already_checked_in": already,
        "current_streak": streak,
        "next_reward_day": cycle_day,
        "next_reward": next_reward,
        "rewards_schedule": CHECKIN_REWARDS,
    }


def do_checkin(session: Session, user_id: int) -> dict:
    """출석 처리 + 보상 지급."""
    user = session.exec(select(User).where(User.id == user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    today = datetime.utcnow().strftime("%Y-%m-%d")
    yesterday = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")

    if user.last_checkin_date == today:
        raise HTTPException(status_code=400, detail="이미 오늘 출석 체크하셨어요")

    # streak 갱신
    if user.last_checkin_date == yesterday:
        user.checkin_streak += 1
    else:
        user.checkin_streak = 1
    user.last_checkin_date = today

    # 7일 주기 보상
    cycle_day = ((user.checkin_streak - 1) % 7) + 1
    reward_def = CHECKIN_REWARDS.get(cycle_day, 100)

    is_lucky = False
    if reward_def == "lucky_box":
        reward_amount = _draw_lucky_box()
        is_lucky = True
    else:
        reward_amount = reward_def

    # 잔고에 추가
    account = session.exec(
        select(TradingAccount).where(TradingAccount.user_id == user_id)
    ).first()
    if account:
        account.balance += Decimal(str(reward_amount))
        session.add(account)

    # 기록
    checkin = DailyCheckIn(
        user_id=user_id, checkin_date=today,
        streak_day=user.checkin_streak,
        reward_amount=Decimal(str(reward_amount)),
    )
    session.add(checkin)
    session.add(user)
    session.commit()

    return {
        "success": True,
        "streak": user.checkin_streak,
        "cycle_day": cycle_day,
        "reward": reward_amount,
        "is_lucky_box": is_lucky,
        "new_balance": float(account.balance) if account else 0,
    }
