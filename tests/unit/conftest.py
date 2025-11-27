# ============================================================================
# 파일: tests/unit/conftest.py
# ============================================================================
# Unit 테스트 전용 설정 - pytest-asyncio 충돌 방지
# ============================================================================


import pytest

# =============================================================================
# pytest-asyncio 설정 오버라이드
# =============================================================================

# 중요: 이 파일이 있으면 루트 conftest.py의 async 설정이
# 이 폴더에 적용되지 않음


def pytest_configure(config):
    """pytest 설정 - unit 테스트용"""
    # unit 테스트 마커 등록
    config.addinivalue_line("markers", "unit: 단위 테스트")


# =============================================================================
# 기본 Fixtures (외부 의존성 없음)
# =============================================================================


@pytest.fixture
def sample_user_data():
    """샘플 사용자 데이터"""
    return {"username": "testuser123", "password": "testpass123"}


@pytest.fixture
def sample_position_data():
    """샘플 포지션 데이터"""
    from decimal import Decimal

    return {
        "symbol": "BTCUSDT",
        "side": "LONG",
        "quantity": Decimal("0.001"),
        "leverage": 10,
        "entry_price": Decimal("50000"),
    }


@pytest.fixture
def sample_trade_data():
    """샘플 거래 데이터"""
    from decimal import Decimal

    return {
        "entry_price": Decimal("50000"),
        "exit_price": Decimal("55000"),
        "quantity": Decimal("0.1"),
        "leverage": 10,
        "fee_rate": Decimal("0.001"),
    }
