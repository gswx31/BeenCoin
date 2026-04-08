from pydantic import BaseModel, validator
from decimal import Decimal
from typing import Optional
from app.core.config import settings


class OrderCreate(BaseModel):
    symbol: str
    side: str
    order_type: str  # MARKET / LIMIT / STOP_LOSS_LIMIT / TAKE_PROFIT_LIMIT
    quantity: Decimal
    price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None  # trigger price for stop/TP orders

    @validator('symbol')
    def validate_symbol(cls, v):
        if v.upper() not in settings.SUPPORTED_SYMBOLS:
            raise ValueError(f'Unsupported symbol: {v}')
        return v.upper()

    @validator('side')
    def validate_side(cls, v):
        if v.upper() not in ['BUY', 'SELL']:
            raise ValueError('Side must be BUY or SELL')
        return v.upper()

    @validator('order_type')
    def validate_order_type(cls, v):
        valid = ['MARKET', 'LIMIT', 'STOP_LOSS_LIMIT', 'TAKE_PROFIT_LIMIT']
        if v.upper() not in valid:
            raise ValueError(f'Order type must be one of: {valid}')
        return v.upper()

    @validator('price')
    def validate_price(cls, v, values):
        ot = values.get('order_type', '')
        if ot in ('LIMIT', 'STOP_LOSS_LIMIT', 'TAKE_PROFIT_LIMIT') and v is None:
            raise ValueError('Price is required for limit/stop orders')
        if ot == 'MARKET' and v is not None:
            raise ValueError('Price should not be provided for MARKET orders')
        return v

    @validator('stop_price')
    def validate_stop_price(cls, v, values):
        ot = values.get('order_type', '')
        if ot in ('STOP_LOSS_LIMIT', 'TAKE_PROFIT_LIMIT') and v is None:
            raise ValueError('Stop price is required for stop/take-profit orders')
        return v


class OrderOut(BaseModel):
    id: int
    symbol: str
    side: str
    order_type: str
    quantity: Decimal
    price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None
    order_status: str
    filled_quantity: Decimal
    filled_price: Optional[Decimal] = None
    commission: Decimal
    commission_asset: str
    created_at: str
    updated_at: str
