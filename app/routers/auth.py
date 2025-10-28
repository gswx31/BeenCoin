# app/routers/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select
from app.models.database import User, TradingAccount
from app.schemas.user import UserCreate, UserOut
from app.utils.security import hash_password, verify_password, create_access_token, get_current_user
from app.core.database import get_session
from app.core.config import settings
from decimal import Decimal
from datetime import datetime

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=UserOut)
def register(user: UserCreate, session: Session = Depends(get_session)):
    """회원가입"""
    try:
        existing_user = session.exec(
            select(User).where(User.username == user.username)
        ).first()
        
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
            created_at=datetime.utcnow()
        )
        
        session.add(db_user)
        session.commit()
        session.refresh(db_user)
        
        account = TradingAccount(
            user_id=db_user.id,
            balance=Decimal(str(settings.INITIAL_BALANCE)),
            total_profit=Decimal('0'),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        session.add(account)
        session.commit()
        
        return UserOut(
            id=db_user.id,
            username=db_user.username,
            created_at=str(db_user.created_at)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="회원가입 중 오류가 발생했습니다."
        )


@router.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session)
):
    """로그인"""
    db_user = session.exec(
        select(User).where(User.username == form_data.username)
    ).first()
    
    if not db_user or not verify_password(form_data.password, db_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="아이디 또는 비밀번호가 잘못되었습니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not db_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="비활성화된 계정입니다."
        )
    
    access_token = create_access_token(data={"sub": db_user.username})
    return {"access_token": access_token, "token_type": "bearer"}