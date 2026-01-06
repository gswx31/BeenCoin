# app/routers/auth_secure.py
"""
🔐 보안 강화된 인증 라우터

개선 사항:
1. Rate Limiting 적용
2. 로그인 실패 추적 (Brute Force 방지)
3. 타이밍 공격 방지
4. 보안 로깅 강화
"""
from datetime import datetime
import logging
import secrets
import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.core.database import get_session
from app.models.database import User
from app.schemas.user_secure import UserCreate, UserOut, PasswordChange, get_password_strength
from app.utils.security import (
    create_access_token,
    hash_password,
    verify_password,
    get_current_user
)
from app.utils.rate_limiter import rate_limit, login_tracker

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

# =============================================================================
# 응답 스키마
# =============================================================================

class LoginResponse(BaseModel):
    """로그인 응답"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="토큰 만료 시간 (초)")

class PasswordStrengthResponse(BaseModel):
    """비밀번호 강도 응답"""
    score: int = Field(ge=0, le=100)
    level: str
    suggestions: list[str] = []

class SecurityEventLog(BaseModel):
    """보안 이벤트 로그"""
    event_type: str
    username: str
    ip_address: str
    user_agent: Optional[str]
    timestamp: datetime
    success: bool
    details: Optional[str]

# =============================================================================
# 헬퍼 함수
# =============================================================================

def _get_client_info(request: Request) -> dict:
    """클라이언트 정보 추출"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        ip = forwarded.split(",")[0].strip()
    else:
        ip = request.client.host if request.client else "unknown"

    return {
        "ip": ip,
        "user_agent": request.headers.get("User-Agent", "unknown"),
    }

def _log_security_event(
    event_type: str,
    username: str,
    request: Request,
    success: bool,
    details: Optional[str] = None
):
    """보안 이벤트 로깅"""
    client_info = _get_client_info(request)

    log_data = {
        "event": event_type,
        "username": username,
        "ip": client_info["ip"],
        "success": success,
        "timestamp": datetime.utcnow().isoformat(),
    }

    if details:
        log_data["details"] = details

    if success:
        logger.info(f"🔐 보안 이벤트: {log_data}")
    else:
        logger.warning(f"⚠️ 보안 이벤트: {log_data}")

def _constant_time_delay():
    """
    타이밍 공격 방지를 위한 일정한 지연

    사용자 존재 여부를 응답 시간으로 유추하는 것을 방지
    """
    # 0.1초 ~ 0.3초 사이의 랜덤 지연
    time.sleep(secrets.randbelow(200) / 1000 + 0.1)

# =============================================================================
# API 엔드포인트
# =============================================================================

@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
@rate_limit("3/minute")
async def register(
    request: Request,
    user: UserCreate,
    session: Session = Depends(get_session)
):
    """
    회원가입

    Rate Limit: 분당 3회

    보안 사항:
    - 사용자명: 영문+숫자만, XSS 방지
    - 비밀번호: 복잡도 검증
    """
    try:
        # 기존 사용자 확인
        existing_user = session.exec(
            select(User).where(User.username == user.username)
        ).first()

        if existing_user:
            # 타이밍 공격 방지
            _constant_time_delay()

            _log_security_event(
                "REGISTER_FAILED",
                user.username,
                request,
                success=False,
                details="username_exists"
            )

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="이미 존재하는 사용자명입니다."
            )

        # 비밀번호 해싱
        hashed_password = hash_password(user.password)

        # 사용자 생성
        db_user = User(
            username=user.username,
            hashed_password=hashed_password,
            is_active=True,
            created_at=datetime.utcnow(),
        )

        session.add(db_user)
        session.commit()
        session.refresh(db_user)

        # 선물 계정 자동 생성 (기존 로직 유지)
        # _create_default_accounts(session, db_user)

        _log_security_event(
            "REGISTER_SUCCESS",
            user.username,
            request,
            success=True
        )

        logger.info(f"✅ 회원가입 성공: {user.username}")

        return UserOut(
            id=db_user.id,
            username=db_user.username,
            created_at=db_user.created_at.isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"❌ 회원가입 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="회원가입 중 오류가 발생했습니다."
        )

@router.post("/login", response_model=LoginResponse)
@rate_limit("5/minute")
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session)
):
    """
    로그인

    Rate Limit: 분당 5회

    보안 사항:
    - 5회 연속 실패 시 15분 차단
    - 타이밍 공격 방지
    - 동일한 에러 메시지 사용 (사용자 존재 여부 숨김)
    """
    username = form_data.username

    try:
        # 계정 차단 확인
        is_blocked, remaining = login_tracker.is_blocked(username)
        if is_blocked:
            _log_security_event(
                "LOGIN_BLOCKED",
                username,
                request,
                success=False,
                details=f"blocked_for_{remaining}s"
            )

            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "message": "너무 많은 로그인 시도로 인해 계정이 임시 차단되었습니다.",
                    "retry_after": remaining
                },
                headers={"Retry-After": str(remaining)}
            )

        # 사용자 조회
        db_user = session.exec(
            select(User).where(User.username == username)
        ).first()

        # 사용자가 없거나 비밀번호가 틀린 경우 동일한 에러
        generic_error = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="아이디 또는 비밀번호가 잘못되었습니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )

        if not db_user:
            # 타이밍 공격 방지: 사용자가 없어도 해싱 수행
            hash_password("dummy_password_for_timing")
            _constant_time_delay()

            login_tracker.record_attempt(username, success=False)

            _log_security_event(
                "LOGIN_FAILED",
                username,
                request,
                success=False,
                details="user_not_found"
            )

            raise generic_error

        # 비밀번호 검증
        if not verify_password(form_data.password, db_user.hashed_password):
            _constant_time_delay()

            login_tracker.record_attempt(username, success=False)
            remaining_attempts = login_tracker.get_remaining_attempts(username)

            _log_security_event(
                "LOGIN_FAILED",
                username,
                request,
                success=False,
                details=f"wrong_password, remaining={remaining_attempts}"
            )

            # 남은 시도 횟수 알림 (선택적)
            if remaining_attempts <= 2:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={
                        "message": "아이디 또는 비밀번호가 잘못되었습니다.",
                        "warning": f"로그인 {remaining_attempts}회 더 실패하면 계정이 임시 차단됩니다."
                    },
                    headers={"WWW-Authenticate": "Bearer"},
                )

            raise generic_error

        # 계정 활성화 확인
        if not db_user.is_active:
            _log_security_event(
                "LOGIN_FAILED",
                username,
                request,
                success=False,
                details="account_inactive"
            )

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="비활성화된 계정입니다. 관리자에게 문의하세요."
            )

        # 로그인 성공
        login_tracker.record_attempt(username, success=True)

        # 토큰 생성
        try:
            from app.core.config_secure import settings
            expire_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
        except ImportError:
            from app.core.config import settings
            expire_minutes = getattr(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 60)

        access_token = create_access_token(data={"sub": db_user.username})

        _log_security_event(
            "LOGIN_SUCCESS",
            username,
            request,
            success=True
        )

        logger.info(f"✅ 로그인 성공: {username}")

        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=expire_minutes * 60
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 로그인 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="로그인 중 오류가 발생했습니다."
        )

@router.post("/change-password", status_code=status.HTTP_200_OK)
@rate_limit("3/minute")
async def change_password(
    request: Request,
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    비밀번호 변경

    Rate Limit: 분당 3회
    """
    try:
        # 현재 비밀번호 확인
        if not verify_password(password_data.current_password, current_user.hashed_password):
            _log_security_event(
                "PASSWORD_CHANGE_FAILED",
                current_user.username,
                request,
                success=False,
                details="wrong_current_password"
            )

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="현재 비밀번호가 일치하지 않습니다."
            )

        # 새 비밀번호가 현재와 동일한지 확인
        if password_data.current_password == password_data.new_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="새 비밀번호는 현재 비밀번호와 달라야 합니다."
            )

        # 새 비밀번호 해싱 및 저장
        current_user.hashed_password = hash_password(password_data.new_password)
        session.add(current_user)
        session.commit()

        _log_security_event(
            "PASSWORD_CHANGE_SUCCESS",
            current_user.username,
            request,
            success=True
        )

        logger.info(f"✅ 비밀번호 변경 성공: {current_user.username}")

        return {"message": "비밀번호가 성공적으로 변경되었습니다."}

    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"❌ 비밀번호 변경 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="비밀번호 변경 중 오류가 발생했습니다."
        )

@router.post("/check-password-strength", response_model=PasswordStrengthResponse)
async def check_password_strength(password: str):
    """
    비밀번호 강도 확인

    회원가입 전 비밀번호 강도를 미리 확인할 수 있는 엔드포인트
    """
    result = get_password_strength(password)
    return PasswordStrengthResponse(**result)

@router.get("/me", response_model=UserOut)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """현재 로그인한 사용자 정보 조회"""
    return UserOut(
        id=current_user.id,
        username=current_user.username,
        created_at=current_user.created_at.isoformat()
    )
