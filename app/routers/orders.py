# app/routers/orders.py
"""
Order management routes
"""
from fastapi import APIRouter, Depends, Query
from sqlmodel import Session
from typing import List, Optional
from app.core.database import get_session
from app.models.database import User, OrderStatus
from app.schemas.order import OrderCreate, OrderResponse, OrderCancel
from app.services.order_service import order_service
from app.utils.security import get_current_user

router = APIRouter(prefix="/orders", tags=["Orders"])

@router.post("/", response_model=OrderResponse)
async def create_order(
    order_data: OrderCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new order
    
    Args:
        order_data: Order creation data
        session: Database session
        current_user: Current authenticated user
    
    Returns:
        OrderResponse: Created order
    """
    order = await order_service.create_order(
        session=session,
        user_id=current_user.id,
        order_data=order_data
    )
    
    return order

@router.get("/", response_model=List[OrderResponse])
async def get_orders(
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    status: Optional[OrderStatus] = Query(None, description="Filter by status"),
    limit: int = Query(20, ge=1, le=100, description="Number of results"),
    offset: int = Query(0, ge=0, description="Results offset"),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Get user orders with optional filtering
    
    Args:
        symbol: Optional symbol filter
        status: Optional status filter
        limit: Maximum number of results
        offset: Results offset
        session: Database session
        current_user: Current authenticated user
    
    Returns:
        List[OrderResponse]: List of orders
    """
    orders = await order_service.get_user_orders(
        session=session,
        user_id=current_user.id,
        symbol=symbol,
        status=status,
        limit=limit,
        offset=offset
    )
    
    return orders

@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific order
    
    Args:
        order_id: Order ID
        session: Database session
        current_user: Current authenticated user
    
    Returns:
        OrderResponse: Order details
    """
    from sqlmodel import select
    from app.models.database import Order
    
    order = session.exec(
        select(Order).where(
            Order.id == order_id,
            Order.user_id == current_user.id
        )
    ).first()
    
    if not order:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    return order

@router.delete("/{order_id}", response_model=OrderResponse)
async def cancel_order(
    order_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Cancel an order
    
    Args:
        order_id: Order ID
        session: Database session
        current_user: Current authenticated user
    
    Returns:
        OrderResponse: Cancelled order
    """
    order = await order_service.cancel_order(
        session=session,
        user_id=current_user.id,
        order_id=order_id
    )
    
    return order