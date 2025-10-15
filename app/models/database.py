# app/models/database.py
from sqlmodel import SQLModel, Field, Relationship, create_engine
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from enum import Enum
from app.core.config import settings

class TradingType(str, Enum):
    SPOT = "SPOT"
    FUTURES = "FUTURES"

class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

class PositionSide(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    BOTH = "BOTH"  # 단방향 모드

class MarginType(str, Enum):
    ISOLATED = "ISOLATED"
    CROSS = "CROSS"

class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_MARKET = "STOP_MARKET"
    TAKE_PROFIT_MARKET = "TAKE_PROFIT_MARKET"

class OrderStatus(str, Enum):
    PENDING = "PENDING"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"

class User(SQLModel, table=True):
    __tablename__ = "users"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True, max_length=50)
    hashed_password: str = Field(max_length=255)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    spot_account: Optional["SpotAccount"] = Relationship(back_populates="user")
    futures_account: Optional["FuturesAccount"] = Relationship(back_populates="user")
    orders: List["Order"] = Relationship(back_populates="user")
    futures_positions: List["FuturesPosition"] = Relationship(back_populates="user")

class SpotAccount(SQLModel, table=True):
    """현물 계정"""
    __tablename__ = "spot_accounts"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", unique=True)
    usdt_balance: Decimal = Field(default=Decimal('1000000.00'), max_digits=20, decimal_places=8)
    total_profit: Decimal = Field(default=Decimal('0.00'), max_digits=20, decimal_places=8)
    
    # Relationships
    user: User = Relationship(back_populates="spot_account")
    positions: List["SpotPosition"] = Relationship(back_populates="account")

class FuturesAccount(SQLModel, table=True):
    """선물 계정"""
    __tablename__ = "futures_accounts"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", unique=True)
    usdt_balance: Decimal = Field(default=Decimal('1000000.00'), max_digits=20, decimal_places=8)
    total_realized_pnl: Decimal = Field(default=Decimal('0.00'), max_digits=20, decimal_places=8)
    total_unrealized_pnl: Decimal = Field(default=Decimal('0.00'), max_digits=20, decimal_places=8)
    total_margin: Decimal = Field(default=Decimal('0.00'), max_digits=20, decimal_places=8)
    available_balance: Decimal = Field(default=Decimal('1000000.00'), max_digits=20, decimal_places=8)
    
    # Relationships
    user: User = Relationship(back_populates="futures_account")

class SpotPosition(SQLModel, table=True):
    """현물 포지션"""
    __tablename__ = "spot_positions"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    account_id: int = Field(foreign_key="spot_accounts.id")
    symbol: str = Field(max_length=20, index=True)
    quantity: Decimal = Field(default=Decimal('0'), max_digits=20, decimal_places=8)
    average_price: Decimal = Field(default=Decimal('0'), max_digits=20, decimal_places=8)
    current_price: Decimal = Field(default=Decimal('0'), max_digits=20, decimal_places=8)
    current_value: Decimal = Field(default=Decimal('0'), max_digits=20, decimal_places=8)
    unrealized_profit: Decimal = Field(default=Decimal('0'), max_digits=20, decimal_places=8)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    account: SpotAccount = Relationship(back_populates="positions")

class FuturesPosition(SQLModel, table=True):
    """선물 포지션"""
    __tablename__ = "futures_positions"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    symbol: str = Field(max_length=20, index=True)
    position_side: PositionSide = Field(default=PositionSide.BOTH)
    quantity: Decimal = Field(default=Decimal('0'), max_digits=20, decimal_places=8)
    entry_price: Decimal = Field(default=Decimal('0'), max_digits=20, decimal_places=8)
    mark_price: Decimal = Field(default=Decimal('0'), max_digits=20, decimal_places=8)
    liquidation_price: Decimal = Field(default=Decimal('0'), max_digits=20, decimal_places=8)
    leverage: int = Field(default=1, ge=1, le=125)
    margin_type: MarginType = Field(default=MarginType.ISOLATED)
    margin: Decimal = Field(default=Decimal('0'), max_digits=20, decimal_places=8)
    unrealized_pnl: Decimal = Field(default=Decimal('0'), max_digits=20, decimal_places=8)
    realized_pnl: Decimal = Field(default=Decimal('0'), max_digits=20, decimal_places=8)
    percentage_pnl: Decimal = Field(default=Decimal('0'), max_digits=10, decimal_places=2)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # 손절/익절 설정
    stop_loss: Optional[Decimal] = Field(default=None, max_digits=20, decimal_places=8)
    take_profit: Optional[Decimal] = Field(default=None, max_digits=20, decimal_places=8)
    
    # Relationships
    user: User = Relationship(back_populates="futures_positions")

class Order(SQLModel, table=True):
    """통합 주문 (현물/선물)"""
    __tablename__ = "orders"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    trading_type: TradingType = Field(default=TradingType.SPOT)
    symbol: str = Field(max_length=20, index=True)
    side: OrderSide
    order_type: OrderType
    status: OrderStatus = Field(default=OrderStatus.PENDING)
    quantity: Decimal = Field(max_digits=20, decimal_places=8)
    price: Optional[Decimal] = Field(default=None, max_digits=20, decimal_places=8)
    filled_quantity: Decimal = Field(default=Decimal('0'), max_digits=20, decimal_places=8)
    average_price: Optional[Decimal] = Field(default=None, max_digits=20, decimal_places=8)
    
    # 선물 전용 필드
    position_side: Optional[PositionSide] = Field(default=None)
    leverage: Optional[int] = Field(default=None, ge=1, le=125)
    reduce_only: bool = Field(default=False)
    close_position: bool = Field(default=False)
    
    # 손절/익절
    stop_price: Optional[Decimal] = Field(default=None, max_digits=20, decimal_places=8)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    user: User = Relationship(back_populates="orders")

class Transaction(SQLModel, table=True):
    """거래 내역"""
    __tablename__ = "transactions"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    order_id: Optional[int] = Field(foreign_key="orders.id")
    trading_type: TradingType
    symbol: str = Field(max_length=20)
    side: OrderSide
    quantity: Decimal = Field(max_digits=20, decimal_places=8)
    price: Decimal = Field(max_digits=20, decimal_places=8)
    fee: Decimal = Field(default=Decimal('0'), max_digits=20, decimal_places=8)
    realized_pnl: Optional[Decimal] = Field(default=None, max_digits=20, decimal_places=8)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

def create_db_and_tables():
    """데이터베이스 및 테이블 생성"""
    # aiosqlite를 sqlite로 변경 (동기 방식)
    sync_db_url = settings.DATABASE_URL.replace("sqlite+aiosqlite://", "sqlite:///")
    
    print(f"Creating database: {sync_db_url}")
    
    engine = create_engine(sync_db_url, echo=False)
    SQLModel.metadata.create_all(engine)
    
    print("✅ Database and tables created successfully!")
    
    # 생성된 테이블 확인
    import sqlite3
    db_file = sync_db_url.replace("sqlite:///", "")
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    print("\n📋 Created tables:")
    for table in tables:
        print(f"  - {table[0]}")
    
    conn.close()