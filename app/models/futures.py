# app/models/futures.py
"""
선물 거래 데이터베이스 모델
"""
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from enum import Enum
import uuid  # ✅ UUID 임포트


# =====================================================
# Enums
# =====================================================

class FuturesPositionSide(str, Enum):
    """선물 포지션 방향"""
    LONG = "LONG"    # 롱 (매수 포지션)
    SHORT = "SHORT"  # 숏 (매도 포지션)


class FuturesOrderType(str, Enum):
    """선물 주문 타입"""
    MARKET = "MARKET"          # 시장가
    LIMIT = "LIMIT"            # 지정가
    STOP_MARKET = "STOP_MARKET"  # 손절 시장가
    TAKE_PROFIT_MARKET = "TAKE_PROFIT_MARKET"  # 익절 시장가


class FuturesPositionStatus(str, Enum):
    """선물 포지션 상태"""
    OPEN = "OPEN"          # 포지션 열림
    CLOSED = "CLOSED"      # 포지션 닫힘
    LIQUIDATED = "LIQUIDATED"  # 청산됨


# =====================================================
# 선물 계정 모델
# =====================================================

class FuturesAccount(SQLModel, table=True):
    """
    선물 거래 계정 (현물 계정과 분리)
    """
    __tablename__ = "futures_accounts"
    
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
        index=True,
        description="선물 계정 UUID"
    )
    user_id: str = Field(foreign_key="users.id", index=True, unique=True)
    
    # 잔액
    balance: Decimal = Field(
        default=Decimal("100000"),  # ✅ 100,000 USDT로 변경
        max_digits=20,
        decimal_places=8,
        description="사용 가능한 증거금"
    )
    margin_used: Decimal = Field(
        default=Decimal("0"),
        max_digits=20,
        decimal_places=8,
        description="포지션에 사용 중인 증거금"
    )
    
    # 수익 정보
    total_profit: Decimal = Field(
        default=Decimal("0"),
        max_digits=20,
        decimal_places=8,
        description="누적 실현 손익"
    )
    unrealized_pnl: Decimal = Field(
        default=Decimal("0"),
        max_digits=20,
        decimal_places=8,
        description="미실현 손익 (모든 포지션 합계)"
    )
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    positions: List["FuturesPosition"] = Relationship(back_populates="account")
    
    @property
    def total_balance(self) -> Decimal:
        """총 자산 = 잔액 + 사용 중 증거금 + 미실현 손익"""
        return self.balance + self.margin_used + self.unrealized_pnl
    
    @property
    def available_balance(self) -> Decimal:
        """사용 가능한 잔액"""
        return self.balance
    
    @property
    def margin_ratio(self) -> Decimal:
        """증거금 비율 (%) = (사용 증거금 / 총 자산) * 100"""
        if self.total_balance <= 0:
            return Decimal("0")
        return (self.margin_used / self.total_balance) * 100


# =====================================================
# 선물 포지션 모델
# =====================================================

class FuturesPosition(SQLModel, table=True):
    """
    선물 포지션
    
    예시:
    - BTC 10x 롱 포지션
    - 진입가: 50,000 USDT
    - 수량: 0.1 BTC
    - 증거금: 500 USDT (50,000 * 0.1 / 10)
    """
    __tablename__ = "futures_positions"
    
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
        index=True,
        description="포지션 UUID"
    )
    account_id: str = Field(foreign_key="futures_accounts.id", index=True)  # ✅ UUID
    
    # 기본 정보
    symbol: str = Field(index=True, max_length=20)
    side: FuturesPositionSide = Field(index=True, description="LONG or SHORT")
    status: FuturesPositionStatus = Field(
        default=FuturesPositionStatus.OPEN,
        index=True
    )
    
    # 레버리지 및 수량
    leverage: int = Field(ge=1, le=125, description="레버리지 (1~125x)")
    quantity: Decimal = Field(
        max_digits=20,
        decimal_places=8,
        description="계약 수량"
    )
    
    # 가격 정보
    entry_price: Decimal = Field(
        max_digits=20,
        decimal_places=8,
        description="진입 평균가"
    )
    mark_price: Decimal = Field(
        default=Decimal("0"),
        max_digits=20,
        decimal_places=8,
        description="현재 마크 가격 (청산 계산용)"
    )
    
    # 증거금
    margin: Decimal = Field(
        max_digits=20,
        decimal_places=8,
        description="사용된 증거금"
    )
    
    # 손익
    unrealized_pnl: Decimal = Field(
        default=Decimal("0"),
        max_digits=20,
        decimal_places=8,
        description="미실현 손익"
    )
    realized_pnl: Decimal = Field(
        default=Decimal("0"),
        max_digits=20,
        decimal_places=8,
        description="실현 손익 (청산 시)"
    )
    
    # 청산 가격
    liquidation_price: Decimal = Field(
        max_digits=20,
        decimal_places=8,
        description="청산 가격"
    )
    
    # 수수료
    fee: Decimal = Field(
        default=Decimal("0"),
        max_digits=20,
        decimal_places=8,
        description="진입 수수료"
    )
    
    # 시간
    opened_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    closed_at: Optional[datetime] = None
    
    # Relationships
    account: Optional[FuturesAccount] = Relationship(back_populates="positions")
    
    @property
    def position_value(self) -> Decimal:
        """포지션 가치 = 진입가 * 수량"""
        return self.entry_price * self.quantity
    
    @property
    def roe_percent(self) -> Decimal:
        """수익률 (ROE %) = (미실현 손익 / 증거금) * 100"""
        if self.margin <= 0:
            return Decimal("0")
        return (self.unrealized_pnl / self.margin) * 100
    
    def calculate_pnl(self, current_price: Decimal) -> Decimal:
        """
        미실현 손익 계산
        
        롱: (현재가 - 진입가) * 수량
        숏: (진입가 - 현재가) * 수량
        """
        if self.side == FuturesPositionSide.LONG:
            return (current_price - self.entry_price) * self.quantity
        else:  # SHORT
            return (self.entry_price - current_price) * self.quantity
    
    def calculate_liquidation_price(self) -> Decimal:
        """
        청산 가격 계산
        
        롱: 진입가 - (증거금 * 0.9 / 수량)
        숏: 진입가 + (증거금 * 0.9 / 수량)
        
        청산 마진: 증거금의 90% (유지 증거금 10%)
        """
        liquidation_margin = self.margin * Decimal("0.9")
        
        if self.side == FuturesPositionSide.LONG:
            return self.entry_price - (liquidation_margin / self.quantity)
        else:  # SHORT
            return self.entry_price + (liquidation_margin / self.quantity)


# =====================================================
# 선물 주문 모델
# =====================================================

class FuturesOrder(SQLModel, table=True):
    """선물 주문"""
    __tablename__ = "futures_orders"
    
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
        index=True,
        description="주문 UUID"
    )
    account_id: str = Field(foreign_key="futures_accounts.id", index=True)  # ✅ UUID
    user_id: str = Field(foreign_key="users.id", index=True)
    position_id: Optional[str] = Field(  # ✅ UUID
        default=None,
        foreign_key="futures_positions.id"
    )
    
    # 주문 정보
    symbol: str = Field(index=True, max_length=20)
    side: FuturesPositionSide = Field(description="LONG or SHORT")
    order_type: FuturesOrderType
    
    # 수량 및 가격
    quantity: Decimal = Field(max_digits=20, decimal_places=8)
    price: Optional[Decimal] = Field(
        default=None,
        max_digits=20,
        decimal_places=8
    )
    leverage: int = Field(ge=1, le=125)
    
    # 주문 상태
    is_close: bool = Field(
        default=False,
        description="포지션 청산 주문인지 여부"
    )
    is_filled: bool = Field(default=False)
    
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    filled_at: Optional[datetime] = None


# =====================================================
# 선물 거래 내역 모델
# =====================================================

class FuturesTransaction(SQLModel, table=True):
    """선물 거래 내역"""
    __tablename__ = "futures_transactions"
    
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
        index=True,
        description="거래 UUID"
    )
    user_id: str = Field(foreign_key="users.id", index=True)
    position_id: str = Field(foreign_key="futures_positions.id", index=True)  # ✅ UUID
    
    # 거래 정보
    symbol: str = Field(index=True, max_length=20)
    side: FuturesPositionSide
    action: str = Field(
        max_length=10,
        description="OPEN(진입) 또는 CLOSE(청산)"
    )
    
    # 수량 및 가격
    quantity: Decimal = Field(max_digits=20, decimal_places=8)
    price: Decimal = Field(max_digits=20, decimal_places=8)
    leverage: int
    
    # 손익
    pnl: Decimal = Field(
        default=Decimal("0"),
        max_digits=20,
        decimal_places=8,
        description="실현 손익 (청산 시에만)"
    )
    fee: Decimal = Field(max_digits=20, decimal_places=8)
    
    timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)