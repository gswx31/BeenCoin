# app/models/futures_fills.py
"""
선물 체결 내역 모델
=================

시장가 주문의 분할 체결 정보를 저장
"""

from datetime import datetime
from decimal import Decimal
import uuid

from sqlmodel import Field, SQLModel

class FuturesFill(SQLModel, table=True):
    """
    선물 체결 내역

    시장가 주문이 여러 개의 실제 거래로 분할 체결된 경우,
    각각의 체결 정보를 저장

    예시:
        0.1 BTC 시장가 매수 (100x 레버리지)
        → 실제 10 BTC 거래

        체결 1: 2 BTC @ 50,000
        체결 2: 3 BTC @ 49,900
        체결 3: 5 BTC @ 49,950
    """

    __tablename__ = "futures_fills"

    # 기본 정보
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True, index=True)

    # 연관 관계
    position_id: str = Field(
        foreign_key="futures_positions.id", index=True, description="포지션 ID"
    )

    # 체결 정보
    price: Decimal = Field(max_digits=20, decimal_places=8, description="체결 가격")

    quantity: Decimal = Field(max_digits=20, decimal_places=8, description="체결 수량")

    # 시간
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, index=True, description="체결 시간"
    )

    # 추가 정보
    is_maker: bool | None = Field(default=None, description="메이커 여부 (Binance 데이터)")
