# app/routers/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select
from app.models.database import User, TradingAccount
from app.schemas.user import UserCreate, UserOut
from app.utils.security import get_password_hash, verify_password, create_access_token
from app.core.database import get_session
from app.core.config import settings
from decimal import Decimal
from datetime import datetime

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=UserOut)
def register(user: UserCreate, session: Session = Depends(get_session)):
    """회원가입"""
    try:
        # 1. 중복 사용자 확인
        existing_user = session.exec(
            select(User).where(User.username == user.username)
        ).first()
        
        if existing_user:
            raise HTTPException(
                status_code=400, 
                detail="이미 존재하는 사용자입니다."
            )
        
        # 2. 비밀번호 해싱
        hashed_password = get_password_hash(user.password)
        
        # 3. 사용자 생성
        db_user = User(
            username=user.username, 
            hashed_password=hashed_password,
            created_at=datetime.utcnow()
        )
        session.add(db_user)
        session.commit()
        session.refresh(db_user)
        
        print(f"✅ User created: {db_user.username} (ID: {db_user.id})")
        
        # 4. 거래 계정 생성 (초기 잔액 100만원)
        account = TradingAccount(
            user_id=db_user.id,
            balance=Decimal(str(settings.INITIAL_BALANCE)),
            total_profit=Decimal('0')
        )
        session.add(account)
        session.commit()
        
        print(f"✅ Account created for user {db_user.username}: ${account.balance}")
        
        return UserOut(
            id=db_user.id,
            username=db_user.username,
            created_at=str(db_user.created_at)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Register error: {e}")
        session.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"회원가입 중 오류가 발생했습니다: {str(e)}"
        )

@router.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session)
):
    """
    로그인 (OAuth2 호환)
    - username: 사용자명
    - password: 비밀번호
    - Content-Type: application/x-www-form-urlencoded
    """
    try:
        print(f"🔐 Login attempt: {form_data.username}")
        
        # 1. 사용자 조회
        db_user = session.exec(
            select(User).where(User.username == form_data.username)
        ).first()
        
        if not db_user:
            print(f"❌ User not found: {form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="아이디 또는 비밀번호가 올바르지 않습니다.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # 2. 비밀번호 확인
        if not verify_password(form_data.password, db_user.hashed_password):
            print(f"❌ Invalid password for: {form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="아이디 또는 비밀번호가 올바르지 않습니다.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # 3. 활성화 상태 확인
        if not db_user.is_active:
            print(f"❌ Inactive user: {form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="비활성화된 계정입니다."
            )
        
        # 4. JWT 토큰 생성
        access_token = create_access_token({"sub": db_user.username})
        
        print(f"✅ Login successful: {db_user.username}")
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "username": db_user.username
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Login error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"로그인 중 오류가 발생했습니다: {str(e)}"
        )

@router.get("/me")
def get_current_user_info(
    token: str = Depends(OAuth2PasswordRequestForm),
    session: Session = Depends(get_session)
):
    """현재 로그인한 사용자 정보"""
    # TODO: 토큰 검증 로직 추가
    pass