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
    # Streak
    current_streak: int = Field(default=0)
    best_streak: int = Field(default=0)
    last_profit_date: Optional[str] = Field(default=None)  # "YYYY-MM-DD"
    # Relationships
    accounts: List["TradingAccount"] = Relationship(back_populates="user")
    orders: List["Order"] = Relationship(back_populates="user")
    transactions: List["TransactionHistory"] = Relationship(back_populates="user")
    alerts: List["PriceAlert"] = Relationship(back_populates="user")
    achievements: List["UserAchievement"] = Relationship(back_populates="user")
    missions: List["UserMission"] = Relationship(back_populates="user")


class TradingAccount(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    balance: Decimal = Field(default=Decimal('1000000.00000000'), max_digits=20, decimal_places=8)
    total_profit: Decimal = Field(default=Decimal('0.00000000'), max_digits=20, decimal_places=8)
    use_bnb_fee: bool = Field(default=False)
    trading_volume_30d: Decimal = Field(default=Decimal('0.00'), max_digits=20, decimal_places=2)
    fee_tier: str = Field(default="Regular")
    user: User = Relationship(back_populates="accounts")
    positions: List["Position"] = Relationship(back_populates="account")


class Order(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    symbol: str = Field(index=True)
    side: str
    order_type: str
    order_status: str = Field(default="PENDING", index=True)
    price: Optional[Decimal] = Field(default=None, max_digits=20, decimal_places=8)
    stop_price: Optional[Decimal] = Field(default=None, max_digits=20, decimal_places=8)
    quantity: Decimal = Field(max_digits=20, decimal_places=8)
    filled_quantity: Decimal = Field(default=Decimal('0.00000000'), max_digits=20, decimal_places=8)
    filled_price: Optional[Decimal] = Field(default=None, max_digits=20, decimal_places=8)
    commission: Decimal = Field(default=Decimal('0.00000000'), max_digits=20, decimal_places=8)
    commission_asset: str = Field(default="USDT")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    user: User = Relationship(back_populates="orders")


class Position(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    account_id: int = Field(foreign_key="tradingaccount.id")
    symbol: str
    quantity: Decimal = Field(default=Decimal('0.00000000'), max_digits=20, decimal_places=8)
    average_price: Decimal = Field(default=Decimal('0.00000000'), max_digits=20, decimal_places=8)
    current_value: Decimal = Field(default=Decimal('0.00000000'), max_digits=20, decimal_places=8)
    unrealized_profit: Decimal = Field(default=Decimal('0.00000000'), max_digits=20, decimal_places=8)
    total_cost: Decimal = Field(default=Decimal('0.00000000'), max_digits=20, decimal_places=8)
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
    is_maker: bool = Field(default=False)
    realized_pnl: Decimal = Field(default=Decimal('0.00000000'), max_digits=20, decimal_places=8)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user: User = Relationship(back_populates="transactions")


class PriceAlert(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    symbol: str = Field(index=True)
    target_price: Decimal = Field(max_digits=20, decimal_places=8)
    condition: str
    is_active: bool = Field(default=True, index=True)
    triggered_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    memo: str = Field(default="")
    user: User = Relationship(back_populates="alerts")


# -- Achievement System --

class UserAchievement(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    achievement_key: str = Field(index=True)  # e.g. "first_trade"
    unlocked_at: datetime = Field(default_factory=datetime.utcnow)
    user: User = Relationship(back_populates="achievements")


# -- Daily Mission System --

class UserMission(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    mission_key: str  # e.g. "trade_3_times"
    mission_date: str  # "YYYY-MM-DD"
    target_value: int = Field(default=1)
    current_value: int = Field(default=0)
    is_completed: bool = Field(default=False)
    reward_claimed: bool = Field(default=False)
    reward_amount: Decimal = Field(default=Decimal('0'), max_digits=20, decimal_places=2)
    user: User = Relationship(back_populates="missions")


def create_db_and_tables():
    from app.core.database import engine
    SQLModel.metadata.create_all(engine)
