# app/routers/auth.py
# =============================================================================
# 인증 라우터 - /me 엔드포인트 및 중복검사 추가
# =============================================================================
from datetime import datetime
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select

from app.core.database import get_session
from app.models.database import User
from app.schemas.user import UserCreate, UserOut
from app.utils.security import create_access_token, get_current_user, hash_password, verify_password

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


# =============================================================================
# 회원가입
# =============================================================================
@router.post("/register", response_model=UserOut)
def register(user: UserCreate, session: Session = Depends(get_session)):
    """회원가입"""
    try:
        existing_user = session.exec(select(User).where(User.username == user.username)).first()

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="이미 존재하는 사용자입니다."
            )

        hashed_password = hash_password(user.password)

        db_user = User(
            username=user.username,
            hashed_password=hashed_password,
            is_active=True,
            created_at=datetime.utcnow(),
        )

        session.add(db_user)
        session.commit()
        session.refresh(db_user)

        logger.info(f"✅ 회원가입 성공: {user.username}")

        return UserOut(
            id=db_user.id, 
            username=db_user.username, 
            created_at=str(db_user.created_at)
        )

    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"❌ 회원가입 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="회원가입 중 오류가 발생했습니다.",
        )


# =============================================================================
# ⭐ 아이디 중복 검사 (NEW)
# =============================================================================
@router.get("/check-username/{username}")
def check_username(username: str, session: Session = Depends(get_session)):
    """
    아이디 중복 검사
    
    - 사용 가능하면 {"available": true}
    - 중복이면 {"available": false}
    """
    existing_user = session.exec(
        select(User).where(User.username == username)
    ).first()
    
    return {
        "username": username,
        "available": existing_user is None
    }


# =============================================================================
# 로그인
# =============================================================================
@router.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(), 
    session: Session = Depends(get_session)
):
    """로그인"""
    try:
        db_user = session.exec(
            select(User).where(User.username == form_data.username)
        ).first()

        if not db_user:
            logger.warning(f"❌ 사용자를 찾을 수 없음: {form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="아이디 또는 비밀번호가 잘못되었습니다.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        is_valid = verify_password(form_data.password, db_user.hashed_password)

        if not is_valid:
            logger.warning(f"❌ 비밀번호 불일치: {form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="아이디 또는 비밀번호가 잘못되었습니다.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not db_user.is_active:
            logger.warning(f"❌ 비활성화된 계정: {form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="비활성화된 계정입니다."
            )

        access_token = create_access_token(data={"sub": db_user.username})

        logger.info(f"✅ 로그인 성공: {form_data.username}")

        return {
            "access_token": access_token, 
            "token_type": "bearer",
            "username": db_user.username  # ⭐ 프론트엔드용 추가
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 로그인 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="로그인 중 오류가 발생했습니다.",
        )


# =============================================================================
# ⭐ 현재 사용자 정보 조회 (NEW - 필수!)
# =============================================================================
@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    """
    현재 로그인한 사용자 정보 조회
    
    - 토큰 유효성 검증
    - 새로고침 시 로그인 상태 유지에 사용
    """
    return UserOut(
        id=current_user.id,
        username=current_user.username,
        created_at=str(current_user.created_at)
    )