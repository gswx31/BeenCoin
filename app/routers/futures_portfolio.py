# app/routers/futures_portfolio.py
"""
선물 포트폴리오 API - 포지션, 계정, 체결 내역
===========================================

기능:
1. 선물 계정 요약
2. 포지션 목록 (OPEN, PENDING, CLOSED)
3. 체결 내역 (분할 체결 포함)
4. 거래 통계
"""

from datetime import datetime, timedelta
import logging

from fastapi import APIRouter, Depends, HTTPException, Query  # ⭐ HTTPException 추가
from pydantic import BaseModel
from sqlmodel import Session, select

from app.core.database import get_session
from app.models.database import User
from app.models.futures import (
    FuturesAccount,
    FuturesPosition,
    FuturesPositionStatus,
    FuturesTransaction,
)
from app.models.futures_fills import FuturesFill
from app.utils.security import get_current_user

router = APIRouter(prefix="/futures/portfolio", tags=["futures-portfolio"])
logger = logging.getLogger(__name__)


# =====================================================
# Response Schemas
# =====================================================


class FuturesPortfolioSummary(BaseModel):
    """선물 포트폴리오 요약"""

    # 계정 정보
    total_balance: float  # 총 자산
    available_balance: float  # 사용 가능한 잔액
    margin_used: float  # 사용 중인 증거금
    unrealized_pnl: float  # 미실현 손익
    total_profit: float  # 실현 손익 누적
    margin_ratio: float  # 증거금 비율 (%)

    # 포지션 정보
    open_positions_count: int  # OPEN 포지션 개수
    pending_positions_count: int  # PENDING 포지션 개수
    total_position_value: float  # 총 포지션 가치

    # 통계
    win_rate: float  # 승률 (%)
    total_trades: int  # 총 거래 횟수
    avg_roe: float  # 평균 수익률 (%)


class PositionDetail(BaseModel):
    """포지션 상세"""

    id: str
    symbol: str
    side: str  # LONG or SHORT
    status: str  # OPEN, PENDING, CLOSED, LIQUIDATED

    # 수량 및 가격
    quantity: float  # 포지션 크기 (레버리지 적용 후)
    entry_price: float  # 진입 평균가
    mark_price: float  # 현재 마크 가격
    liquidation_price: float  # 청산가

    # 레버리지 및 증거금
    leverage: int  # 레버리지
    margin: float  # 사용된 증거금

    # 손익
    unrealized_pnl: float  # 미실현 손익
    realized_pnl: float  # 실현 손익
    roe_percent: float  # 수익률 (%)

    # 시간
    opened_at: str
    closed_at: str | None

    # 체결 내역 (분할 체결)
    fill_details: list[dict] | None = None


class FillDetail(BaseModel):
    """체결 내역 상세"""

    price: float
    quantity: float
    timestamp: str


class TransactionDetail(BaseModel):
    """거래 내역"""

    id: str
    position_id: str
    symbol: str
    side: str
    action: str  # OPEN, CLOSE, LIQUIDATION, LIMIT_FILLED
    quantity: float
    price: float
    leverage: int
    pnl: float
    fee: float
    timestamp: str

    # 분할 체결 정보
    fill_count: int = 1  # 체결 건수
    fills: list[FillDetail] | None = None


# =====================================================
# 1. 포트폴리오 요약
# =====================================================


@router.get("/summary", response_model=FuturesPortfolioSummary)
async def get_portfolio_summary(
    current_user: User = Depends(get_current_user), session: Session = Depends(get_session)
):
    """
    선물 포트폴리오 요약

    - 계정 잔액, 증거금, 손익
    - 포지션 통계
    - 거래 승률
    """
    try:
        # 1. 계정 조회
        account = session.exec(
            select(FuturesAccount).where(FuturesAccount.user_id == current_user.id)
        ).first()

        if not account:
            # 계정이 없으면 초기값 반환
            return FuturesPortfolioSummary(
                total_balance=0,
                available_balance=0,
                margin_used=0,
                unrealized_pnl=0,
                total_profit=0,
                margin_ratio=0,
                open_positions_count=0,
                pending_positions_count=0,
                total_position_value=0,
                win_rate=0,
                total_trades=0,
                avg_roe=0,
            )

        # 2. 포지션 통계
        open_positions = session.exec(
            select(FuturesPosition).where(
                FuturesPosition.account_id == account.id,
                FuturesPosition.status == FuturesPositionStatus.OPEN,
            )
        ).all()

        pending_positions = session.exec(
            select(FuturesPosition).where(
                FuturesPosition.account_id == account.id,
                FuturesPosition.status == FuturesPositionStatus.PENDING,
            )
        ).all()

        total_position_value = sum(float(pos.entry_price * pos.quantity) for pos in open_positions)

        # 3. 거래 통계 (청산된 포지션 기준)
        closed_positions = session.exec(
            select(FuturesPosition).where(
                FuturesPosition.account_id == account.id,
                FuturesPosition.status.in_(
                    [FuturesPositionStatus.CLOSED, FuturesPositionStatus.LIQUIDATED]
                ),
            )
        ).all()

        total_trades = len(closed_positions)
        win_trades = len([p for p in closed_positions if p.realized_pnl > 0])
        win_rate = (win_trades / total_trades * 100) if total_trades > 0 else 0

        avg_roe = (
            sum(float(p.roe_percent) for p in closed_positions) / total_trades
            if total_trades > 0
            else 0
        )

        return FuturesPortfolioSummary(
            # 계정
            total_balance=float(account.total_balance),
            available_balance=float(account.available_balance),
            margin_used=float(account.margin_used),
            unrealized_pnl=float(account.unrealized_pnl),
            total_profit=float(account.total_profit),
            margin_ratio=float(account.margin_ratio),
            # 포지션
            open_positions_count=len(open_positions),
            pending_positions_count=len(pending_positions),
            total_position_value=total_position_value,
            # 통계
            win_rate=round(win_rate, 2),
            total_trades=total_trades,
            avg_roe=round(avg_roe, 2),
        )

    except Exception as e:
        logger.error(f"❌ 포트폴리오 요약 조회 실패: {e}")
        raise


# =====================================================
# 2. 포지션 목록 (상태별)
# =====================================================


@router.get("/fills/{position_id}", response_model=list[FillDetail])
async def get_position_fills(
    position_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """특정 포지션의 체결 내역 조회"""

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
        return [
            FillDetail(
                price=float(position.entry_price),
                quantity=float(position.quantity),
                timestamp=position.opened_at.isoformat(),
            )
        ]

    # 분할 체결 반환
    return [
        FillDetail(
            price=float(fill.price),
            quantity=float(fill.quantity),
            timestamp=fill.timestamp.isoformat(),
        )
        for fill in fills
    ]


# =====================================================
# 3. 체결 내역 (분할 체결 포함)
# =====================================================


# @router.get("/fills/{position_id}", response_model=list[FillDetail])
# async def get_position_fills(
#     position_id: str,
#     current_user: User = Depends(get_current_user),
#     session: Session = Depends(get_session),
# ):
#     """
#     특정 포지션의 체결 내역 조회

#     - 분할 체결된 모든 내역 표시
#     - 가격, 수량, 시간 포함
#     """
#     try:
#         # 포지션 확인
#         position = session.get(FuturesPosition, position_id)
#         if not position:
#             return []

#         # 권한 확인
#         account = session.get(FuturesAccount, position.account_id)
#         if account.user_id != current_user.id:
#             return []

#         # 거래 내역 조회
#         transactions = session.exec(
#             select(FuturesTransaction)
#             .where(FuturesTransaction.position_id == position_id)
#             .order_by(FuturesTransaction.timestamp.asc())
#         ).all()

#         # 체결 내역 파싱
#         # TODO: 실제로는 포지션 개설 시 분할 체결 정보를 별도 테이블에 저장해야 함
#         fills = []
#         for tx in transactions:
#             if tx.action in ["OPEN", "LIMIT_FILLED"]:
#                 fills.append(
#                     FillDetail(
#                         price=float(tx.price),
#                         quantity=float(tx.quantity),
#                         timestamp=tx.timestamp.isoformat(),
#                     )
#                 )

#         return fills

#     except Exception as e:
#         logger.error(f"❌ 체결 내역 조회 실패: {e}")
#         raise


# =====================================================
# 4. 거래 내역 (전체)
# =====================================================


@router.get("/transactions", response_model=list[TransactionDetail])
async def get_transactions(
    symbol: str | None = Query(None, description="심볼 필터 (BTCUSDT 등)"),
    action: str | None = Query(None, description="액션 필터 (OPEN, CLOSE, LIQUIDATION)"),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    거래 내역 조회

    - 포지션 개설/청산 내역
    - 분할 체결 정보 포함
    - 심볼, 액션으로 필터링 가능
    """
    try:
        # 거래 내역 조회
        query = select(FuturesTransaction).where(FuturesTransaction.user_id == current_user.id)

        if symbol:
            query = query.where(FuturesTransaction.symbol == symbol)

        if action:
            query = query.where(FuturesTransaction.action == action)

        transactions = session.exec(
            query.order_by(FuturesTransaction.timestamp.desc()).limit(limit)
        ).all()

        # 각 거래의 분할 체결 정보 조회
        result = []
        for tx in transactions:
            # 같은 포지션의 모든 체결 조회
            if tx.action in ["OPEN", "LIMIT_FILLED"]:
                fills = session.exec(
                    select(FuturesTransaction)
                    .where(
                        FuturesTransaction.position_id == tx.position_id,
                        FuturesTransaction.action.in_(["OPEN", "LIMIT_FILLED"]),
                    )
                    .order_by(FuturesTransaction.timestamp.asc())
                ).all()

                fill_details = [
                    FillDetail(
                        price=float(f.price),
                        quantity=float(f.quantity),
                        timestamp=f.timestamp.isoformat(),
                    )
                    for f in fills
                ]
            else:
                fill_details = None

            result.append(
                TransactionDetail(
                    id=tx.id,
                    position_id=tx.position_id,
                    symbol=tx.symbol,
                    side=tx.side.value,
                    action=tx.action,
                    quantity=float(tx.quantity),
                    price=float(tx.price),
                    leverage=tx.leverage,
                    pnl=float(tx.pnl),
                    fee=float(tx.fee),
                    timestamp=tx.timestamp.isoformat(),
                    fill_count=len(fill_details) if fill_details else 1,
                    fills=fill_details,
                )
            )

        return result

    except Exception as e:
        logger.error(f"❌ 거래 내역 조회 실패: {e}")
        raise


# =====================================================
# 5. 거래 통계
# =====================================================


@router.get("/stats")
async def get_trading_stats(
    period: str = Query("all", description="all, 7d, 30d"),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    거래 통계

    - 총 거래 횟수
    - 승률
    - 평균 ROE
    - 최대 수익/손실
    """
    try:
        # 계정 조회
        account = session.exec(
            select(FuturesAccount).where(FuturesAccount.user_id == current_user.id)
        ).first()

        if not account:
            return {
                "total_trades": 0,
                "win_trades": 0,
                "lose_trades": 0,
                "win_rate": 0,
                "total_pnl": 0,
                "avg_roe": 0,
                "max_profit": 0,
                "max_loss": 0,
            }

        # 기간 필터
        query = select(FuturesPosition).where(
            FuturesPosition.account_id == account.id,
            FuturesPosition.status.in_(
                [FuturesPositionStatus.CLOSED, FuturesPositionStatus.LIQUIDATED]
            ),
        )

        if period == "7d":
            start_date = datetime.utcnow() - timedelta(days=7)
            query = query.where(FuturesPosition.closed_at >= start_date)
        elif period == "30d":
            start_date = datetime.utcnow() - timedelta(days=30)
            query = query.where(FuturesPosition.closed_at >= start_date)

        closed_positions = session.exec(query).all()

        if not closed_positions:
            return {
                "total_trades": 0,
                "win_trades": 0,
                "lose_trades": 0,
                "win_rate": 0,
                "total_pnl": 0,
                "avg_roe": 0,
                "max_profit": 0,
                "max_loss": 0,
            }

        # 통계 계산
        total_trades = len(closed_positions)
        win_trades = len([p for p in closed_positions if p.realized_pnl > 0])
        lose_trades = total_trades - win_trades
        win_rate = (win_trades / total_trades * 100) if total_trades > 0 else 0

        total_pnl = sum(float(p.realized_pnl) for p in closed_positions)
        avg_roe = sum(float(p.roe_percent) for p in closed_positions) / total_trades

        max_profit = max((float(p.realized_pnl) for p in closed_positions), default=0)
        max_loss = min((float(p.realized_pnl) for p in closed_positions), default=0)

        return {
            "period": period,
            "total_trades": total_trades,
            "win_trades": win_trades,
            "lose_trades": lose_trades,
            "win_rate": round(win_rate, 2),
            "total_pnl": round(total_pnl, 2),
            "avg_roe": round(avg_roe, 2),
            "max_profit": round(max_profit, 2),
            "max_loss": round(max_loss, 2),
        }

    except Exception as e:
        logger.error(f"❌ 거래 통계 조회 실패: {e}")
        raise
