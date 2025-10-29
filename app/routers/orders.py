# app/routers/orders.py
"""
주문 관련 API 라우터 - 수정 버전
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
    주문 생성
    
    ### 요청 파라미터:
    - **symbol**: 거래 심볼 (예: BTCUSDT, ETHUSDT)
    - **side**: 주문 방향 (BUY, SELL)
    - **order_type**: 주문 타입 (MARKET, LIMIT)
    - **quantity**: 주문 수량
    - **price**: 가격 (지정가 주문 시 필수)
    
    ### 응답:
    - 생성된 주문 정보
    - 시장가 주문은 즉시 FILLED 상태
    - 지정가 주문은 PENDING 상태로 생성
    
    ### 에러:
    - 400: 잘못된 입력, 잔액/수량 부족
    - 503: 시장가격 조회 실패
    """
    
    logger.info(
        f"📥 주문 요청: User={current_user.username}, "
        f"Symbol={order.symbol}, Side={order.side}, "
        f"Type={order.order_type}, Qty={order.quantity}"
    )
    
    try:
        # 주문 생성
        created_order = await create_order(session, current_user.id, order)
        
        # ✅ OrderOut으로 변환 (order_status 필드명 주의!)
        return OrderOut(
            id=created_order.id,
            user_id=created_order.user_id,
            symbol=created_order.symbol,
            side=created_order.side.value if hasattr(created_order.side, 'value') else str(created_order.side),
            order_type=created_order.order_type.value if hasattr(created_order.order_type, 'value') else str(created_order.order_type),
            order_status=created_order.order_status.value if hasattr(created_order.order_status, 'value') else str(created_order.order_status),  # ✅ order_status
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
    """
    사용자 주문 목록 조회
    
    ### 쿼리 파라미터:
    - **symbol**: 특정 심볼만 조회 (선택)
    - **status**: 특정 상태만 조회 (선택)
    - **limit**: 최대 조회 개수 (기본 100, 최대 500)
    
    ### 응답:
    - 주문 목록 (최신순)
    """
    
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
        
        # ✅ OrderOut으로 변환 (order_status 필드명 주의!)
        return [
            OrderOut(
                id=order.id,
                user_id=order.user_id,
                symbol=order.symbol,
                side=order.side.value if hasattr(order.side, 'value') else str(order.side),
                order_type=order.order_type.value if hasattr(order.order_type, 'value') else str(order.order_type),
                order_status=order.order_status.value if hasattr(order.order_status, 'value') else str(order.order_status),  # ✅ order_status
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
    """
    특정 주문 조회
    
    ### 경로 파라미터:
    - **order_id**: 조회할 주문 ID
    
    ### 응답:
    - 주문 상세 정보
    
    ### 에러:
    - 404: 주문을 찾을 수 없음
    - 403: 접근 권한 없음
    """
    
    try:
        from app.models.database import Order
        
        # 주문 조회
        order = session.get(Order, order_id)
        
        if not order:
            raise HTTPException(
                status_code=404,
                detail="주문을 찾을 수 없습니다"
            )
        
        # 권한 확인
        if order.user_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="이 주문에 접근할 권한이 없습니다"
            )
        
        # ✅ OrderOut으로 변환 (order_status 필드명 주의!)
        return OrderOut(
            id=order.id,
            user_id=order.user_id,
            symbol=order.symbol,
            side=order.side.value if hasattr(order.side, 'value') else str(order.side),
            order_type=order.order_type.value if hasattr(order.order_type, 'value') else str(order.order_type),
            order_status=order.order_status.value if hasattr(order.order_status, 'value') else str(order.order_status),  # ✅ order_status
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
    
    ### 경로 파라미터:
    - **order_id**: 취소할 주문 ID
    
    ### 응답:
    - 취소된 주문 정보 (order_status가 CANCELLED로 변경됨)
    
    ### 에러:
    - 404: 주문을 찾을 수 없음
    - 403: 취소 권한 없음
    - 400: 취소할 수 없는 상태
    """
    
    logger.info(f"🚫 주문 취소 요청: User={current_user.username}, Order ID={order_id}")
    
    try:
        cancelled_order = await cancel_order(session, current_user.id, order_id)
        
        # ✅ OrderOut으로 변환 (order_status 필드명 주의!)
        return OrderOut(
            id=cancelled_order.id,
            user_id=cancelled_order.user_id,
            symbol=cancelled_order.symbol,
            side=cancelled_order.side.value if hasattr(cancelled_order.side, 'value') else str(cancelled_order.side),
            order_type=cancelled_order.order_type.value if hasattr(cancelled_order.order_type, 'value') else str(cancelled_order.order_type),
            order_status=cancelled_order.order_status.value if hasattr(cancelled_order.order_status, 'value') else str(cancelled_order.order_status),  # ✅ order_status
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