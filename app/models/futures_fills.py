# app/models/futures_fills.py
"""
선물 체결 내역 모델
=================

시장가 주문의 분할 체결 정보를 저장
"""

import uuid
from datetime import datetime
from decimal import Decimal

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


# =====================================================
# futures_service.py에 추가할 함수
# =====================================================

"""
# app/services/futures_service.py

from app.models.futures_fills import FuturesFill

async def open_futures_position(...):
    # ... 기존 코드 ...

    if order_type == FuturesOrderType.MARKET:
        # 시장가 체결
        result = await execute_market_order_with_real_trades(...)

        entry_price = result["average_price"]
        fill_details = result["fills"]

        # 포지션 저장
        session.add(position)
        session.flush()  # position.id 생성

        # ⭐ 체결 내역 저장 (분할 체결)
        for fill in fill_details:
            fill_record = FuturesFill(
                position_id=position.id,
                price=Decimal(str(fill["price"])),
                quantity=Decimal(str(fill["quantity"])),
                timestamp=datetime.fromisoformat(fill["timestamp"])
            )
            session.add(fill_record)

        logger.info(
            f"✅ 체결 내역 저장: {len(fill_details)}건"
        )

    # ... 나머지 코드 ...
"""


# =====================================================
# futures_portfolio.py 개선 - 체결 내역 조회
# =====================================================

"""
# app/routers/futures_portfolio.py

from app.models.futures_fills import FuturesFill

@router.get("/fills/{position_id}", response_model=List[FillDetail])
async def get_position_fills(
    position_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    '''특정 포지션의 체결 내역 조회'''

    # 포지션 확인 및 권한 체크
    position = session.get(FuturesPosition, position_id)
    if not position:
        raise HTTPException(404, "포지션을 찾을 수 없습니다")

    account = session.get(FuturesAccount, position.account_id)
    if account.user_id != current_user.id:
        raise HTTPException(403, "권한이 없습니다")

    # ⭐ 체결 내역 조회 (분할 체결)
    fills = session.exec(
        select(FuturesFill)
        .where(FuturesFill.position_id == position_id)
        .order_by(FuturesFill.timestamp.asc())
    ).all()

    if not fills:
        # 체결 내역이 없으면 포지션 정보로 단일 체결 반환
        return [FillDetail(
            price=float(position.entry_price),
            quantity=float(position.quantity),
            timestamp=position.opened_at.isoformat()
        )]

    # 분할 체결 반환
    return [
        FillDetail(
            price=float(fill.price),
            quantity=float(fill.quantity),
            timestamp=fill.timestamp.isoformat()
        )
        for fill in fills
    ]
"""


# =====================================================
# 데이터베이스 마이그레이션
# =====================================================

"""
# alembic/versions/xxx_add_futures_fills.py

def upgrade():
    op.create_table(
        'futures_fills',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('position_id', sa.String(), nullable=False),
        sa.Column('price', sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column('quantity', sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('is_maker', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['position_id'], ['futures_positions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_futures_fills_position_id', 'futures_fills', ['position_id'])
    op.create_index('ix_futures_fills_timestamp', 'futures_fills', ['timestamp'])


def downgrade():
    op.drop_index('ix_futures_fills_timestamp', table_name='futures_fills')
    op.drop_index('ix_futures_fills_position_id', table_name='futures_fills')
    op.drop_table('futures_fills')
"""
