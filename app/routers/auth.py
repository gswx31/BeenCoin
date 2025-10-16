# app/routers/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select
from app.models.database import User, SpotAccount, FuturesAccount
from app.schemas.user import UserCreate, UserOut
from app.utils.security import hash_password, verify_password, create_access_token, get_current_user
from app.core.database import get_session
from app.core.config import settings
from decimal import Decimal
from datetime import datetime

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=UserOut)
def register(user: UserCreate, session: Session = Depends(get_session)):
    """
    회원가입 - 현물/선물 계정 동시 생성
    
    요청:
        {
            "username": "testuser",
            "password": "password123"
        }
    
    응답:
        {
            "id": 1,
            "username": "testuser",
            "created_at": "2025-01-01T00:00:00"
        }
    """
    try:
        # 중복 확인
        existing_user = session.exec(
            select(User).where(User.username == user.username)
        ).first()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="이미 존재하는 사용자입니다."
            )
        
        # 사용자 생성
        hashed_password = hash_password(user.password)
        db_user = User(
            username=user.username,
            hashed_password=hashed_password,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        session.add(db_user)
        session.commit()
        session.refresh(db_user)
        
        # 현물 계정 생성
        spot_account = SpotAccount(
            user_id=db_user.id,
            usdt_balance=Decimal(str(settings.INITIAL_BALANCE)),
            total_profit=Decimal('0')
        )
        session.add(spot_account)
        
        # 선물 계정 생성
        futures_account = FuturesAccount(
            user_id=db_user.id,
            usdt_balance=Decimal(str(settings.INITIAL_BALANCE)),
            total_realized_pnl=Decimal('0'),
            total_unrealized_pnl=Decimal('0'),
            total_margin=Decimal('0'),
            available_balance=Decimal(str(settings.INITIAL_BALANCE))
        )
        session.add(futures_account)
        
        session.commit()
        
        print(f"✅ User created: {db_user.username} (ID: {db_user.id})")
        print(f"   Spot balance: ${spot_account.usdt_balance}")
        print(f"   Futures balance: ${futures_account.usdt_balance}")
        
        return UserOut(
            id=db_user.id,
            username=db_user.username,
            created_at=str(db_user.created_at)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        print(f"❌ Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="회원가입 중 오류가 발생했습니다."
        )


@router.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session)
):
    """
    로그인
    
    Form Data:
        username: 사용자명
        password: 비밀번호
    
    응답:
        {
            "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
            "token_type": "bearer"
        }
    """
    # 사용자 조회
    db_user = session.exec(
        select(User).where(User.username == form_data.username)
    ).first()
    
    # 사용자 없음 또는 비밀번호 불일치
    if not db_user or not verify_password(form_data.password, db_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="아이디 또는 비밀번호가 잘못되었습니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 비활성화된 계정
    if not db_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="비활성화된 계정입니다."
        )
    
    # 액세스 토큰 생성
    access_token = create_access_token(data={"sub": db_user.username})
    
    print(f"✅ Login successful: {db_user.username}")
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@router.get("/me", response_model=UserOut)
def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    현재 로그인한 사용자 정보 조회
    
    헤더:
        Authorization: Bearer <access_token>
    
    응답:
        {
            "id": 1,
            "username": "testuser",
            "created_at": "2025-01-01T00:00:00"
        }
    """
    return UserOut(
        id=current_user.id,
        username=current_user.username,
        created_at=str(current_user.created_at)
    )