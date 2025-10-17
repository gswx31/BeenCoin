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
        
        # ✅ Enum을 문자열로 변환
        def safe_value(field):
            if hasattr(field, 'value'):
                return field.value
            return str(field) if field else None
        
        return OrderOut(
            id=created_order.id,
            user_id=created_order.user_id,
            symbol=created_order.symbol,
            side=safe_value(created_order.side),
            order_type=safe_value(created_order.order_type),
            order_status=safe_value(created_order.status),  # ✅ status -> order_status
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
        
        def safe_value(field):
            if hasattr(field, 'value'):
                return field.value
            return str(field) if field else None
        
        return [
            OrderOut(
                id=order.id,
                user_id=order.user_id,
                symbol=order.symbol,
                side=safe_value(order.side),
                order_type=safe_value(order.order_type),
                order_status=safe_value(order.status),  # ✅ status -> order_status
                quantity=float(order.quantity),
                price=float(order.price) if order.price else None,
                filled_quantity=float(order.filled_quantity),
                average_price=float(order.average_price) if order.average_price else None,
                created_at=str(order.created_at),
                updated_at=str(order.updated_at)
            )
            for order in orders
        ]
    except Exception as e:
        logger.error(f"❌ 주문 내역 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"주문 내역 조회 실패: {str(e)}")


@router.delete("/{order_id}")
def cancel_order_endpoint(
    order_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """주문 취소"""
    return cancel_order(session, current_user.id, order_id)