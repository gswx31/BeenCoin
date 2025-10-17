# app/routers/orders.py
from fastapi import APIRouter, Depends, HTTPException, Path
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


@router.post("/", response_model=OrderOut, status_code=201)
async def place_order(
    order: OrderCreate, 
    current_user: User = Depends(get_current_user), 
    session: Session = Depends(get_session)
):
    """
    주문 생성
    
    - **symbol**: 거래 심볼 (BTCUSDT, ETHUSDT 등)
    - **side**: BUY (매수) 또는 SELL (매도)
    - **order_type**: MARKET (시장가) 또는 LIMIT (지정가)
    - **quantity**: 주문 수량
    - **price**: 가격 (지정가 주문 시 필수)
    """
    try:
        created_order = await create_order(session, current_user.id, order)
        
        # Enum을 문자열로 변환
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
            order_status=safe_value(created_order.status),
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
    status: str = None,
    symbol: str = None,
    limit: int = 50,
    current_user: User = Depends(get_current_user), 
    session: Session = Depends(get_session)
):
    """
    주문 내역 조회
    
    - **status**: 주문 상태 필터 (PENDING, FILLED, CANCELLED 등)
    - **symbol**: 특정 코인만 조회
    - **limit**: 조회 개수 (기본 50)
    """
    try:
        orders = get_user_orders(session, current_user.id, limit)
        
        # 필터링
        if status:
            orders = [o for o in orders if str(o.status.value if hasattr(o.status, 'value') else o.status) == status]
        
        if symbol:
            orders = [o for o in orders if o.symbol == symbol]
        
        def safe_value(field):
            if hasattr(field, 'value'):
                return field.value
            return str(field) if field else None
        
        result = []
        for order in orders:
            result.append(OrderOut(
                id=order.id,
                user_id=order.user_id,
                symbol=order.symbol,
                side=safe_value(order.side),
                order_type=safe_value(order.order_type),
                order_status=safe_value(order.status),
                quantity=float(order.quantity),
                price=float(order.price) if order.price else None,
                filled_quantity=float(order.filled_quantity),
                average_price=float(order.average_price) if order.average_price else None,
                created_at=str(order.created_at),
                updated_at=str(order.updated_at)
            ))
        
        return result
        
    except Exception as e:
        logger.error(f"❌ 주문 조회 실패: {e}")
        return []


@router.post("/{order_id}/cancel")
def cancel_order_endpoint(
    order_id: int = Path(..., description="취소할 주문 ID"),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    주문 취소
    
    - **order_id**: 취소할 주문의 ID
    - PENDING 상태의 주문만 취소 가능
    """
    try:
        result = cancel_order(session, current_user.id, order_id)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 주문 취소 실패: {e}")
        raise HTTPException(status_code=500, detail=f"주문 취소 실패: {str(e)}")


@router.get("/{order_id}", response_model=OrderOut)
def get_order_detail(
    order_id: int = Path(..., description="주문 ID"),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """특정 주문 상세 조회"""
    try:
        from app.models.database import Order
        
        order = session.get(Order, order_id)
        
        if not order:
            raise HTTPException(status_code=404, detail="주문을 찾을 수 없습니다")
        
        if order.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="권한이 없습니다")
        
        def safe_value(field):
            if hasattr(field, 'value'):
                return field.value
            return str(field) if field else None
        
        return OrderOut(
            id=order.id,
            user_id=order.user_id,
            symbol=order.symbol,
            side=safe_value(order.side),
            order_type=safe_value(order.order_type),
            order_status=safe_value(order.status),
            quantity=float(order.quantity),
            price=float(order.price) if order.price else None,
            filled_quantity=float(order.filled_quantity),
            average_price=float(order.average_price) if order.average_price else None,
            created_at=str(order.created_at),
            updated_at=str(order.updated_at)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 주문 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="주문 조회 실패")