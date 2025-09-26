from fastapi import APIRouter, Depends
from sqlmodel import Session
from app.schemas.order import OrderCreate, OrderOut
from app.services.order_service import create_order, get_user_orders
from app.core.database import get_session
from fastapi.security import OAuth2PasswordBearer
from typing import List
from app.utils.security import decode_access_token
from app.models.database import User
from app.core.config import settings
from fastapi import HTTPException

router = APIRouter(prefix="/orders", tags=["orders"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme), session: Session = Depends(get_session)) -> User:
    payload = decode_access_token(token)
    username: str = payload.get("sub")
    if username is None:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    user = session.exec(select(User).where(User.username == username)).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user

@router.post("/", response_model=OrderOut)
async def place_order(order: OrderCreate, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    return await create_order(session, current_user.id, order)

@router.get("/", response_model=List[OrderOut])
def get_orders(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    orders = get_user_orders(session, current_user.id)
    return [OrderOut(**o.dict(), created_at=str(o.created_at), updated_at=str(o.updated_at)) for o in orders]
