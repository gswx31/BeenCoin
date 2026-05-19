"""
친구 추천 코드 시스템.
- 신규 가입 시 자동으로 8자리 코드 생성
- 추천 코드 입력 시 양쪽에 보너스 (신규 5만, 추천인 1만)
"""
import string
import secrets
from decimal import Decimal
from sqlmodel import Session, select
from app.models.database import User, TradingAccount
from fastapi import HTTPException

REFERRAL_NEW_USER_BONUS = Decimal("50000")  # 신규 가입자
REFERRAL_REFERRER_BONUS = Decimal("10000")  # 추천한 사람


def generate_referral_code(session: Session) -> str:
    """충돌 방지 코드 생성."""
    alphabet = string.ascii_uppercase + string.digits
    for _ in range(20):
        code = ''.join(secrets.choice(alphabet) for _ in range(8))
        existing = session.exec(select(User).where(User.referral_code == code)).first()
        if not existing:
            return code
    raise RuntimeError("Failed to generate unique referral code")


def assign_referral_code_if_missing(session: Session, user: User):
    if not user.referral_code:
        user.referral_code = generate_referral_code(session)
        session.add(user)
        session.commit()


def apply_referral(session: Session, new_user_id: int, code: str) -> dict:
    """신규 가입자가 추천 코드 사용."""
    code = code.strip().upper()
    new_user = session.exec(select(User).where(User.id == new_user_id)).first()
    if not new_user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없어요")
    if new_user.referred_by_user_id:
        raise HTTPException(status_code=400, detail="이미 추천 코드를 사용하셨어요")

    referrer = session.exec(select(User).where(User.referral_code == code)).first()
    if not referrer:
        raise HTTPException(status_code=404, detail="존재하지 않는 추천 코드예요")
    if referrer.id == new_user_id:
        raise HTTPException(status_code=400, detail="자신의 코드는 사용할 수 없어요")

    # 양쪽 계좌 보너스
    new_account = session.exec(select(TradingAccount).where(TradingAccount.user_id == new_user_id)).first()
    referrer_account = session.exec(select(TradingAccount).where(TradingAccount.user_id == referrer.id)).first()

    if new_account:
        new_account.balance += REFERRAL_NEW_USER_BONUS
        session.add(new_account)
    if referrer_account:
        referrer_account.balance += REFERRAL_REFERRER_BONUS
        session.add(referrer_account)

    new_user.referred_by_user_id = referrer.id
    referrer.referral_count += 1
    session.add(new_user)
    session.add(referrer)
    session.commit()

    return {
        "success": True,
        "new_user_bonus": float(REFERRAL_NEW_USER_BONUS),
        "referrer_username": referrer.username,
    }


def get_referral_info(session: Session, user_id: int) -> dict:
    user = session.exec(select(User).where(User.id == user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없어요")
    assign_referral_code_if_missing(session, user)

    referred_by_username = None
    if user.referred_by_user_id:
        ref = session.exec(select(User).where(User.id == user.referred_by_user_id)).first()
        if ref:
            referred_by_username = ref.username

    return {
        "referral_code": user.referral_code,
        "referred_by": referred_by_username,
        "referral_count": user.referral_count,
        "earned_bonus": float(Decimal(str(user.referral_count)) * REFERRAL_REFERRER_BONUS),
        "new_user_bonus": float(REFERRAL_NEW_USER_BONUS),
        "referrer_bonus": float(REFERRAL_REFERRER_BONUS),
    }
