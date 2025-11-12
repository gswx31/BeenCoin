# app/models/futures.py
"""
Futures trading models
"""
from sqlmodel import Field, SQLModel, Relationship
from typing import Optional
from datetime import datetime
from decimal import Decimal
from enum import Enum

class FuturesOrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_MARKET = "STOP_MARKET"
    TAKE_PROFIT = "TAKE_PROFIT"
    TAKE_PROFIT_MARKET = "TAKE_PROFIT_MARKET"

class FuturesPositionSide(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"

class FuturesPositionStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    LIQUIDATED = "LIQUIDATED"

# Futures Account Model
class FuturesAccount(SQLModel, table=True):
    """Futures trading account"""
    __tablename__ = "futures_accounts"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", unique=True)
    usdt_balance: Decimal = Field(default=100000.0)
    margin_balance: Decimal = Field(default=0.0)
    unrealized_pnl: Decimal = Field(default=0.0)
    realized_pnl: Decimal = Field(default=0.0)
    total_volume: Decimal = Field(default=0.0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

# Futures Position Model
class FuturesPosition(SQLModel, table=True):
    """Futures position model"""
    __tablename__ = "futures_positions"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    symbol: str = Field(index=True)
    side: FuturesPositionSide
    quantity: Decimal
    entry_price: Decimal
    mark_price: Optional[Decimal] = None
    liquidation_price: Optional[Decimal] = None
    leverage: int = Field(default=1)
    margin: Decimal
    unrealized_pnl: Decimal = Field(default=0.0)
    realized_pnl: Decimal = Field(default=0.0)
    status: FuturesPositionStatus = Field(default=FuturesPositionStatus.OPEN)
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

# Futures Order Model  
class FuturesOrder(SQLModel, table=True):
    """Futures order model"""
    __tablename__ = "futures_orders"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    position_id: Optional[int] = Field(foreign_key="futures_positions.id")
    symbol: str = Field(index=True)
    order_type: FuturesOrderType
    side: FuturesPositionSide
    quantity: Decimal
    price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None
    leverage: int = Field(default=1)
    status: str = Field(default="PENDING")
    executed_quantity: Decimal = Field(default=0.0)
    executed_price: Optional[Decimal] = None
    fee: Decimal = Field(default=0.0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

# Futures Transaction Model
class FuturesTransaction(SQLModel, table=True):
    """Futures transaction history"""
    __tablename__ = "futures_transactions"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    order_id: Optional[int] = Field(foreign_key="futures_orders.id")
    transaction_type: str  # OPEN_POSITION, CLOSE_POSITION, LIQUIDATION, FEE, FUNDING
    amount: Decimal
    balance_after: Decimal
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)