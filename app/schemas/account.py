from pydantic import BaseModel
from decimal import Decimal
from typing import List, Optional


class PositionOut(BaseModel):
    symbol: str
    quantity: Decimal
    average_price: Decimal
    current_value: Decimal
    unrealized_profit: Decimal
    total_cost: Decimal


class FeeInfo(BaseModel):
    tier: str
    maker_fee: str
    taker_fee: str
    bnb_discount: bool
    volume_30d: str


class AccountOut(BaseModel):
    balance: Decimal
    total_profit: Decimal
    positions: List[PositionOut]
    profit_rate: Decimal
    total_value: Decimal
    fee_info: FeeInfo
