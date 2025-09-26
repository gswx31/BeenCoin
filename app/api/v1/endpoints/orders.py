from fastapi import APIRouter, Depends
from sqlmodel import Session
from app.schemas.order import OrderCreate, OrderOut
from app.services.order_service import create_order, get_user_orders
from app.core.database import get_session
from app.routers.orders import get_current_user
from typing import List

router = APIRouter(prefix="/orders", tags=["orders"])

@router.post("/", response_model=OrderOut)
async def place_order(order: OrderCreate, current_user = Depends(get_current_user), session: Session = Depends(get_session)):
    return await create_order(session, current_user.id, order)

@router.get("/", response_model=List[OrderOut])
def get_orders(current_user = Depends(get_current_user), session: Session = Depends(get_session)):
    orders = get_user_orders(session, current_user.id)
    return [OrderOut(**o.dict(), created_at=str(o.created_at), updated_at=str(o.updated_at)) for o in orders]
