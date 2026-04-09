from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.schemas.order import OrderCreate, OrderOut
from app.services.order_service import create_order, get_user_orders, cancel_order
from app.core.database import get_session
from fastapi.security import OAuth2PasswordBearer
from typing import List
from app.utils.security import decode_access_token
from app.models.database import User
from app.core.config import settings

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


def _order_to_out(o) -> OrderOut:
    return OrderOut(
        id=o.id, symbol=o.symbol, side=o.side,
        order_type=o.order_type, quantity=o.quantity,
        price=o.price, stop_price=o.stop_price,
        order_status=o.order_status,
        filled_quantity=o.filled_quantity,
        filled_price=o.filled_price,
        commission=o.commission,
        commission_asset=o.commission_asset,
        created_at=str(o.created_at), updated_at=str(o.updated_at),
    )


@router.post("", response_model=OrderOut)
async def place_order(
    order: OrderCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    result = await create_order(session, current_user.id, order)
    return _order_to_out(result)


@router.get("", response_model=List[OrderOut])
def get_orders(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    return [_order_to_out(o) for o in get_user_orders(session, current_user.id)]


@router.delete("/{order_id}", response_model=OrderOut)
def delete_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    return _order_to_out(cancel_order(session, current_user.id, order_id))
