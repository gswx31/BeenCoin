# app/routers/orders.py
"""
주문 관련 API 라우터 - 수정 버전 (cancel_order 호출 수정)
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session
from typing import List, Optional
from app.schemas.order import OrderCreate, OrderOut
from app.services.order_service import create_order, get_user_orders, cancel_order
from app.core.database import get_session
from app.utils.security import get_current_user
from app.models.database import User
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
    주문 생성 (최근 체결 내역 기반)
    
    ### 체결 방식:
    - **시장가**: 최근 체결 내역에서 가장 유리한 가격부터 체결
    - **지정가**: 체결 가능하면 즉시 체결, 아니면 대기
    
    ### 매수 예시:
    - 최근 체결: 120원, 119원, 121원, 118원...
    - 0.5 BTC 매수 주문
    - → 118원(0.2) + 119원(0.15) + 120원(0.15) = 평균 119원에 체결
    
    ### 매도 예시:
    - 최근 체결: 120원, 121원, 119원, 122원...
    - 0.5 BTC 매도 주문
    - → 122원(0.2) + 121원(0.15) + 120원(0.15) = 평균 121원에 체결
    """
    
    logger.info(
        f"📥 주문 요청: User={current_user.username}, "
        f"Symbol={order.symbol}, Side={order.side}, "
        f"Type={order.order_type}, Qty={order.quantity}"
    )
    
    try:
        # 주문 생성
        created_order = await create_order(session, current_user.id, order)
        
        # OrderOut으로 변환
        return OrderOut(
            id=created_order.id,
            user_id=created_order.user_id,
            symbol=created_order.symbol,
            side=created_order.side.value if hasattr(created_order.side, 'value') else str(created_order.side),
            order_type=created_order.order_type.value if hasattr(created_order.order_type, 'value') else str(created_order.order_type),
            order_status=created_order.order_status.value if hasattr(created_order.order_status, 'value') else str(created_order.order_status),
            quantity=float(created_order.quantity),
            price=float(created_order.price) if created_order.price else None,
            filled_quantity=float(created_order.filled_quantity),
            average_price=float(created_order.average_price) if created_order.average_price else None,
            created_at=created_order.created_at.isoformat(),
            updated_at=created_order.updated_at.isoformat()
        )
    
    except HTTPException as e:
        logger.error(f"❌ 주문 실패 (HTTP {e.status_code}): {e.detail}")
        raise
    
    except Exception as e:
        logger.error(f"❌ 주문 처리 중 예상치 못한 오류: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"주문 처리 중 오류가 발생했습니다: {str(e)}"
        )


@router.get("/", response_model=List[OrderOut])
async def get_orders(
    symbol: Optional[str] = Query(None, description="필터링할 심볼"),
    status: Optional[str] = Query(None, description="필터링할 상태 (PENDING, FILLED, CANCELLED)"),
    limit: int = Query(100, ge=1, le=500, description="최대 조회 개수"),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """사용자 주문 목록 조회"""
    
    logger.info(
        f"📋 주문 목록 조회: User={current_user.username}, "
        f"Symbol={symbol}, Status={status}, Limit={limit}"
    )
    
    try:
        orders = get_user_orders(
            session=session,
            user_id=current_user.id,
            symbol=symbol,
            status=status,
            limit=limit
        )
        
        return [
            OrderOut(
                id=order.id,
                user_id=order.user_id,
                symbol=order.symbol,
                side=order.side.value if hasattr(order.side, 'value') else str(order.side),
                order_type=order.order_type.value if hasattr(order.order_type, 'value') else str(order.order_type),
                order_status=order.order_status.value if hasattr(order.order_status, 'value') else str(order.order_status),
                quantity=float(order.quantity),
                price=float(order.price) if order.price else None,
                filled_quantity=float(order.filled_quantity),
                average_price=float(order.average_price) if order.average_price else None,
                created_at=order.created_at.isoformat(),
                updated_at=order.updated_at.isoformat()
            )
            for order in orders
        ]
    
    except Exception as e:
        logger.error(f"❌ 주문 목록 조회 실패: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="주문 목록 조회 중 오류가 발생했습니다"
        )


@router.get("/{order_id}", response_model=OrderOut)
async def get_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """특정 주문 조회"""
    
    try:
        from app.models.database import Order
        
        order = session.get(Order, order_id)
        
        if not order:
            raise HTTPException(
                status_code=404,
                detail="주문을 찾을 수 없습니다"
            )
        
        if order.user_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="이 주문에 접근할 권한이 없습니다"
            )
        
        return OrderOut(
            id=order.id,
            user_id=order.user_id,
            symbol=order.symbol,
            side=order.side.value if hasattr(order.side, 'value') else str(order.side),
            order_type=order.order_type.value if hasattr(order.order_type, 'value') else str(order.order_type),
            order_status=order.order_status.value if hasattr(order.order_status, 'value') else str(order.order_status),
            quantity=float(order.quantity),
            price=float(order.price) if order.price else None,
            filled_quantity=float(order.filled_quantity),
            average_price=float(order.average_price) if order.average_price else None,
            created_at=order.created_at.isoformat(),
            updated_at=order.updated_at.isoformat()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 주문 조회 실패: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="주문 조회 중 오류가 발생했습니다"
        )


@router.delete("/{order_id}", response_model=OrderOut)
async def cancel_order_endpoint(
    order_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    주문 취소
    
    ### 취소 가능 조건:
    - PENDING 상태인 주문만 취소 가능
    - FILLED, CANCELLED 상태는 취소 불가
    """
    
    logger.info(f"🚫 주문 취소 요청: User={current_user.username}, Order ID={order_id}")
    
    try:
        # ✅ 수정: 인자 순서 변경 (user_id, order_id)
        cancelled_order = cancel_order(session, current_user.id, order_id)
        
        return OrderOut(
            id=cancelled_order.id,
            user_id=cancelled_order.user_id,
            symbol=cancelled_order.symbol,
            side=cancelled_order.side.value if hasattr(cancelled_order.side, 'value') else str(cancelled_order.side),
            order_type=cancelled_order.order_type.value if hasattr(cancelled_order.order_type, 'value') else str(cancelled_order.order_type),
            order_status=cancelled_order.order_status.value if hasattr(cancelled_order.order_status, 'value') else str(cancelled_order.order_status),
            quantity=float(cancelled_order.quantity),
            price=float(cancelled_order.price) if cancelled_order.price else None,
            filled_quantity=float(cancelled_order.filled_quantity),
            average_price=float(cancelled_order.average_price) if cancelled_order.average_price else None,
            created_at=cancelled_order.created_at.isoformat(),
            updated_at=cancelled_order.updated_at.isoformat()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 주문 취소 실패: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="주문 취소 중 오류가 발생했습니다"
        )