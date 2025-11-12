# app/schemas/order.py
"""
Order schemas for request/response validation
"""
from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime
from decimal import Decimal
from app.models.database import OrderType, OrderSide, OrderStatus

class OrderBase(BaseModel):
    """Base order schema"""
    symbol: str
    order_type: OrderType
    order_side: OrderSide
    quantity: Decimal = Field(..., gt=0)
    price: Optional[Decimal] = Field(None, gt=0)
    stop_price: Optional[Decimal] = Field(None, gt=0)
    
    @validator('price')
    def validate_price_for_limit(cls, v, values):
        if values.get('order_type') == OrderType.LIMIT and v is None:
            raise ValueError('Price is required for LIMIT orders')
        return v
    
    @validator('stop_price')
    def validate_stop_price(cls, v, values):
        if values.get('order_type') in [OrderType.STOP_LOSS, OrderType.TAKE_PROFIT] and v is None:
            raise ValueError('Stop price is required for STOP_LOSS and TAKE_PROFIT orders')
        return v

class OrderCreate(OrderBase):
    """Order creation schema"""
    pass

class OrderResponse(OrderBase):
    """Order response schema"""
    id: int
    user_id: int
    order_status: OrderStatus
    executed_quantity: Decimal
    executed_price: Optional[Decimal]
    fee: Decimal
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class OrderUpdate(BaseModel):
    """Order update schema"""
    price: Optional[Decimal] = Field(None, gt=0)
    quantity: Optional[Decimal] = Field(None, gt=0)
    stop_price: Optional[Decimal] = Field(None, gt=0)

class OrderCancel(BaseModel):
    """Order cancellation schema"""
    order_id: int
    reason: Optional[str] = None