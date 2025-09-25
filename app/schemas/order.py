from pydantic import BaseModel
from decimal import Decimal
from typing import Optional

class OrderCreate(BaseModel):
    symbol: str
    side: str  # 'buy' or 'sell'
    order_type: str  # 'market' or 'limit'
    quantity: Decimal
    price: Optional[Decimal] = None  # for limit orders

class OrderOut(BaseModel):
    id: int
    symbol: str
    side: str
    order_type: str
    status: str
    quantity: Decimal
    filled_quantity: Decimal
    price: Optional[Decimal]
