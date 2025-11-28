# ============================================================================
# 파일: tests/unit/test_scheduler_branch_coverage.py
# ============================================================================
# Scheduler 브랜치 커버리지 향상을 위한 단위 테스트
# 
# 타겟: scheduler.py 22.5% → 60%+
# ============================================================================

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from decimal import Decimal
from datetime import datetime, timedelta
from uuid import uuid4


# ============================================================================
# 1. check_pending_futures_limit_orders 테스트
# ============================================================================

class TestCheckPendingFuturesLimitOrders:
    """지정가 주문 체결 확인 테스트"""

    @pytest.mark.asyncio
    async def test_no_pending_positions(self):
        """대기 중인 포지션 없음 - 조기 반환 분기"""
        mock_session = MagicMock()
        mock_session.exec.return_value.all.return_value = []
        
        from app.tasks.scheduler import check_pending_futures_limit_orders
        
        await check_pending_futures_limit_orders(mock_session)
        
        # exec 한 번 호출되고 종료
        mock_session.exec.assert_called_once()
        mock_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_pending_position_no_execution(self):
        """대기 중 포지션 있지만 체결 없음 분기"""
        from app.models.futures import FuturesPositionSide, FuturesPositionStatus
        
        mock_position = MagicMock()
        mock_position.id = str(uuid4())
        mock_position.symbol = "BTCUSDT"
        mock_position.side = FuturesPositionSide.LONG
        mock_position.entry_price = Decimal("50000")
        mock_position.quantity = Decimal("0.1")
        mock_position.leverage = 10
        mock_position.status = FuturesPositionStatus.PENDING
        
        # filled_quantity 속성 없음
        del mock_position.filled_quantity
        
        mock_session = MagicMock()
        mock_session.exec.return_value.all.return_value = [mock_position]
        
        with patch('app.tasks.scheduler.check_limit_order_execution', new_callable=AsyncMock) as mock_check:
            mock_check.return_value = None  # 체결 없음
            
            from app.tasks.scheduler import check_pending_futures_limit_orders
            
            await check_pending_futures_limit_orders(mock_session)
            
            mock_check.assert_called_once()
            # 체결 없으므로 commit 호출
            mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_pending_position_partial_fill(self):
        """대기 중 포지션 부분 체결 분기"""
        from app.models.futures import FuturesPositionSide, FuturesPositionStatus
        
        mock_position = MagicMock()
        mock_position.id = str(uuid4())
        mock_position.symbol = "BTCUSDT"
        mock_position.side = FuturesPositionSide.LONG
        mock_position.entry_price = Decimal("50000")
        mock_position.quantity = Decimal("1.0")
        mock_position.leverage = 10
        mock_position.status = FuturesPositionStatus.PENDING
        mock_position.filled_quantity = Decimal("0")
        
        mock_session = MagicMock()
        mock_session.exec.return_value.all.return_value = [mock_position]
        
        # 부분 체결 결과
        partial_fill_result = {
            "filled_quantity": Decimal("0.5"),
            "remaining": Decimal("0.5"),
            "fills": [
                {"price": 49900, "quantity": 5.0, "timestamp": datetime.utcnow().isoformat()}
            ]
        }
        
        with patch('app.tasks.scheduler.check_limit_order_execution', new_callable=AsyncMock) as mock_check:
            mock_check.return_value = partial_fill_result
            
            from app.tasks.scheduler import check_pending_futures_limit_orders
            
            await check_pending_futures_limit_orders(mock_session)
            
            # 부분 체결이므로 상태는 PENDING 유지
            assert mock_position.status == FuturesPositionStatus.PENDING

    @pytest.mark.asyncio
    async def test_pending_position_full_fill_long(self):
        """대기 중 롱 포지션 완전 체결 분기"""
        from app.models.futures import FuturesPositionSide, FuturesPositionStatus, FuturesAccount
        
        mock_account = MagicMock()
        mock_account.user_id = str(uuid4())
        
        mock_position = MagicMock()
        mock_position.id = str(uuid4())
        mock_position.account_id = str(uuid4())
        mock_position.symbol = "BTCUSDT"
        mock_position.side = FuturesPositionSide.LONG
        mock_position.entry_price = Decimal("50000")
        mock_position.quantity = Decimal("1.0")
        mock_position.leverage = 10
        mock_position.status = FuturesPositionStatus.PENDING
        mock_position.fee = Decimal("10")
        mock_position.filled_quantity = Decimal("0")
        
        mock_session = MagicMock()
        mock_session.exec.return_value.all.return_value = [mock_position]
        mock_session.get.return_value = mock_account
        
        # 완전 체결 결과
        full_fill_result = {
            "filled_quantity": Decimal("1.0"),
            "remaining": Decimal("0"),
            "fills": [
                {"price": 49900, "quantity": 5.0, "timestamp": datetime.utcnow().isoformat()},
                {"price": 50000, "quantity": 5.0, "timestamp": datetime.utcnow().isoformat()}
            ]
        }
        
        with patch('app.tasks.scheduler.check_limit_order_execution', new_callable=AsyncMock) as mock_check:
            mock_check.return_value = full_fill_result
            
            from app.tasks.scheduler import check_pending_futures_limit_orders
            
            await check_pending_futures_limit_orders(mock_session)
            
            # 완전 체결이므로 OPEN 상태로 전환
            mock_position.status = FuturesPositionStatus.OPEN

    @pytest.mark.asyncio
    async def test_pending_position_full_fill_short(self):
        """대기 중 숏 포지션 완전 체결 분기"""
        from app.models.futures import FuturesPositionSide, FuturesPositionStatus
        
        mock_account = MagicMock()
        mock_account.user_id = str(uuid4())
        
        mock_position = MagicMock()
        mock_position.id = str(uuid4())
        mock_position.account_id = str(uuid4())
        mock_position.symbol = "BTCUSDT"
        mock_position.side = FuturesPositionSide.SHORT  # 숏
        mock_position.entry_price = Decimal("50000")
        mock_position.quantity = Decimal("1.0")
        mock_position.leverage = 10
        mock_position.status = FuturesPositionStatus.PENDING
        mock_position.fee = Decimal("10")
        
        mock_session = MagicMock()
        mock_session.exec.return_value.all.return_value = [mock_position]
        mock_session.get.return_value = mock_account
        
        full_fill_result = {
            "filled_quantity": Decimal("1.0"),
            "remaining": Decimal("0"),
            "fills": [{"price": 50100, "quantity": 10.0, "timestamp": datetime.utcnow().isoformat()}]
        }
        
        with patch('app.tasks.scheduler.check_limit_order_execution', new_callable=AsyncMock) as mock_check:
            mock_check.return_value = full_fill_result
            
            from app.tasks.scheduler import check_pending_futures_limit_orders
            
            await check_pending_futures_limit_orders(mock_session)

    @pytest.mark.asyncio
    async def test_pending_position_exception_handling(self):
        """포지션 처리 중 예외 - continue 분기"""
        from app.models.futures import FuturesPositionSide, FuturesPositionStatus
        
        mock_position = MagicMock()
        mock_position.id = str(uuid4())
        mock_position.symbol = "BTCUSDT"
        mock_position.side = FuturesPositionSide.LONG
        mock_position.entry_price = Decimal("50000")
        mock_position.quantity = Decimal("1.0")
        mock_position.leverage = 10
        mock_position.status = FuturesPositionStatus.PENDING
        
        mock_session = MagicMock()
        mock_session.exec.return_value.all.return_value = [mock_position]
        
        with patch('app.tasks.scheduler.check_limit_order_execution', new_callable=AsyncMock) as mock_check:
            mock_check.side_effect = Exception("Test exception")
            
            from app.tasks.scheduler import check_pending_futures_limit_orders
            
            # 예외가 발생해도 rollback 후 종료
            await check_pending_futures_limit_orders(mock_session)


# ============================================================================
# 2. check_liquidation 테스트
# ============================================================================

class TestCheckLiquidation:
    """강제 청산 확인 테스트"""

    @pytest.mark.asyncio
    async def test_no_open_positions(self):
        """오픈 포지션 없음 - 조기 반환 분기"""
        mock_session = MagicMock()
        mock_session.exec.return_value.all.return_value = []
        
        from app.tasks.scheduler import check_liquidation
        
        await check_liquidation(mock_session)
        
        mock_session.exec.assert_called_once()

    @pytest.mark.asyncio
    async def test_long_position_safe(self):
        """롱 포지션 - 청산가 미도달 분기"""
        from app.models.futures import FuturesPositionSide
        
        mock_position = MagicMock()
        mock_position.id = str(uuid4())
        mock_position.symbol = "BTCUSDT"
        mock_position.side = FuturesPositionSide.LONG
        mock_position.entry_price = Decimal("50000")
        mock_position.liquidation_price = Decimal("45000")
        mock_position.quantity = Decimal("0.1")
        
        mock_session = MagicMock()
        mock_session.exec.return_value.all.return_value = [mock_position]
        
        with patch('app.tasks.scheduler.get_current_price', new_callable=AsyncMock) as mock_price:
            mock_price.return_value = Decimal("52000")  # 청산가보다 높음
            
            with patch('app.tasks.scheduler.liquidate_position', new_callable=AsyncMock) as mock_liquidate:
                from app.tasks.scheduler import check_liquidation
                
                await check_liquidation(mock_session)
                
                # 청산되지 않아야 함
                mock_liquidate.assert_not_called()

    @pytest.mark.asyncio
    async def test_long_position_liquidated(self):
        """롱 포지션 - 청산가 도달 분기"""
        from app.models.futures import FuturesPositionSide
        
        mock_position = MagicMock()
        mock_position.id = str(uuid4())
        mock_position.symbol = "BTCUSDT"
        mock_position.side = FuturesPositionSide.LONG
        mock_position.entry_price = Decimal("50000")
        mock_position.liquidation_price = Decimal("45000")
        mock_position.quantity = Decimal("0.1")
        
        mock_session = MagicMock()
        mock_session.exec.return_value.all.return_value = [mock_position]
        
        with patch('app.tasks.scheduler.get_current_price', new_callable=AsyncMock) as mock_price:
            mock_price.return_value = Decimal("44000")  # 청산가 이하
            
            with patch('app.tasks.scheduler.liquidate_position', new_callable=AsyncMock) as mock_liquidate:
                from app.tasks.scheduler import check_liquidation
                
                await check_liquidation(mock_session)
                
                # 청산되어야 함
                mock_liquidate.assert_called_once()

    @pytest.mark.asyncio
    async def test_short_position_safe(self):
        """숏 포지션 - 청산가 미도달 분기"""
        from app.models.futures import FuturesPositionSide
        
        mock_position = MagicMock()
        mock_position.id = str(uuid4())
        mock_position.symbol = "BTCUSDT"
        mock_position.side = FuturesPositionSide.SHORT
        mock_position.entry_price = Decimal("50000")
        mock_position.liquidation_price = Decimal("55000")
        mock_position.quantity = Decimal("0.1")
        
        mock_session = MagicMock()
        mock_session.exec.return_value.all.return_value = [mock_position]
        
        with patch('app.tasks.scheduler.get_current_price', new_callable=AsyncMock) as mock_price:
            mock_price.return_value = Decimal("48000")  # 청산가보다 낮음
            
            with patch('app.tasks.scheduler.liquidate_position', new_callable=AsyncMock) as mock_liquidate:
                from app.tasks.scheduler import check_liquidation
                
                await check_liquidation(mock_session)
                
                mock_liquidate.assert_not_called()

    @pytest.mark.asyncio
    async def test_short_position_liquidated(self):
        """숏 포지션 - 청산가 도달 분기"""
        from app.models.futures import FuturesPositionSide
        
        mock_position = MagicMock()
        mock_position.id = str(uuid4())
        mock_position.symbol = "BTCUSDT"
        mock_position.side = FuturesPositionSide.SHORT
        mock_position.entry_price = Decimal("50000")
        mock_position.liquidation_price = Decimal("55000")
        mock_position.quantity = Decimal("0.1")
        
        mock_session = MagicMock()
        mock_session.exec.return_value.all.return_value = [mock_position]
        
        with patch('app.tasks.scheduler.get_current_price', new_callable=AsyncMock) as mock_price:
            mock_price.return_value = Decimal("56000")  # 청산가 이상
            
            with patch('app.tasks.scheduler.liquidate_position', new_callable=AsyncMock) as mock_liquidate:
                from app.tasks.scheduler import check_liquidation
                
                await check_liquidation(mock_session)
                
                mock_liquidate.assert_called_once()

    @pytest.mark.asyncio
    async def test_position_exception_handling(self):
        """포지션 처리 중 예외 - continue 분기"""
        from app.models.futures import FuturesPositionSide
        
        mock_position = MagicMock()
        mock_position.id = str(uuid4())
        mock_position.symbol = "BTCUSDT"
        mock_position.side = FuturesPositionSide.LONG
        mock_position.liquidation_price = Decimal("45000")
        
        mock_session = MagicMock()
        mock_session.exec.return_value.all.return_value = [mock_position]
        
        with patch('app.tasks.scheduler.get_current_price', new_callable=AsyncMock) as mock_price:
            mock_price.side_effect = Exception("Price fetch error")
            
            from app.tasks.scheduler import check_liquidation
            
            # 예외 발생해도 계속 진행
            await check_liquidation(mock_session)


# ============================================================================
# 3. update_unrealized_pnl 테스트
# ============================================================================

class TestUpdateUnrealizedPnl:
    """미실현 손익 업데이트 테스트"""

    @pytest.mark.asyncio
    async def test_no_open_positions(self):
        """오픈 포지션 없음 - 조기 반환 분기"""
        mock_session = MagicMock()
        mock_session.exec.return_value.all.return_value = []
        
        from app.tasks.scheduler import update_unrealized_pnl
        
        await update_unrealized_pnl(mock_session)
        
        mock_session.exec.assert_called_once()
        mock_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_long_position_profit(self):
        """롱 포지션 - 이익 분기"""
        from app.models.futures import FuturesPositionSide
        
        mock_position = MagicMock()
        mock_position.id = str(uuid4())
        mock_position.symbol = "BTCUSDT"
        mock_position.side = FuturesPositionSide.LONG
        mock_position.entry_price = Decimal("50000")
        mock_position.quantity = Decimal("0.1")
        mock_position.unrealized_pnl = Decimal("0")
        mock_position.mark_price = Decimal("50000")
        
        mock_session = MagicMock()
        mock_session.exec.return_value.all.return_value = [mock_position]
        
        with patch('app.tasks.scheduler.get_current_price', new_callable=AsyncMock) as mock_price:
            mock_price.return_value = Decimal("52000")  # 상승
            
            from app.tasks.scheduler import update_unrealized_pnl
            
            await update_unrealized_pnl(mock_session)
            
            # PnL 업데이트 확인
            assert mock_position.mark_price == Decimal("52000")
            # 롱: (52000 - 50000) * 0.1 = 200
            expected_pnl = (Decimal("52000") - Decimal("50000")) * Decimal("0.1")
            assert mock_position.unrealized_pnl == expected_pnl

    @pytest.mark.asyncio
    async def test_long_position_loss(self):
        """롱 포지션 - 손실 분기"""
        from app.models.futures import FuturesPositionSide
        
        mock_position = MagicMock()
        mock_position.id = str(uuid4())
        mock_position.symbol = "BTCUSDT"
        mock_position.side = FuturesPositionSide.LONG
        mock_position.entry_price = Decimal("50000")
        mock_position.quantity = Decimal("0.1")
        mock_position.unrealized_pnl = Decimal("0")
        mock_position.mark_price = Decimal("50000")
        
        mock_session = MagicMock()
        mock_session.exec.return_value.all.return_value = [mock_position]
        
        with patch('app.tasks.scheduler.get_current_price', new_callable=AsyncMock) as mock_price:
            mock_price.return_value = Decimal("48000")  # 하락
            
            from app.tasks.scheduler import update_unrealized_pnl
            
            await update_unrealized_pnl(mock_session)
            
            # 롱: (48000 - 50000) * 0.1 = -200
            expected_pnl = (Decimal("48000") - Decimal("50000")) * Decimal("0.1")
            assert mock_position.unrealized_pnl == expected_pnl

    @pytest.mark.asyncio
    async def test_short_position_profit(self):
        """숏 포지션 - 이익 분기"""
        from app.models.futures import FuturesPositionSide
        
        mock_position = MagicMock()
        mock_position.id = str(uuid4())
        mock_position.symbol = "BTCUSDT"
        mock_position.side = FuturesPositionSide.SHORT
        mock_position.entry_price = Decimal("50000")
        mock_position.quantity = Decimal("0.1")
        mock_position.unrealized_pnl = Decimal("0")
        mock_position.mark_price = Decimal("50000")
        
        mock_session = MagicMock()
        mock_session.exec.return_value.all.return_value = [mock_position]
        
        with patch('app.tasks.scheduler.get_current_price', new_callable=AsyncMock) as mock_price:
            mock_price.return_value = Decimal("48000")  # 하락 (숏은 이익)
            
            from app.tasks.scheduler import update_unrealized_pnl
            
            await update_unrealized_pnl(mock_session)
            
            # 숏: (50000 - 48000) * 0.1 = 200
            expected_pnl = (Decimal("50000") - Decimal("48000")) * Decimal("0.1")
            assert mock_position.unrealized_pnl == expected_pnl

    @pytest.mark.asyncio
    async def test_short_position_loss(self):
        """숏 포지션 - 손실 분기"""
        from app.models.futures import FuturesPositionSide
        
        mock_position = MagicMock()
        mock_position.id = str(uuid4())
        mock_position.symbol = "BTCUSDT"
        mock_position.side = FuturesPositionSide.SHORT
        mock_position.entry_price = Decimal("50000")
        mock_position.quantity = Decimal("0.1")
        mock_position.unrealized_pnl = Decimal("0")
        mock_position.mark_price = Decimal("50000")
        
        mock_session = MagicMock()
        mock_session.exec.return_value.all.return_value = [mock_position]
        
        with patch('app.tasks.scheduler.get_current_price', new_callable=AsyncMock) as mock_price:
            mock_price.return_value = Decimal("52000")  # 상승 (숏은 손실)
            
            from app.tasks.scheduler import update_unrealized_pnl
            
            await update_unrealized_pnl(mock_session)
            
            # 숏: (50000 - 52000) * 0.1 = -200
            expected_pnl = (Decimal("50000") - Decimal("52000")) * Decimal("0.1")
            assert mock_position.unrealized_pnl == expected_pnl

    @pytest.mark.asyncio
    async def test_position_exception_handling(self):
        """포지션 처리 중 예외 - continue 분기"""
        from app.models.futures import FuturesPositionSide
        
        mock_position = MagicMock()
        mock_position.id = str(uuid4())
        mock_position.symbol = "BTCUSDT"
        mock_position.side = FuturesPositionSide.LONG
        
        mock_session = MagicMock()
        mock_session.exec.return_value.all.return_value = [mock_position]
        
        with patch('app.tasks.scheduler.get_current_price', new_callable=AsyncMock) as mock_price:
            mock_price.side_effect = Exception("Price fetch error")
            
            from app.tasks.scheduler import update_unrealized_pnl
            
            await update_unrealized_pnl(mock_session)
            
            # 예외 발생해도 commit 호출
            mock_session.commit.assert_called_once()


# ============================================================================
# 4. update_account_unrealized_pnl 테스트
# ============================================================================

class TestUpdateAccountUnrealizedPnl:
    """계정 미실현 손익 합계 업데이트 테스트"""

    @pytest.mark.asyncio
    async def test_no_accounts(self):
        """계정 없음 - 빈 루프 분기"""
        mock_session = MagicMock()
        mock_session.exec.return_value.all.return_value = []
        
        from app.tasks.scheduler import update_account_unrealized_pnl
        
        await update_account_unrealized_pnl(mock_session)
        
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_account_with_no_positions(self):
        """계정 있지만 포지션 없음 분기"""
        mock_account = MagicMock()
        mock_account.id = str(uuid4())
        mock_account.unrealized_pnl = Decimal("100")  # 기존 값
        
        mock_session = MagicMock()
        
        # 첫 번째 호출: 계정 목록
        # 두 번째 호출: 포지션 목록 (빈 리스트)
        mock_session.exec.return_value.all.side_effect = [
            [mock_account],  # 계정 목록
            []  # 포지션 목록 (없음)
        ]
        
        from app.tasks.scheduler import update_account_unrealized_pnl
        
        await update_account_unrealized_pnl(mock_session)
        
        # 미실현 손익이 0으로 업데이트
        assert mock_account.unrealized_pnl == Decimal("0")

    @pytest.mark.asyncio
    async def test_account_with_positions(self):
        """계정에 포지션 있음 분기"""
        mock_account = MagicMock()
        mock_account.id = str(uuid4())
        mock_account.unrealized_pnl = Decimal("0")
        
        mock_position1 = MagicMock()
        mock_position1.unrealized_pnl = Decimal("100")
        
        mock_position2 = MagicMock()
        mock_position2.unrealized_pnl = Decimal("-50")
        
        mock_session = MagicMock()
        mock_session.exec.return_value.all.side_effect = [
            [mock_account],  # 계정 목록
            [mock_position1, mock_position2]  # 포지션 목록
        ]
        
        from app.tasks.scheduler import update_account_unrealized_pnl
        
        await update_account_unrealized_pnl(mock_session)
        
        # 100 + (-50) = 50
        assert mock_account.unrealized_pnl == Decimal("50")

    @pytest.mark.asyncio
    async def test_multiple_accounts(self):
        """여러 계정 분기"""
        mock_account1 = MagicMock()
        mock_account1.id = str(uuid4())
        mock_account1.unrealized_pnl = Decimal("0")
        
        mock_account2 = MagicMock()
        mock_account2.id = str(uuid4())
        mock_account2.unrealized_pnl = Decimal("0")
        
        mock_position1 = MagicMock()
        mock_position1.unrealized_pnl = Decimal("200")
        
        mock_position2 = MagicMock()
        mock_position2.unrealized_pnl = Decimal("-100")
        
        mock_session = MagicMock()
        mock_session.exec.return_value.all.side_effect = [
            [mock_account1, mock_account2],  # 계정 목록
            [mock_position1],  # account1 포지션
            [mock_position2]   # account2 포지션
        ]
        
        from app.tasks.scheduler import update_account_unrealized_pnl
        
        await update_account_unrealized_pnl(mock_session)

    @pytest.mark.asyncio
    async def test_exception_handling(self):
        """예외 발생 - rollback 분기"""
        mock_session = MagicMock()
        mock_session.exec.side_effect = Exception("DB Error")
        
        from app.tasks.scheduler import update_account_unrealized_pnl
        
        await update_account_unrealized_pnl(mock_session)
        
        mock_session.rollback.assert_called_once()


# ============================================================================
# 5. 백그라운드 작업 시작 함수 테스트
# ============================================================================

class TestBackgroundTaskStarters:
    """백그라운드 작업 시작 함수 테스트"""

    def test_start_futures_background_tasks(self):
        """start_futures_background_tasks 호출 테스트"""
        with patch('asyncio.create_task') as mock_create_task:
            from app.tasks.scheduler import start_futures_background_tasks
            
            start_futures_background_tasks()
            
            mock_create_task.assert_called_once()

    def test_start_all_background_tasks(self):
        """start_all_background_tasks 호출 테스트"""
        with patch('asyncio.create_task') as mock_create_task:
            from app.tasks.scheduler import start_all_background_tasks
            
            start_all_background_tasks()
            
            mock_create_task.assert_called_once()


# ============================================================================
# 실행
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])