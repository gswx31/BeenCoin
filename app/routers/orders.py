# app/routers/orders.py
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from app.schemas.order import OrderCreate, OrderOut
from app.services.order_service import create_order, get_user_orders, cancel_order
from app.core.database import get_session
from app.utils.security import get_current_user
from app.models.database import User
from typing import List
import logging

router = APIRouter(prefix="/orders", tags=["orders"])
logger = logging.getLogger(__name__)

@router.post("/", response_model=OrderOut)
async def place_order(
    order: OrderCreate, 
    current_user: User = Depends(get_current_user), 
    session: Session = Depends(get_session)
):
    """주문 생성"""
    try:
        created_order = await create_order(session, current_user.id, order)
        
        return OrderOut(
            id=created_order.id,
            user_id=created_order.user_id,
            symbol=created_order.symbol,
            side=created_order.side.value if hasattr(created_order.side, 'value') else created_order.side,
            order_type=created_order.order_type.value if hasattr(created_order.order_type, 'value') else created_order.order_type,
            status=created_order.status.value if hasattr(created_order.status, 'value') else created_order.status,
            quantity=float(created_order.quantity),
            price=float(created_order.price) if created_order.price else None,
            filled_quantity=float(created_order.filled_quantity),
            average_price=float(created_order.average_price) if created_order.average_price else None,
            created_at=str(created_order.created_at),
            updated_at=str(created_order.updated_at)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 주문 실패: {e}")
        raise HTTPException(status_code=500, detail=f"주문 실패: {str(e)}")


@router.get("/", response_model=List[OrderOut])
def get_orders(
    current_user: User = Depends(get_current_user), 
    session: Session = Depends(get_session)
):
    """주문 내역 조회"""
    try:
        orders = get_user_orders(session, current_user.id)
        
        return [
            OrderOut(
                id=o.id,
                user_id=o.user_id,
                symbol=o.symbol,
                side=o.side.value if hasattr(o.side, 'value') else o.side,
                order_type=o.order_type.value if hasattr(o.order_type, 'value') else o.order_type,
                status=o.status.value if hasattr(o.status, 'value') else o.status,
                quantity=float(o.quantity),
                price=float(o.price) if o.price else None,
                filled_quantity=float(o.filled_quantity),
                average_price=float(o.average_price) if o.average_price else None,
                created_at=str(o.created_at),
                updated_at=str(o.updated_at)
            )
            for o in orders
        ]
    except Exception as e:
        logger.error(f"❌ 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"조회 실패: {str(e)}")


@router.delete("/{order_id}")
def cancel_order_endpoint(
    order_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """주문 취소"""
    return cancel_order(session, current_user.id, order_id)