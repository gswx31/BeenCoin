from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    hashed_password: str
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    accounts: List["TradingAccount"] = Relationship(back_populates="user")
    orders: List["Order"] = Relationship(back_populates="user")
    transactions: List["TransactionHistory"] = Relationship(back_populates="user")
    alerts: List["PriceAlert"] = Relationship(back_populates="user")


class TradingAccount(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    balance: Decimal = Field(default=Decimal('1000000.00000000'), max_digits=20, decimal_places=8)
    total_profit: Decimal = Field(default=Decimal('0.00000000'), max_digits=20, decimal_places=8)
    # Fee settings
    use_bnb_fee: bool = Field(default=False)  # BNB 수수료 할인 사용 여부
    # 30-day rolling volume for fee tier
    trading_volume_30d: Decimal = Field(default=Decimal('0.00'), max_digits=20, decimal_places=2)
    fee_tier: str = Field(default="Regular")
    user: User = Relationship(back_populates="accounts")
    positions: List["Position"] = Relationship(back_populates="account")


class Order(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    symbol: str = Field(index=True)
    side: str  # BUY / SELL
    order_type: str  # MARKET / LIMIT / STOP_LOSS_LIMIT / TAKE_PROFIT_LIMIT
    order_status: str = Field(default="PENDING", index=True)
    price: Optional[Decimal] = Field(default=None, max_digits=20, decimal_places=8)
    stop_price: Optional[Decimal] = Field(default=None, max_digits=20, decimal_places=8)  # trigger price for stop/TP
    quantity: Decimal = Field(max_digits=20, decimal_places=8)
    filled_quantity: Decimal = Field(default=Decimal('0.00000000'), max_digits=20, decimal_places=8)
    filled_price: Optional[Decimal] = Field(default=None, max_digits=20, decimal_places=8)  # actual avg fill price
    commission: Decimal = Field(default=Decimal('0.00000000'), max_digits=20, decimal_places=8)
    commission_asset: str = Field(default="USDT")  # USDT or BNB
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    user: User = Relationship(back_populates="orders")


class Position(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    account_id: int = Field(foreign_key="tradingaccount.id")
    symbol: str
    quantity: Decimal = Field(default=Decimal('0.00000000'), max_digits=20, decimal_places=8)
    average_price: Decimal = Field(default=Decimal('0.00000000'), max_digits=20, decimal_places=8)  # includes fee in cost basis
    current_value: Decimal = Field(default=Decimal('0.00000000'), max_digits=20, decimal_places=8)
    unrealized_profit: Decimal = Field(default=Decimal('0.00000000'), max_digits=20, decimal_places=8)
    total_cost: Decimal = Field(default=Decimal('0.00000000'), max_digits=20, decimal_places=8)  # total invested incl. fees
    account: TradingAccount = Relationship(back_populates="positions")


class TransactionHistory(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    order_id: Optional[int] = Field(default=None, foreign_key="order.id")
    symbol: str
    side: str
    quantity: Decimal = Field(max_digits=20, decimal_places=8)
    price: Decimal = Field(max_digits=20, decimal_places=8)
    fee: Decimal = Field(default=Decimal('0.00000000'), max_digits=20, decimal_places=8)
    fee_asset: str = Field(default="USDT")
    is_maker: bool = Field(default=False)  # maker or taker
    realized_pnl: Decimal = Field(default=Decimal('0.00000000'), max_digits=20, decimal_places=8)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user: User = Relationship(back_populates="transactions")


class PriceAlert(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    symbol: str = Field(index=True)
    target_price: Decimal = Field(max_digits=20, decimal_places=8)
    condition: str  # ABOVE / BELOW
    is_active: bool = Field(default=True, index=True)
    triggered_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    memo: str = Field(default="")
    user: User = Relationship(back_populates="alerts")


def create_db_and_tables():
    from app.core.database import engine
    SQLModel.metadata.create_all(engine)
