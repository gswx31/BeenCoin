# app/routers/auth.py
from datetime import datetime
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select

from app.core.database import get_session
from app.models.database import User
from app.schemas.user import UserCreate, UserOut
from app.utils.security import create_access_token, hash_password, verify_password

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut)
def register(user: UserCreate, session: Session = Depends(get_session)):
    """회원가입"""
    try:
        existing_user = session.exec(select(User).where(User.username == user.username)).first()

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="이미 존재하는 사용자입니다."
            )

        # ⭐ hash_password 사용 (get_password_hash도 동일하게 동작)
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

        # TradingAccount 생성은 User 모델에서 자동으로 처리됨
        # 하지만 명시적으로 추가할 수도 있음

        logger.info(f"✅ 회원가입 성공: {user.username}")

        return UserOut(id=db_user.id, username=db_user.username, created_at=str(db_user.created_at))

    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"❌ 회원가입 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="회원가입 중 오류가 발생했습니다.",
        )


@router.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_session)
):
    """로그인"""
    try:
        # 사용자 조회
        db_user = session.exec(select(User).where(User.username == form_data.username)).first()

        if not db_user:
            logger.warning(f"❌ 사용자를 찾을 수 없음: {form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="아이디 또는 비밀번호가 잘못되었습니다.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # ⭐ 비밀번호 검증
        is_valid = verify_password(form_data.password, db_user.hashed_password)

        if not is_valid:
            logger.warning(f"❌ 비밀번호 불일치: {form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="아이디 또는 비밀번호가 잘못되었습니다.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 활성화 상태 확인
        if not db_user.is_active:
            logger.warning(f"❌ 비활성화된 계정: {form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="비활성화된 계정입니다."
            )

        # JWT 토큰 생성
        access_token = create_access_token(data={"sub": db_user.username})

        logger.info(f"✅ 로그인 성공: {form_data.username}")

        return {"access_token": access_token, "token_type": "bearer"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 로그인 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="로그인 중 오류가 발생했습니다.",
        )
