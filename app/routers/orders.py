from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from app.schemas.order import OrderCreate, OrderOut
from app.services.order_service import create_order
from app.core.database import get_session
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from app.core.config import settings
from app.models.database import User

router = APIRouter(prefix="/orders", tags=["orders"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme), session: Session = Depends(get_session)):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    user = session.exec(select(User).where(User.username == username)).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user

@router.post("/", response_model=OrderOut)
async def place_order(order: OrderCreate, current_user = Depends(get_current_user), session: Session = Depends(get_session)):
    return await create_order(session, current_user.id, order)
