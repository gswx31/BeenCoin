# app/models/database.py
"""
데이터베이스 모델 - 제약 조건 및 인덱스 추가
"""
from sqlmodel import Field, SQLModel, Relationship
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from enum import Enum
from sqlalchemy import UniqueConstraint, Index, CheckConstraint, Column, Numeric


# ========================================
# Enum 정의
# ========================================

class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class TradingType(str, Enum):
    SPOT = "SPOT"


# ========================================
# 사용자 모델
# ========================================
class User(SQLModel, table=True):
    __tablename__ = "users"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True, max_length=50)
    hashed_password: str = Field(max_length=255)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # ✅ FUTURES_ACCOUNT 관계 추가 (핵심 수정!)
    spot_account: Optional["SpotAccount"] = Relationship(back_populates="user")
    futures_account: Optional["FuturesAccount"] = Relationship(back_populates="user")  # ✅ 추가
    orders: List["Order"] = Relationship(back_populates="user")
    transactions: List["Transaction"] = Relationship(back_populates="user")
# ========================================
# 현물 거래 계정
# ========================================

class SpotAccount(SQLModel, table=True):
    __tablename__ = "spot_accounts"
    
    # ✅ 제약 조건 추가
    __table_args__ = (
        CheckConstraint('usdt_balance >= 0', name='check_positive_balance'),
        CheckConstraint('total_profit >= -1000000', name='check_reasonable_profit'),
        Index('idx_user_balance', 'user_id', 'usdt_balance'),
    )
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", unique=True, index=True)
    
    # ✅ Decimal 타입 명시적 설정
    usdt_balance: Decimal = Field(
        sa_column=Column(Numeric(20, 8), nullable=False),
        default=Decimal('0')
    )
    total_profit: Decimal = Field(
        sa_column=Column(Numeric(20, 8), nullable=False),
        default=Decimal('0')
    )
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # 관계
    user: User = Relationship(back_populates="spot_account")
    positions: List["SpotPosition"] = Relationship(back_populates="account")


# ========================================
# 현물 포지션
# ========================================

class SpotPosition(SQLModel, table=True):
    __tablename__ = "spot_positions"
    
    # ✅ 제약 조건 추가
    __table_args__ = (
        UniqueConstraint('account_id', 'symbol', name='uix_account_symbol'),
        CheckConstraint('quantity >= 0', name='check_positive_quantity'),
        CheckConstraint('average_price >= 0', name='check_positive_price'),
        Index('idx_account_symbol', 'account_id', 'symbol'),
        Index('idx_symbol_quantity', 'symbol', 'quantity'),
    )
    
    id: Optional[int] = Field(default=None, primary_key=True)
    account_id: int = Field(foreign_key="spot_accounts.id", index=True)
    symbol: str = Field(max_length=20, index=True)
    
    # ✅ Decimal 타입 명시적 설정
    quantity: Decimal = Field(
        sa_column=Column(Numeric(20, 8), nullable=False),
        default=Decimal('0')
    )
    average_price: Decimal = Field(
        sa_column=Column(Numeric(20, 8), nullable=False),
        default=Decimal('0')
    )
    current_price: Decimal = Field(
        sa_column=Column(Numeric(20, 8), nullable=False),
        default=Decimal('0')
    )
    current_value: Decimal = Field(
        sa_column=Column(Numeric(20, 8), nullable=False),
        default=Decimal('0')
    )
    unrealized_profit: Decimal = Field(
        sa_column=Column(Numeric(20, 8), nullable=False),
        default=Decimal('0')
    )
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # 관계
    account: SpotAccount = Relationship(back_populates="positions")


# ========================================
# 주문
# ========================================

class Order(SQLModel, table=True):
    __tablename__ = "orders"
    
    # ✅ 제약 조건 및 인덱스 추가
    __table_args__ = (
        CheckConstraint('quantity > 0', name='check_positive_order_quantity'),
        CheckConstraint('filled_quantity >= 0', name='check_positive_filled'),
        CheckConstraint('filled_quantity <= quantity', name='check_filled_not_exceed'),
        Index('idx_user_status', 'user_id', 'order_status'),
        Index('idx_symbol_created', 'symbol', 'created_at'),
        Index('idx_status_created', 'order_status', 'created_at'),
    )
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    trading_type: TradingType = Field(default=TradingType.SPOT)
    
    symbol: str = Field(max_length=20, index=True)
    side: OrderSide
    order_type: OrderType
    order_status: OrderStatus = Field(default=OrderStatus.PENDING, index=True)
    
    # ✅ Decimal 타입 명시적 설정
    quantity: Decimal = Field(
        sa_column=Column(Numeric(20, 8), nullable=False)
    )
    price: Optional[Decimal] = Field(
        sa_column=Column(Numeric(20, 8), nullable=True),
        default=None
    )
    filled_quantity: Decimal = Field(
        sa_column=Column(Numeric(20, 8), nullable=False),
        default=Decimal('0')
    )
    average_price: Optional[Decimal] = Field(
        sa_column=Column(Numeric(20, 8), nullable=True),
        default=None
    )
    
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # 관계
    user: User = Relationship(back_populates="orders")
    transactions: List["Transaction"] = Relationship(back_populates="order")


# ========================================
# 거래 내역
# ========================================

class Transaction(SQLModel, table=True):
    __tablename__ = "transactions"
    
    # ✅ 인덱스 추가
    __table_args__ = (
        CheckConstraint('quantity > 0', name='check_positive_tx_quantity'),
        CheckConstraint('price > 0', name='check_positive_tx_price'),
        CheckConstraint('fee >= 0', name='check_non_negative_fee'),
        Index('idx_user_timestamp', 'user_id', 'timestamp'),
        Index('idx_order_timestamp', 'order_id', 'timestamp'),
        Index('idx_symbol_timestamp', 'symbol', 'timestamp'),
    )
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    order_id: int = Field(foreign_key="orders.id", index=True)
    trading_type: TradingType = Field(default=TradingType.SPOT)
    
    symbol: str = Field(max_length=20, index=True)
    side: OrderSide
    
    # ✅ Decimal 타입 명시적 설정
    quantity: Decimal = Field(
        sa_column=Column(Numeric(20, 8), nullable=False)
    )
    price: Decimal = Field(
        sa_column=Column(Numeric(20, 8), nullable=False)
    )
    fee: Decimal = Field(
        sa_column=Column(Numeric(20, 8), nullable=False),
        default=Decimal('0')
    )
    
    timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)
    
    # 관계
    user: User = Relationship(back_populates="transactions")
    order: Order = Relationship(back_populates="transactions")
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

# ========================================
# 마이그레이션 헬퍼 함수
# ========================================

def create_all_tables():
    """모든 테이블 생성"""
    from app.core.database import engine
    SQLModel.metadata.create_all(engine)
    print("✅ 모든 테이블이 생성되었습니다")


def drop_all_tables():
    """모든 테이블 삭제"""
    from app.core.database import engine
    SQLModel.metadata.drop_all(engine)
    print("❌ 모든 테이블이 삭제되었습니다")