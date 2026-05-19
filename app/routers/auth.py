from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel
from sqlmodel import Session, select
from app.models.database import User, TradingAccount, RefreshToken
from app.schemas.user import UserCreate, UserLogin, UserOut
from app.utils.security import (
    get_password_hash, verify_password, create_access_token,
    generate_refresh_token, hash_refresh_token,
)
from app.core.database import get_session
from app.core.config import settings
from app.core.rate_limit import limiter
from datetime import datetime, timedelta
from decimal import Decimal

router = APIRouter(prefix="/auth", tags=["auth"])


class RefreshRequest(BaseModel):
    refresh_token: str


def _issue_tokens(session: Session, user: User) -> dict:
    """Access + Refresh 토큰 발급 후 DB에 hash 저장."""
    access = create_access_token({"sub": user.username})
    raw_refresh, hashed = generate_refresh_token()
    rt = RefreshToken(
        user_id=user.id,
        token_hash=hashed,
        expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    session.add(rt)
    session.commit()
    return {
        "access_token": access,
        "refresh_token": raw_refresh,
        "token_type": "bearer",
    }


@router.post("/register", response_model=UserOut)
@limiter.limit("5/minute")
def register(request: Request, user: UserCreate, session: Session = Depends(get_session)):
    existing = session.exec(select(User).where(User.username == user.username)).first()
    if existing:
        raise HTTPException(status_code=400, detail="이미 사용 중인 아이디예요")
    db_user = User(username=user.username, hashed_password=get_password_hash(user.password))
    session.add(db_user)
    session.commit()
    session.refresh(db_user)

    if not session.exec(select(TradingAccount).where(TradingAccount.user_id == db_user.id)).first():
        session.add(TradingAccount(user_id=db_user.id, balance=Decimal(str(settings.INITIAL_BALANCE))))
        session.commit()

    # 추천 코드 자동 발급
    from app.services.referral_service import assign_referral_code_if_missing
    assign_referral_code_if_missing(session, db_user)

    # 회원가입 시 추천 코드 사용 (선택)
    if getattr(user, 'referral_code', None):
        try:
            from app.services.referral_service import apply_referral
            apply_referral(session, db_user.id, user.referral_code)
        except Exception:
            pass  # 잘못된 코드는 무시 (가입 자체는 성공)

    return UserOut(id=db_user.id, username=db_user.username, created_at=str(db_user.created_at))


@router.post("/login")
@limiter.limit("10/minute")
def login(request: Request, user: UserLogin, session: Session = Depends(get_session)):
    db_user = session.exec(select(User).where(User.username == user.username)).first()
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 틀렸어요")
    if not db_user.is_active:
        raise HTTPException(status_code=403, detail="비활성화된 계정이에요")
    return _issue_tokens(session, db_user)


@router.post("/refresh")
@limiter.limit("30/minute")
def refresh(request: Request, body: RefreshRequest, session: Session = Depends(get_session)):
    """
    Refresh Token Rotation:
    - 기존 토큰을 무효화하고 새 access+refresh 발급
    - 이미 무효화된 토큰 재사용 시 → 해당 유저의 모든 토큰 강제 무효화 (탈취 의심)
    """
    hashed = hash_refresh_token(body.refresh_token)
    rt = session.exec(select(RefreshToken).where(RefreshToken.token_hash == hashed)).first()

    if not rt:
        raise HTTPException(status_code=401, detail="세션이 만료됐어요. 다시 로그인해주세요")

    if rt.revoked:
        # 재사용 감지! 해당 유저의 모든 refresh token 무효화
        all_tokens = session.exec(
            select(RefreshToken).where(RefreshToken.user_id == rt.user_id, RefreshToken.revoked == False)
        ).all()
        for t in all_tokens:
            t.revoked = True
            session.add(t)
        session.commit()
        raise HTTPException(status_code=401, detail="보안 문제로 모든 세션이 종료됐어요. 다시 로그인해주세요")

    if rt.expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="세션이 만료됐어요. 다시 로그인해주세요")

    user = session.exec(select(User).where(User.id == rt.user_id)).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="비활성화된 계정이에요")

    # Rotate: 기존 토큰 폐기 + 새 토큰 발급
    rt.revoked = True
    session.add(rt)
    tokens = _issue_tokens(session, user)

    # 새 토큰 ID를 rotated_to에 기록
    new_rt = session.exec(
        select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(tokens["refresh_token"]))
    ).first()
    if new_rt:
        rt.rotated_to = new_rt.id
        session.add(rt)
        session.commit()

    return tokens


@router.post("/logout")
def logout(body: RefreshRequest, session: Session = Depends(get_session)):
    hashed = hash_refresh_token(body.refresh_token)
    rt = session.exec(select(RefreshToken).where(RefreshToken.token_hash == hashed)).first()
    if rt:
        rt.revoked = True
        session.add(rt)
        session.commit()
    return {"detail": "Logged out"}
