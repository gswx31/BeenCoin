from pydantic import BaseModel
from decimal import Decimal
from typing import List

class PositionOut(BaseModel):
    symbol: str
    quantity: Decimal
    average_price: Decimal
    current_value: Decimal
    unrealized_profit: Decimal

class AccountOut(BaseModel):
    balance: Decimal
    total_profit: Decimal
    positions: List[PositionOut]
    profit_rate: Decimal
    total_value: Decimal
