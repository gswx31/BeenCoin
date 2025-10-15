from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select
from app.models.database import User, SpotAccount, FuturesAccount
from app.schemas.user import UserCreate, UserOut
from app.utils.security import hash_password, verify_password, create_access_token, get_current_user  # 수정: verify_password, create_access_token, get_current_user 추가
from app.core.database import get_session
from app.core.config import settings
from decimal import Decimal
from datetime import datetime

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=UserOut)
def register(user: UserCreate, session: Session = Depends(get_session)):
    """회원가입 - 현물/선물 계정 동시 생성"""
    try:
        # 중복 확인
        existing_user = session.exec(select(User).where(User.username == user.username)).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="이미 존재하는 사용자입니다.")
        
        # 비밀번호 해싱
        hashed_password = hash_password(user.password)
        
        # 사용자 생성
        db_user = User(username=user.username, hashed_password=hashed_password, created_at=datetime.utcnow())
        session.add(db_user)
        session.commit()
        session.refresh(db_user)
        
        print(f"User created: {db_user.username} (ID: {db_user.id})")
        
        # 현물 계정 생성
        spot_account = SpotAccount(
            user_id=db_user.id,
            usdt_balance=Decimal(str(settings.INITIAL_BALANCE or "1000000.00")),  # settings에 없으면 기본값
            total_profit=Decimal('0')
        )
        session.add(spot_account)
        
        # 선물 계정 생성
        futures_account = FuturesAccount(
            user_id=db_user.id,
            usdt_balance=Decimal(str(settings.INITIAL_BALANCE or "1000000.00")),
            available_balance=Decimal(str(settings.INITIAL_BALANCE or "1000000.00")),
            total_realized_pnl=Decimal('0'),
            total_unrealized_pnl=Decimal('0'),
            total_margin=Decimal('0')
        )
        session.add(futures_account)
        session.commit()
        
        print(f"Spot & Futures accounts created for {db_user.username}")
        
        return UserOut(id=db_user.id, username=db_user.username, created_at=str(db_user.created_at))
    
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"회원가입 오류: {str(e)}")

@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_session)):
    """
    로그인 - OAuth2 form-data (username, password)
    응답: access_token (Bearer Token)
    """
    try:
        db_user = session.exec(select(User).where(User.username == form_data.username)).first()
        if not db_user or not verify_password(form_data.password, db_user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="아이디 또는 비밀번호가 올바르지 않습니다.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not db_user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="비활성화된 계정입니다.")
        
        # JWT 생성 (sub: username)
        access_token = create_access_token(data={"sub": db_user.username})
        
        print(f"Login successful: {db_user.username}")
        return {"access_token": access_token, "token_type": "bearer", "username": db_user.username}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"로그인 오류: {str(e)}")

@router.get("/me", response_model=UserOut)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """현재 사용자 정보 (Bearer Token 필요)"""
    return UserOut(
        id=current_user.id,
        username=current_user.username,
        created_at=str(current_user.created_at)
    )