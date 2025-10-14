# app/models/database.py
from sqlmodel import SQLModel, Field, Relationship, create_engine
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from app.core.config import settings

class User(SQLModel, table=True):
    __tablename__ = "user"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True, max_length=50)
    hashed_password: str = Field(max_length=255)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    accounts: List["TradingAccount"] = Relationship(back_populates="user")
    orders: List["Order"] = Relationship(back_populates="user")
    transactions: List["TransactionHistory"] = Relationship(back_populates="user")

class TradingAccount(SQLModel, table=True):
    __tablename__ = "tradingaccount"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    balance: Decimal = Field(default=Decimal('1000000.00'), max_digits=20, decimal_places=8)
    total_profit: Decimal = Field(default=Decimal('0.00'), max_digits=20, decimal_places=8)
    
    # Relationships
    user: User = Relationship(back_populates="accounts")
    positions: List["Position"] = Relationship(back_populates="account")

class Order(SQLModel, table=True):
    __tablename__ = "order"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    symbol: str = Field(max_length=20)
    side: str = Field(max_length=10)  # BUY or SELL
    order_type: str = Field(max_length=10)  # MARKET or LIMIT
    order_status: str = Field(default="PENDING", max_length=20)
    price: Optional[Decimal] = Field(default=None, max_digits=20, decimal_places=8)
    quantity: Decimal = Field(max_digits=20, decimal_places=8)
    filled_quantity: Decimal = Field(default=Decimal('0'), max_digits=20, decimal_places=8)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    user: User = Relationship(back_populates="orders")

class Position(SQLModel, table=True):
    __tablename__ = "position"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    account_id: int = Field(foreign_key="tradingaccount.id")
    symbol: str = Field(max_length=20)
    quantity: Decimal = Field(default=Decimal('0'), max_digits=20, decimal_places=8)
    average_price: Decimal = Field(default=Decimal('0'), max_digits=20, decimal_places=8)
    current_value: Decimal = Field(default=Decimal('0'), max_digits=20, decimal_places=8)
    unrealized_profit: Decimal = Field(default=Decimal('0'), max_digits=20, decimal_places=8)
    
    # Relationships
    account: TradingAccount = Relationship(back_populates="positions")

class TransactionHistory(SQLModel, table=True):
    __tablename__ = "transactionhistory"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    order_id: Optional[int] = Field(default=None, foreign_key="order.id")
    symbol: str = Field(max_length=20)
    side: str = Field(max_length=10)
    quantity: Decimal = Field(max_digits=20, decimal_places=8)
    price: Decimal = Field(max_digits=20, decimal_places=8)
    fee: Decimal = Field(default=Decimal('0'), max_digits=20, decimal_places=8)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    user: User = Relationship(back_populates="transactions")

def create_db_and_tables():
    """데이터베이스 및 테이블 생성"""
    # aiosqlite를 sqlite로 변경 (동기 방식)
    sync_db_url = settings.DATABASE_URL.replace("sqlite+aiosqlite://", "sqlite:///")
    
    print(f"Creating database: {sync_db_url}")
    
    engine = create_engine(sync_db_url, echo=True)
    SQLModel.metadata.create_all(engine)
    
    print("✅ Database and tables created successfully!")