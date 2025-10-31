# app/schemas/order.py
"""
주문 관련 스키마 - 수정 버전
손절/익절 주문 지원
"""
from pydantic import BaseModel, Field, field_validator
from decimal import Decimal
from datetime import datetime
from typing import Optional


class OrderCreate(BaseModel):
    """주문 생성 요청"""
    symbol: str = Field(..., description="거래 심볼 (예: BTCUSDT)")
    side: str = Field(..., description="BUY 또는 SELL")
    order_type: str = Field(..., description="MARKET, LIMIT, STOP_LOSS, TAKE_PROFIT")
    quantity: Decimal = Field(..., gt=0, description="주문 수량")
    price: Optional[Decimal] = Field(None, gt=0, description="지정가 (LIMIT만)")
    stop_price: Optional[Decimal] = Field(None, gt=0, description="손절/익절 가격")
    
    @field_validator('side')
    @classmethod
    def validate_side(cls, v):
        if v not in ['BUY', 'SELL']:
            raise ValueError('side must be BUY or SELL')
        return v
    
    @field_validator('order_type')
    @classmethod
    def validate_order_type(cls, v):
        if v not in ['MARKET', 'LIMIT', 'STOP_LOSS', 'TAKE_PROFIT']:
            raise ValueError('Invalid order_type')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "symbol": "BTCUSDT",
                "side": "BUY",
                "order_type": "MARKET",
                "quantity": "0.1"
            }
        }


class OrderOut(BaseModel):
    """주문 응답"""
    id: int
    user_id: str
    symbol: str
    side: str
    order_type: str
    order_status: str
    quantity: Decimal
    price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None
    filled_quantity: Decimal
    average_price: Optional[Decimal] = None
    fee: Optional[Decimal] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class OrderListOut(BaseModel):
    """주문 목록 응답"""
    orders: list[OrderOut]
    total: int