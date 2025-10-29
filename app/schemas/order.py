# app/schemas/order.py
from pydantic import BaseModel, Field, validator
from typing import Optional
from app.core.config import settings


class OrderCreate(BaseModel):
    """주문 생성 요청 스키마"""
    symbol: str = Field(..., description="거래 심볼 (예: BTCUSDT)")
    side: str = Field(..., description="매수/매도 (BUY/SELL)")
    order_type: str = Field(..., description="주문 타입 (MARKET/LIMIT)")
    quantity: float = Field(..., gt=0, description="수량 (0보다 커야 함)")
    price: Optional[float] = Field(None, gt=0, description="가격 (지정가 주문 시 필수)")
    
    @validator('side')
    def validate_side(cls, v):
        """매수/매도 검증"""
        if v not in ['BUY', 'SELL']:
            raise ValueError('side는 BUY 또는 SELL이어야 합니다')
        return v
    
    @validator('order_type')
    def validate_order_type(cls, v):
        """주문 타입 검증"""
        if v not in ['MARKET', 'LIMIT']:
            raise ValueError('order_type은 MARKET 또는 LIMIT이어야 합니다')
        return v
    
    @validator('symbol')
    def validate_symbol(cls, v):
        """지원하는 심볼인지 검증"""
        if v not in settings.SUPPORTED_SYMBOLS:
            raise ValueError(f'지원하지 않는 심볼입니다. 지원 심볼: {", ".join(settings.SUPPORTED_SYMBOLS)}')
        return v
    
    @validator('price')
    def validate_price_for_limit(cls, v, values):
        """지정가 주문일 때 가격 필수"""
        if values.get('order_type') == 'LIMIT' and v is None:
            raise ValueError('지정가 주문은 가격이 필요합니다')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "symbol": "BTCUSDT",
                "side": "BUY",
                "order_type": "MARKET",
                "quantity": 0.001,
                "price": None
            }
        }


class OrderOut(BaseModel):
    """주문 응답 스키마"""
    id: int
    user_id: str
    symbol: str
    side: str
    order_type: str
    order_status: str
    quantity: float
    price: Optional[float]
    filled_quantity: float
    average_price: Optional[float]
    created_at: str
    updated_at: str
    
    class Config:
        schema_extra = {
            "example": {
                "id": 1,
                "user_id": "132412634534-345-345345-345",
                "symbol": "BTCUSDT",
                "side": "BUY",
                "order_type": "MARKET",
                "order_status": "FILLED",
                "quantity": 0.001,
                "price": None,
                "filled_quantity": 0.001,
                "average_price": 50000.00,
                "created_at": "2025-10-17T12:00:00",
                "updated_at": "2025-10-17T12:00:01"
            }
        }


class OrderCancel(BaseModel):
    """주문 취소 요청"""
    order_id: int = Field(..., description="취소할 주문 ID")


class OrderCancelResponse(BaseModel):
    """주문 취소 응답"""
    message: str
    order_id: int