from pydantic import BaseModel, validator
from decimal import Decimal
from typing import Optional
from app.core.config import settings

class OrderCreate(BaseModel):
    symbol: str
    side: str
    order_type: str
    quantity: Decimal
    price: Optional[Decimal] = None

    @validator('symbol')
    def validate_symbol(cls, v):
        if v.upper() not in settings.SUPPORTED_SYMBOLS:
            raise ValueError(f'Unsupported symbol: {v}. Supported: {settings.SUPPORTED_SYMBOLS}')
        return v.upper()

    @validator('side')
    def validate_side(cls, v):
        if v.upper() not in ['BUY', 'SELL']:
            raise ValueError('Side must be BUY or SELL')
        return v.upper()

    @validator('order_type')
    def validate_order_type(cls, v):
        if v.upper() not in ['MARKET', 'LIMIT']:
            raise ValueError('Order type must be MARKET or LIMIT')
        return v.upper()

    @validator('price')
    def validate_price(cls, v, values):
        if values.get('order_type') == 'LIMIT' and v is None:
            raise ValueError('Price is required for LIMIT orders')
        if values.get('order_type') == 'MARKET' and v is not None:
            raise ValueError('Price should not be provided for MARKET orders')
        return v

class OrderOut(OrderCreate):
    id: int
    order_status: str
    filled_quantity: Decimal
    created_at: str
    updated_at: str
