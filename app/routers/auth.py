from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from app.models.database import User, TradingAccount
from app.schemas.user import UserCreate, UserLogin, UserOut
from app.utils.security import get_password_hash, verify_password, create_access_token
from app.core.database import get_session

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=UserOut)
def register(user: UserCreate, session: Session = Depends(get_session)):
    existing_user = session.exec(select(User).where(User.username == user.username)).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    hashed_password = get_password_hash(user.password)
    db_user = User(username=user.username, hashed_password=hashed_password)
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    account = TradingAccount(user_id=db_user.id)
    session.add(account)
    session.commit()
    return db_user

@router.post("/login")
def login(user: UserLogin, session: Session = Depends(get_session)):
    db_user = session.exec(select(User).where(User.username == user.username)).first()
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    access_token = create_access_token({"sub": db_user.username})
    return {"access_token": access_token, "token_type": "bearer"}
