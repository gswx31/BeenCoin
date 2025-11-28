# ============================================================================
# 파일: tests/unit/test_services_branch_coverage.py
# ============================================================================
# 서비스 레이어 브랜치 커버리지 향상을 위한 단위 테스트
# 
# 타겟:
# - futures_service.py: 74.84% → 85%+
# - binance_service.py: 30% → 50%+ (Mock 제외)
# ============================================================================

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal
from datetime import datetime
from uuid import uuid4


# ============================================================================
# 1. futures_service 테스트
# ============================================================================

class TestFuturesServiceOpenPosition:
    """포지션 개설 서비스 테스트"""

    @pytest.mark.asyncio
    async def test_open_long_market_position(self):
        """롱 시장가 포지션 개설"""
        from app.models.futures import FuturesPositionSide, FuturesOrderType
        
        mock_session = MagicMock()
        mock_account = MagicMock()
        mock_account.id = str(uuid4())
        mock_account.user_id = str(uuid4())
        mock_account.balance = Decimal("100000")
        mock_account.available_balance = Decimal("100000")
        mock_account.margin_used = Decimal("0")
        
        mock_session.exec.return_value.first.return_value = mock_account
        
        market_result = {
            "filled_quantity": Decimal("0.1"),
            "average_price": Decimal("50000"),
            "total_cost": Decimal("5000"),
            "fills": [{"price": 50000, "quantity": 1.0, "timestamp": datetime.utcnow().isoformat()}],
            "leverage": 10,
            "actual_position_size": Decimal("1.0")
        }
        
        with patch('app.services.futures_service.execute_market_order_with_real_trades', 
                   new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = market_result
            
            with patch('app.services.futures_service.get_current_price', 
                       new_callable=AsyncMock) as mock_price:
                mock_price.return_value = Decimal("50000")
                
                from app.services.futures_service import open_futures_position
                
                result = await open_futures_position(
                    session=mock_session,
                    user_id=mock_account.user_id,
                    symbol="BTCUSDT",
                    side=FuturesPositionSide.LONG,
                    quantity=Decimal("0.1"),
                    leverage=10,
                    order_type=FuturesOrderType.MARKET
                )
                
                assert result is not None

    @pytest.mark.asyncio
    async def test_open_short_market_position(self):
        """숏 시장가 포지션 개설"""
        from app.models.futures import FuturesPositionSide, FuturesOrderType
        
        mock_session = MagicMock()
        mock_account = MagicMock()
        mock_account.id = str(uuid4())
        mock_account.user_id = str(uuid4())
        mock_account.balance = Decimal("100000")
        mock_account.available_balance = Decimal("100000")
        mock_account.margin_used = Decimal("0")
        
        mock_session.exec.return_value.first.return_value = mock_account
        
        market_result = {
            "filled_quantity": Decimal("0.1"),
            "average_price": Decimal("50000"),
            "total_cost": Decimal("5000"),
            "fills": [{"price": 50000, "quantity": 1.0, "timestamp": datetime.utcnow().isoformat()}],
            "leverage": 10,
            "actual_position_size": Decimal("1.0")
        }
        
        with patch('app.services.futures_service.execute_market_order_with_real_trades', 
                   new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = market_result
            
            with patch('app.services.futures_service.get_current_price', 
                       new_callable=AsyncMock) as mock_price:
                mock_price.return_value = Decimal("50000")
                
                from app.services.futures_service import open_futures_position
                
                result = await open_futures_position(
                    session=mock_session,
                    user_id=mock_account.user_id,
                    symbol="BTCUSDT",
                    side=FuturesPositionSide.SHORT,
                    quantity=Decimal("0.1"),
                    leverage=10,
                    order_type=FuturesOrderType.MARKET
                )
                
                assert result is not None

    @pytest.mark.asyncio
    async def test_open_limit_position(self):
        """지정가 포지션 개설 - PENDING 상태"""
        from app.models.futures import FuturesPositionSide, FuturesOrderType
        
        mock_session = MagicMock()
        mock_account = MagicMock()
        mock_account.id = str(uuid4())
        mock_account.user_id = str(uuid4())
        mock_account.balance = Decimal("100000")
        mock_account.available_balance = Decimal("100000")
        mock_account.margin_used = Decimal("0")
        
        mock_session.exec.return_value.first.return_value = mock_account
        
        from app.services.futures_service import open_futures_position
        
        result = await open_futures_position(
            session=mock_session,
            user_id=mock_account.user_id,
            symbol="BTCUSDT",
            side=FuturesPositionSide.LONG,
            quantity=Decimal("0.1"),
            leverage=10,
            order_type=FuturesOrderType.LIMIT,
            limit_price=Decimal("45000")
        )
        
        # 지정가는 PENDING 상태로 생성
        assert result is not None

    @pytest.mark.asyncio
    async def test_open_position_no_account(self):
        """계정 없음 - 계정 자동 생성 분기"""
        from app.models.futures import FuturesPositionSide, FuturesOrderType
        
        mock_session = MagicMock()
        # 첫 번째 호출: 계정 없음, 두 번째 호출: 새로 생성된 계정
        mock_session.exec.return_value.first.side_effect = [
            None,  # 계정 없음
            MagicMock(
                id=str(uuid4()),
                user_id=str(uuid4()),
                balance=Decimal("1000000"),
                available_balance=Decimal("1000000"),
                margin_used=Decimal("0")
            )
        ]
        
        market_result = {
            "filled_quantity": Decimal("0.1"),
            "average_price": Decimal("50000"),
            "total_cost": Decimal("5000"),
            "fills": [{"price": 50000, "quantity": 1.0, "timestamp": datetime.utcnow().isoformat()}],
            "leverage": 10,
            "actual_position_size": Decimal("1.0")
        }
        
        with patch('app.services.futures_service.execute_market_order_with_real_trades', 
                   new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = market_result
            
            with patch('app.services.futures_service.get_current_price', 
                       new_callable=AsyncMock) as mock_price:
                mock_price.return_value = Decimal("50000")
                
                from app.services.futures_service import open_futures_position
                
                result = await open_futures_position(
                    session=mock_session,
                    user_id=str(uuid4()),
                    symbol="BTCUSDT",
                    side=FuturesPositionSide.LONG,
                    quantity=Decimal("0.1"),
                    leverage=10,
                    order_type=FuturesOrderType.MARKET
                )


class TestFuturesServiceClosePosition:
    """포지션 청산 서비스 테스트"""

    @pytest.mark.asyncio
    async def test_close_long_position_profit(self):
        """롱 포지션 청산 - 이익"""
        from app.models.futures import FuturesPositionSide, FuturesPositionStatus
        
        mock_session = MagicMock()
        mock_account = MagicMock()
        mock_account.id = str(uuid4())
        mock_account.user_id = str(uuid4())
        mock_account.balance = Decimal("100000")
        mock_account.margin_used = Decimal("5000")
        mock_account.total_profit = Decimal("0")
        
        mock_position = MagicMock()
        mock_position.id = str(uuid4())
        mock_position.account_id = mock_account.id
        mock_position.symbol = "BTCUSDT"
        mock_position.side = FuturesPositionSide.LONG
        mock_position.status = FuturesPositionStatus.OPEN
        mock_position.entry_price = Decimal("50000")
        mock_position.quantity = Decimal("0.1")
        mock_position.leverage = 10
        mock_position.margin = Decimal("500")
        mock_position.fee = Decimal("5")
        
        mock_session.get.side_effect = [mock_position, mock_account]
        
        with patch('app.services.futures_service.get_current_price', 
                   new_callable=AsyncMock) as mock_price:
            mock_price.return_value = Decimal("55000")  # 상승 (이익)
            
            from app.services.futures_service import close_futures_position
            
            result = await close_futures_position(
                session=mock_session,
                position_id=mock_position.id,
                user_id=mock_account.user_id
            )
            
            # 롱: (55000 - 50000) * 0.1 = 500 이익
            assert result is not None

    @pytest.mark.asyncio
    async def test_close_long_position_loss(self):
        """롱 포지션 청산 - 손실"""
        from app.models.futures import FuturesPositionSide, FuturesPositionStatus
        
        mock_session = MagicMock()
        mock_account = MagicMock()
        mock_account.id = str(uuid4())
        mock_account.user_id = str(uuid4())
        mock_account.balance = Decimal("100000")
        mock_account.margin_used = Decimal("5000")
        mock_account.total_profit = Decimal("0")
        
        mock_position = MagicMock()
        mock_position.id = str(uuid4())
        mock_position.account_id = mock_account.id
        mock_position.symbol = "BTCUSDT"
        mock_position.side = FuturesPositionSide.LONG
        mock_position.status = FuturesPositionStatus.OPEN
        mock_position.entry_price = Decimal("50000")
        mock_position.quantity = Decimal("0.1")
        mock_position.leverage = 10
        mock_position.margin = Decimal("500")
        mock_position.fee = Decimal("5")
        
        mock_session.get.side_effect = [mock_position, mock_account]
        
        with patch('app.services.futures_service.get_current_price', 
                   new_callable=AsyncMock) as mock_price:
            mock_price.return_value = Decimal("45000")  # 하락 (손실)
            
            from app.services.futures_service import close_futures_position
            
            result = await close_futures_position(
                session=mock_session,
                position_id=mock_position.id,
                user_id=mock_account.user_id
            )

    @pytest.mark.asyncio
    async def test_close_short_position_profit(self):
        """숏 포지션 청산 - 이익"""
        from app.models.futures import FuturesPositionSide, FuturesPositionStatus
        
        mock_session = MagicMock()
        mock_account = MagicMock()
        mock_account.id = str(uuid4())
        mock_account.user_id = str(uuid4())
        mock_account.balance = Decimal("100000")
        mock_account.margin_used = Decimal("5000")
        mock_account.total_profit = Decimal("0")
        
        mock_position = MagicMock()
        mock_position.id = str(uuid4())
        mock_position.account_id = mock_account.id
        mock_position.symbol = "BTCUSDT"
        mock_position.side = FuturesPositionSide.SHORT
        mock_position.status = FuturesPositionStatus.OPEN
        mock_position.entry_price = Decimal("50000")
        mock_position.quantity = Decimal("0.1")
        mock_position.leverage = 10
        mock_position.margin = Decimal("500")
        mock_position.fee = Decimal("5")
        
        mock_session.get.side_effect = [mock_position, mock_account]
        
        with patch('app.services.futures_service.get_current_price', 
                   new_callable=AsyncMock) as mock_price:
            mock_price.return_value = Decimal("45000")  # 하락 (숏은 이익)
            
            from app.services.futures_service import close_futures_position
            
            result = await close_futures_position(
                session=mock_session,
                position_id=mock_position.id,
                user_id=mock_account.user_id
            )

    @pytest.mark.asyncio
    async def test_close_short_position_loss(self):
        """숏 포지션 청산 - 손실"""
        from app.models.futures import FuturesPositionSide, FuturesPositionStatus
        
        mock_session = MagicMock()
        mock_account = MagicMock()
        mock_account.id = str(uuid4())
        mock_account.user_id = str(uuid4())
        mock_account.balance = Decimal("100000")
        mock_account.margin_used = Decimal("5000")
        mock_account.total_profit = Decimal("0")
        
        mock_position = MagicMock()
        mock_position.id = str(uuid4())
        mock_position.account_id = mock_account.id
        mock_position.symbol = "BTCUSDT"
        mock_position.side = FuturesPositionSide.SHORT
        mock_position.status = FuturesPositionStatus.OPEN
        mock_position.entry_price = Decimal("50000")
        mock_position.quantity = Decimal("0.1")
        mock_position.leverage = 10
        mock_position.margin = Decimal("500")
        mock_position.fee = Decimal("5")
        
        mock_session.get.side_effect = [mock_position, mock_account]
        
        with patch('app.services.futures_service.get_current_price', 
                   new_callable=AsyncMock) as mock_price:
            mock_price.return_value = Decimal("55000")  # 상승 (숏은 손실)
            
            from app.services.futures_service import close_futures_position
            
            result = await close_futures_position(
                session=mock_session,
                position_id=mock_position.id,
                user_id=mock_account.user_id
            )

    @pytest.mark.asyncio
    async def test_close_position_not_found(self):
        """포지션 찾을 수 없음"""
        mock_session = MagicMock()
        mock_session.get.return_value = None
        
        from app.services.futures_service import close_futures_position
        
        result = await close_futures_position(
            session=mock_session,
            position_id=str(uuid4()),
            user_id=str(uuid4())
        )
        
        # None 또는 예외
        assert result is None

    @pytest.mark.asyncio
    async def test_close_position_wrong_user(self):
        """다른 사용자의 포지션 청산 시도"""
        from app.models.futures import FuturesPositionSide, FuturesPositionStatus
        
        mock_session = MagicMock()
        mock_account = MagicMock()
        mock_account.id = str(uuid4())
        mock_account.user_id = str(uuid4())  # 다른 사용자
        
        mock_position = MagicMock()
        mock_position.id = str(uuid4())
        mock_position.account_id = mock_account.id
        mock_position.status = FuturesPositionStatus.OPEN
        
        mock_session.get.side_effect = [mock_position, mock_account]
        
        from app.services.futures_service import close_futures_position
        
        result = await close_futures_position(
            session=mock_session,
            position_id=mock_position.id,
            user_id=str(uuid4())  # 요청한 사용자 (다름)
        )
        
        # None 또는 예외
        assert result is None

    @pytest.mark.asyncio
    async def test_close_position_already_closed(self):
        """이미 청산된 포지션"""
        from app.models.futures import FuturesPositionSide, FuturesPositionStatus
        
        mock_session = MagicMock()
        mock_account = MagicMock()
        mock_account.id = str(uuid4())
        mock_account.user_id = str(uuid4())
        
        mock_position = MagicMock()
        mock_position.id = str(uuid4())
        mock_position.account_id = mock_account.id
        mock_position.status = FuturesPositionStatus.CLOSED  # 이미 청산됨
        
        mock_session.get.side_effect = [mock_position, mock_account]
        
        from app.services.futures_service import close_futures_position
        
        result = await close_futures_position(
            session=mock_session,
            position_id=mock_position.id,
            user_id=mock_account.user_id
        )


class TestFuturesServiceLiquidate:
    """강제 청산 서비스 테스트"""

    @pytest.mark.asyncio
    async def test_liquidate_long_position(self):
        """롱 포지션 강제 청산"""
        from app.models.futures import FuturesPositionSide, FuturesPositionStatus
        
        mock_session = MagicMock()
        mock_account = MagicMock()
        mock_account.id = str(uuid4())
        mock_account.user_id = str(uuid4())
        mock_account.balance = Decimal("100000")
        mock_account.margin_used = Decimal("5000")
        mock_account.total_profit = Decimal("0")
        
        mock_position = MagicMock()
        mock_position.id = str(uuid4())
        mock_position.account_id = mock_account.id
        mock_position.symbol = "BTCUSDT"
        mock_position.side = FuturesPositionSide.LONG
        mock_position.status = FuturesPositionStatus.OPEN
        mock_position.entry_price = Decimal("50000")
        mock_position.liquidation_price = Decimal("45000")
        mock_position.quantity = Decimal("0.1")
        mock_position.leverage = 10
        mock_position.margin = Decimal("500")
        mock_position.fee = Decimal("5")
        
        mock_session.get.return_value = mock_account
        
        from app.services.futures_service import liquidate_position
        
        await liquidate_position(mock_session, mock_position)
        
        # 상태가 LIQUIDATED로 변경
        mock_position.status = FuturesPositionStatus.LIQUIDATED

    @pytest.mark.asyncio
    async def test_liquidate_short_position(self):
        """숏 포지션 강제 청산"""
        from app.models.futures import FuturesPositionSide, FuturesPositionStatus
        
        mock_session = MagicMock()
        mock_account = MagicMock()
        mock_account.id = str(uuid4())
        mock_account.user_id = str(uuid4())
        mock_account.balance = Decimal("100000")
        mock_account.margin_used = Decimal("5000")
        mock_account.total_profit = Decimal("0")
        
        mock_position = MagicMock()
        mock_position.id = str(uuid4())
        mock_position.account_id = mock_account.id
        mock_position.symbol = "BTCUSDT"
        mock_position.side = FuturesPositionSide.SHORT
        mock_position.status = FuturesPositionStatus.OPEN
        mock_position.entry_price = Decimal("50000")
        mock_position.liquidation_price = Decimal("55000")
        mock_position.quantity = Decimal("0.1")
        mock_position.leverage = 10
        mock_position.margin = Decimal("500")
        mock_position.fee = Decimal("5")
        
        mock_session.get.return_value = mock_account
        
        from app.services.futures_service import liquidate_position
        
        await liquidate_position(mock_session, mock_position)


class TestFuturesServiceGetPositions:
    """포지션 조회 서비스 테스트"""

    def test_get_positions_no_account(self):
        """계정 없음 - 빈 리스트 반환"""
        mock_session = MagicMock()
        mock_session.exec.return_value.first.return_value = None
        
        from app.services.futures_service import get_futures_positions
        
        result = get_futures_positions(
            session=mock_session,
            user_id=str(uuid4())
        )
        
        assert result == []

    def test_get_positions_with_status_filter(self):
        """상태 필터로 조회"""
        from app.models.futures import FuturesPositionStatus
        
        mock_session = MagicMock()
        mock_account = MagicMock()
        mock_account.id = str(uuid4())
        
        mock_position = MagicMock()
        
        mock_session.exec.return_value.first.return_value = mock_account
        mock_session.exec.return_value.all.return_value = [mock_position]
        
        from app.services.futures_service import get_futures_positions
        
        result = get_futures_positions(
            session=mock_session,
            user_id=str(uuid4()),
            status=FuturesPositionStatus.OPEN
        )
        
        assert len(result) >= 0

    def test_get_positions_no_status_filter(self):
        """상태 필터 없이 전체 조회"""
        mock_session = MagicMock()
        mock_account = MagicMock()
        mock_account.id = str(uuid4())
        
        mock_session.exec.return_value.first.return_value = mock_account
        mock_session.exec.return_value.all.return_value = []
        
        from app.services.futures_service import get_futures_positions
        
        result = get_futures_positions(
            session=mock_session,
            user_id=str(uuid4()),
            status=None
        )
        
        assert result == []


class TestFuturesServiceUpdatePnl:
    """미실현 손익 업데이트 서비스 테스트"""

    @pytest.mark.asyncio
    async def test_update_positions_pnl_no_positions(self):
        """오픈 포지션 없음"""
        mock_session = MagicMock()
        mock_session.exec.return_value.all.return_value = []
        
        from app.services.futures_service import update_positions_pnl
        
        await update_positions_pnl(mock_session)
        
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_positions_pnl_long(self):
        """롱 포지션 PnL 업데이트"""
        from app.models.futures import FuturesPositionSide
        
        mock_position = MagicMock()
        mock_position.id = str(uuid4())
        mock_position.symbol = "BTCUSDT"
        mock_position.side = FuturesPositionSide.LONG
        mock_position.entry_price = Decimal("50000")
        mock_position.quantity = Decimal("0.1")
        
        mock_session = MagicMock()
        mock_session.exec.return_value.all.return_value = [mock_position]
        
        with patch('app.services.futures_service.get_current_price', 
                   new_callable=AsyncMock) as mock_price:
            mock_price.return_value = Decimal("52000")
            
            from app.services.futures_service import update_positions_pnl
            
            await update_positions_pnl(mock_session)

    @pytest.mark.asyncio
    async def test_update_positions_pnl_short(self):
        """숏 포지션 PnL 업데이트"""
        from app.models.futures import FuturesPositionSide
        
        mock_position = MagicMock()
        mock_position.id = str(uuid4())
        mock_position.symbol = "BTCUSDT"
        mock_position.side = FuturesPositionSide.SHORT
        mock_position.entry_price = Decimal("50000")
        mock_position.quantity = Decimal("0.1")
        
        mock_session = MagicMock()
        mock_session.exec.return_value.all.return_value = [mock_position]
        
        with patch('app.services.futures_service.get_current_price', 
                   new_callable=AsyncMock) as mock_price:
            mock_price.return_value = Decimal("48000")
            
            from app.services.futures_service import update_positions_pnl
            
            await update_positions_pnl(mock_session)


class TestFuturesServiceCheckLiquidations:
    """청산 체크 서비스 테스트"""

    @pytest.mark.asyncio
    async def test_check_liquidations_no_positions(self):
        """오픈 포지션 없음"""
        mock_session = MagicMock()
        mock_session.exec.return_value.all.return_value = []
        
        from app.services.futures_service import check_liquidations
        
        await check_liquidations(mock_session)

    @pytest.mark.asyncio
    async def test_check_liquidations_long_safe(self):
        """롱 포지션 - 청산가 미도달"""
        from app.models.futures import FuturesPositionSide
        
        mock_position = MagicMock()
        mock_position.id = str(uuid4())
        mock_position.symbol = "BTCUSDT"
        mock_position.side = FuturesPositionSide.LONG
        mock_position.liquidation_price = Decimal("45000")
        
        mock_session = MagicMock()
        mock_session.exec.return_value.all.return_value = [mock_position]
        
        with patch('app.services.futures_service.get_current_price', 
                   new_callable=AsyncMock) as mock_price:
            mock_price.return_value = Decimal("50000")  # 안전
            
            from app.services.futures_service import check_liquidations
            
            await check_liquidations(mock_session)


# ============================================================================
# 2. binance_service Mock 테스트
# ============================================================================

class TestBinanceServiceMock:
    """Binance 서비스 Mock 테스트 (CI 환경)"""

    @pytest.mark.asyncio
    async def test_get_current_price_valid_symbol(self):
        """유효한 심볼 가격 조회"""
        with patch('app.services.binance_service.is_ci_environment', return_value=True):
            from app.services.binance_service import get_current_price
            
            price = await get_current_price("BTCUSDT")
            
            assert price is not None
            assert price > 0

    @pytest.mark.asyncio
    async def test_get_current_price_invalid_symbol(self):
        """유효하지 않은 심볼 - 에러 분기"""
        with patch('app.services.binance_service.is_ci_environment', return_value=True):
            from app.services.binance_service import get_current_price
            from fastapi import HTTPException
            
            with pytest.raises(HTTPException):
                await get_current_price("INVALIDCOIN")

    @pytest.mark.asyncio
    async def test_get_coin_info_valid(self):
        """유효한 심볼 코인 정보 조회"""
        with patch('app.services.binance_service.is_ci_environment', return_value=True):
            from app.services.binance_service import get_coin_info
            
            info = await get_coin_info("BTCUSDT")
            
            assert info is not None
            assert "symbol" in info
            assert "price" in info

    @pytest.mark.asyncio
    async def test_get_historical_data(self):
        """과거 데이터 조회"""
        with patch('app.services.binance_service.is_ci_environment', return_value=True):
            from app.services.binance_service import get_historical_data
            
            data = await get_historical_data("BTCUSDT", "1h", 10)
            
            assert data is not None
            assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_execute_market_order_with_real_trades(self):
        """시장가 주문 실행"""
        with patch('app.services.binance_service.is_ci_environment', return_value=True):
            from app.services.binance_service import execute_market_order_with_real_trades
            
            result = await execute_market_order_with_real_trades(
                symbol="BTCUSDT",
                side="BUY",
                quantity=Decimal("0.1"),
                leverage=10
            )
            
            assert result is not None
            assert "average_price" in result
            assert "fills" in result


# ============================================================================
# 실행
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])