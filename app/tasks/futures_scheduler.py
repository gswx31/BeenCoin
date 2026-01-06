# app/tasks/futures_scheduler.py
"""
선물 거래 백그라운드 작업
- 청산 체크
- 미실현 손익 업데이트
"""
import asyncio
import logging

from sqlmodel import Session

from app.core.database import engine
from app.services.futures_service import check_liquidations, update_positions_pnl

logger = logging.getLogger(__name__)

async def run_futures_tasks():
    """
    선물 거래 백그라운드 작업

    5초마다:
    - 청산 체크 (중요!)
    - 미실현 손익 업데이트
    """

    logger.info("🚀 선물 거래 백그라운드 작업 시작")

    while True:
        try:
            with Session(engine) as session:
                # 1. 청산 체크 (중요!)
                logger.debug("⚠️ 청산 체크 중...")
                await check_liquidations(session)

                # 2. 미실현 손익 업데이트
                logger.debug("📊 미실현 손익 업데이트 중...")
                await update_positions_pnl(session)

            # 5초 대기 (선물은 더 빠른 체크 필요)
            await asyncio.sleep(5)

        except Exception as e:
            logger.error(f"❌ 선물 백그라운드 작업 오류: {e}")
            await asyncio.sleep(5)

def start_futures_tasks():
    """선물 백그라운드 작업 시작"""

    asyncio.create_task(run_futures_tasks())
    logger.info("✅ 선물 거래 스케줄러 등록 완료")
