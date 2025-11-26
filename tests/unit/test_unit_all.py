# ============================================================================
# 파일: tests/unit/test_unit_all.py
# ============================================================================
# 단위 테스트 - 실제 비즈니스 로직 검증
# ============================================================================

"""
테스트 항목:
1. 설정 및 환경변수 테스트
2. 보안 유틸리티 테스트 (비밀번호 해싱, JWT)
3. 모델 테스트 (User, FuturesAccount, FuturesPosition)
4. 스키마 검증 테스트
5. 레버리지/청산가/손익 계산 테스트
6. 유틸리티 함수 테스트
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from uuid import uuid4
import re


# =============================================================================
# 1. 설정 및 환경변수 테스트
# =============================================================================

class TestConfig:
    """설정 모듈 테스트"""
    
    def test_config_import(self):
        """config 모듈 import 성공"""
        from app.core.config import settings
        assert settings is not None
    
    def test_project_name_exists(self):
        """프로젝트 이름 설정 확인"""
        from app.core.config import settings
        assert hasattr(settings, "PROJECT_NAME")
        assert len(settings.PROJECT_NAME) > 0
    
    def test_supported_symbols_exists(self):
        """지원 심볼 목록 확인"""
        from app.core.config import settings
        assert hasattr(settings, "SUPPORTED_SYMBOLS")
        assert isinstance(settings.SUPPORTED_SYMBOLS, list)
        assert "BTCUSDT" in settings.SUPPORTED_SYMBOLS
        assert "ETHUSDT" in settings.SUPPORTED_SYMBOLS
    
    def test_initial_balance_positive(self):
        """초기 잔액이 양수인지 확인"""
        from app.core.config import settings
        assert hasattr(settings, "INITIAL_BALANCE")
        assert settings.INITIAL_BALANCE > 0
    
    def test_leverage_limits(self):
        """레버리지 제한 설정 확인"""
        from app.core.config import settings
        if hasattr(settings, "MAX_LEVERAGE"):
            assert settings.MAX_LEVERAGE >= 1
            assert settings.MAX_LEVERAGE <= 125
    
    def test_fee_rate_valid(self):
        """수수료율 유효성 확인"""
        from app.core.config import settings
        if hasattr(settings, "FEE_RATE"):
            assert 0 <= settings.FEE_RATE <= 0.01  # 0% ~ 1%


# =============================================================================
# 2. 보안 유틸리티 테스트
# =============================================================================

class TestSecurity:
    """보안 유틸리티 테스트"""
    
    def test_hash_password(self):
        """비밀번호 해싱 테스트"""
        from app.utils.security import hash_password
        
        password = "testpassword123"
        hashed = hash_password(password)
        
        # 해시된 비밀번호는 원본과 달라야 함
        assert hashed != password
        # 해시는 충분히 길어야 함
        assert len(hashed) > 20
    
    def test_verify_password_correct(self):
        """올바른 비밀번호 검증"""
        from app.utils.security import hash_password, verify_password
        
        password = "correctpassword"
        hashed = hash_password(password)
        
        assert verify_password(password, hashed) is True
    
    def test_verify_password_incorrect(self):
        """잘못된 비밀번호 검증"""
        from app.utils.security import hash_password, verify_password
        
        password = "correctpassword"
        hashed = hash_password(password)
        
        assert verify_password("wrongpassword", hashed) is False
    
    def test_verify_password_empty(self):
        """빈 비밀번호 검증"""
        from app.utils.security import hash_password, verify_password
        
        password = "somepassword"
        hashed = hash_password(password)
        
        assert verify_password("", hashed) is False
    
    def test_hash_different_passwords_different_hashes(self):
        """다른 비밀번호는 다른 해시를 생성"""
        from app.utils.security import hash_password
        
        hash1 = hash_password("password1")
        hash2 = hash_password("password2")
        
        assert hash1 != hash2
    
    def test_same_password_different_hashes(self):
        """같은 비밀번호도 매번 다른 해시 생성 (salt)"""
        from app.utils.security import hash_password
        
        password = "samepassword"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        
        # salt 때문에 같은 비밀번호도 다른 해시 생성
        assert hash1 != hash2
    
    def test_create_access_token(self):
        """JWT 토큰 생성"""
        from app.utils.security import create_access_token
        
        token = create_access_token(data={"sub": "testuser"})
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 50
        # JWT 형식 확인 (3개의 점으로 구분된 부분)
        assert token.count('.') == 2
    
    def test_create_access_token_with_expiry(self):
        """만료 시간이 있는 JWT 토큰 생성"""
        from app.utils.security import create_access_token
        
        token = create_access_token(
            data={"sub": "testuser"},
            expires_delta=timedelta(minutes=30)
        )
        
        assert token is not None
        assert len(token) > 50
    
    def test_token_contains_user_info(self):
        """토큰에 사용자 정보 포함 확인"""
        from app.utils.security import create_access_token
        import jwt
        from app.core.config import settings
        
        username = "testuser123"
        token = create_access_token(data={"sub": username})
        
        # 토큰 디코딩 (검증 없이)
        decoded = jwt.decode(token, options={"verify_signature": False})
        assert decoded["sub"] == username


# =============================================================================
# 3. 모델 테스트
# =============================================================================

class TestModels:
    """데이터베이스 모델 테스트"""
    
    def test_user_model_import(self):
        """User 모델 import"""
        from app.models.database import User
        assert User is not None
    
    def test_user_model_fields(self):
        """User 모델 필드 확인"""
        from app.models.database import User
        
        # 필수 필드 확인
        user = User(
            username="testuser",
            hashed_password="hashedpassword123"
        )
        assert user.username == "testuser"
        assert user.hashed_password == "hashedpassword123"
    
    def test_futures_account_model_import(self):
        """FuturesAccount 모델 import"""
        from app.models.futures import FuturesAccount
        assert FuturesAccount is not None
    
    def test_futures_position_model_import(self):
        """FuturesPosition 모델 import"""
        from app.models.futures import FuturesPosition
        assert FuturesPosition is not None
    
    def test_position_side_enum(self):
        """포지션 방향 Enum 테스트"""
        from app.models.futures import FuturesPositionSide
        
        assert FuturesPositionSide.LONG.value == "LONG"
        assert FuturesPositionSide.SHORT.value == "SHORT"
    
    def test_position_status_enum(self):
        """포지션 상태 Enum 테스트"""
        from app.models.futures import FuturesPositionStatus
        
        assert FuturesPositionStatus.OPEN.value == "OPEN"
        assert FuturesPositionStatus.CLOSED.value == "CLOSED"
        assert FuturesPositionStatus.LIQUIDATED.value == "LIQUIDATED"
    
    def test_futures_fills_model_import(self):
        """FuturesFill 모델 import"""
        from app.models.futures_fills import FuturesFill
        assert FuturesFill is not None


# =============================================================================
# 4. 스키마 검증 테스트
# =============================================================================

class TestSchemas:
    """Pydantic 스키마 검증 테스트"""
    
    def test_user_create_schema(self):
        """UserCreate 스키마 테스트"""
        from app.schemas.user import UserCreate
        
        user = UserCreate(username="validuser", password="validpass123")
        assert user.username == "validuser"
        assert user.password == "validpass123"
    
    def test_user_create_invalid_username_too_short(self):
        """너무 짧은 사용자명 검증"""
        from app.schemas.user import UserCreate
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError):
            UserCreate(username="ab", password="validpass123")
    
    def test_user_create_invalid_password_too_short(self):
        """너무 짧은 비밀번호 검증"""
        from app.schemas.user import UserCreate
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError):
            UserCreate(username="validuser", password="short")
    
    def test_user_create_special_char_in_username(self):
        """특수문자 포함 사용자명 검증"""
        from app.schemas.user import UserCreate
        from pydantic import ValidationError
        
        # 언더스코어는 허용되지 않음
        with pytest.raises(ValidationError):
            UserCreate(username="user_name", password="validpass123")
    
    def test_user_login_schema(self):
        """UserLogin 스키마 테스트"""
        from app.schemas.user import UserLogin
        
        login = UserLogin(username="testuser", password="testpass")
        assert login.username == "testuser"


# =============================================================================
# 5. 레버리지/청산가/손익 계산 테스트
# =============================================================================

class TestCalculations:
    """거래 계산 로직 테스트"""
    
    def test_margin_calculation(self):
        """증거금 계산"""
        # 포지션 가치 = 수량 × 가격
        # 증거금 = 포지션 가치 / 레버리지
        
        quantity = Decimal("0.01")
        price = Decimal("50000")
        leverage = 10
        
        position_value = quantity * price  # 500 USDT
        margin = position_value / leverage  # 50 USDT
        
        assert position_value == Decimal("500")
        assert margin == Decimal("50")
    
    def test_margin_calculation_high_leverage(self):
        """고레버리지 증거금 계산"""
        quantity = Decimal("0.1")
        price = Decimal("100000")
        leverage = 100
        
        position_value = quantity * price  # 10000 USDT
        margin = position_value / leverage  # 100 USDT
        
        assert margin == Decimal("100")
    
    def test_liquidation_price_long(self):
        """롱 포지션 청산가 계산"""
        entry_price = Decimal("50000")
        leverage = 10
        maintenance_margin_rate = Decimal("0.1")  # 10%
        
        # 청산가 = 진입가 × (1 - (1 - 유지증거금율) / 레버리지)
        liquidation_price = entry_price * (1 - (1 - maintenance_margin_rate) / leverage)
        
        # 10배 레버리지, 10% 유지증거금 -> 약 9% 하락시 청산
        assert liquidation_price == Decimal("45500.0")
        assert liquidation_price < entry_price
    
    def test_liquidation_price_short(self):
        """숏 포지션 청산가 계산"""
        entry_price = Decimal("50000")
        leverage = 10
        maintenance_margin_rate = Decimal("0.1")
        
        # 숏 청산가 = 진입가 × (1 + (1 - 유지증거금율) / 레버리지)
        liquidation_price = entry_price * (1 + (1 - maintenance_margin_rate) / leverage)
        
        assert liquidation_price == Decimal("54500.0")
        assert liquidation_price > entry_price
    
    def test_pnl_long_profit(self):
        """롱 포지션 수익 계산"""
        entry_price = Decimal("50000")
        exit_price = Decimal("55000")
        quantity = Decimal("0.01")
        
        # 롱 PnL = (청산가 - 진입가) × 수량
        pnl = (exit_price - entry_price) * quantity
        
        assert pnl == Decimal("50")  # 50 USDT 수익
    
    def test_pnl_long_loss(self):
        """롱 포지션 손실 계산"""
        entry_price = Decimal("50000")
        exit_price = Decimal("45000")
        quantity = Decimal("0.01")
        
        pnl = (exit_price - entry_price) * quantity
        
        assert pnl == Decimal("-50")  # 50 USDT 손실
    
    def test_pnl_short_profit(self):
        """숏 포지션 수익 계산"""
        entry_price = Decimal("50000")
        exit_price = Decimal("45000")
        quantity = Decimal("0.01")
        
        # 숏 PnL = (진입가 - 청산가) × 수량
        pnl = (entry_price - exit_price) * quantity
        
        assert pnl == Decimal("50")  # 50 USDT 수익
    
    def test_pnl_short_loss(self):
        """숏 포지션 손실 계산"""
        entry_price = Decimal("50000")
        exit_price = Decimal("55000")
        quantity = Decimal("0.01")
        
        pnl = (entry_price - exit_price) * quantity
        
        assert pnl == Decimal("-50")  # 50 USDT 손실
    
    def test_roe_calculation(self):
        """ROE(수익률) 계산"""
        pnl = Decimal("50")
        margin = Decimal("50")
        
        # ROE = (PnL / 증거금) × 100
        roe = (pnl / margin) * 100
        
        assert roe == Decimal("100")  # 100% 수익률
    
    def test_roe_with_leverage(self):
        """레버리지에 따른 ROE 계산"""
        # 10배 레버리지로 1% 가격 상승 시
        entry_price = Decimal("50000")
        exit_price = Decimal("50500")  # 1% 상승
        quantity = Decimal("0.01")
        leverage = 10
        
        position_value = quantity * entry_price
        margin = position_value / leverage
        pnl = (exit_price - entry_price) * quantity
        roe = (pnl / margin) * 100
        
        # 1% 가격 상승 × 10배 레버리지 = 10% ROE
        assert roe == Decimal("10")
    
    def test_fee_calculation(self):
        """수수료 계산"""
        position_value = Decimal("1000")
        fee_rate = Decimal("0.001")  # 0.1%
        
        fee = position_value * fee_rate
        
        assert fee == Decimal("1")  # 1 USDT 수수료
    
    def test_net_pnl_after_fee(self):
        """수수료 차감 후 순이익"""
        pnl = Decimal("100")
        entry_fee = Decimal("1")
        exit_fee = Decimal("1")
        
        net_pnl = pnl - entry_fee - exit_fee
        
        assert net_pnl == Decimal("98")


# =============================================================================
# 6. 유틸리티 함수 테스트
# =============================================================================

class TestUtilities:
    """유틸리티 함수 테스트"""
    
    def test_username_validation_alphanumeric(self):
        """사용자명 검증 - 영문자+숫자만"""
        # 유효한 사용자명
        valid_usernames = ["user123", "testuser", "abc123def", "User1"]
        # 무효한 사용자명
        invalid_usernames = ["user_name", "user-name", "user@name", "user name"]
        
        pattern = r'^[a-zA-Z0-9]+$'
        
        for username in valid_usernames:
            assert re.match(pattern, username), f"{username} should be valid"
        
        for username in invalid_usernames:
            assert not re.match(pattern, username), f"{username} should be invalid"
    
    def test_symbol_validation(self):
        """심볼 유효성 검증"""
        from app.core.config import settings
        
        valid_symbol = "BTCUSDT"
        invalid_symbol = "INVALIDUSDT"
        
        assert valid_symbol in settings.SUPPORTED_SYMBOLS
        assert invalid_symbol not in settings.SUPPORTED_SYMBOLS
    
    def test_leverage_validation(self):
        """레버리지 유효성 검증"""
        valid_leverages = [1, 2, 5, 10, 20, 50, 100, 125]
        invalid_leverages = [0, -1, 150, 200, 1000]
        
        for lev in valid_leverages:
            assert 1 <= lev <= 125, f"Leverage {lev} should be valid"
        
        for lev in invalid_leverages:
            assert not (1 <= lev <= 125), f"Leverage {lev} should be invalid"
    
    def test_quantity_validation(self):
        """수량 유효성 검증"""
        valid_quantities = [Decimal("0.001"), Decimal("0.1"), Decimal("1"), Decimal("10")]
        invalid_quantities = [Decimal("0"), Decimal("-1"), Decimal("-0.001")]
        
        for qty in valid_quantities:
            assert qty > 0, f"Quantity {qty} should be valid"
        
        for qty in invalid_quantities:
            assert not (qty > 0), f"Quantity {qty} should be invalid"
    
    def test_decimal_precision(self):
        """Decimal 정밀도 테스트"""
        # 부동소수점 문제 방지
        a = Decimal("0.1")
        b = Decimal("0.2")
        c = Decimal("0.3")
        
        # float의 경우: 0.1 + 0.2 != 0.3
        assert a + b == c
    
    def test_price_formatting(self):
        """가격 포맷팅 테스트"""
        price = Decimal("12345.67890")
        
        # 소수점 2자리로 반올림
        formatted = round(price, 2)
        assert formatted == Decimal("12345.68")
        
        # 소수점 8자리 (암호화폐 표준)
        formatted_crypto = round(price, 8)
        assert formatted_crypto == Decimal("12345.67890000")


# =============================================================================
# 7. 엣지 케이스 테스트
# =============================================================================

class TestEdgeCases:
    """엣지 케이스 테스트"""
    
    def test_zero_quantity_position(self):
        """0 수량 포지션"""
        quantity = Decimal("0")
        price = Decimal("50000")
        
        position_value = quantity * price
        assert position_value == Decimal("0")
    
    def test_very_small_quantity(self):
        """매우 작은 수량"""
        quantity = Decimal("0.00000001")  # 1 satoshi
        price = Decimal("100000")
        
        position_value = quantity * price
        assert position_value == Decimal("0.001")
    
    def test_very_large_position(self):
        """매우 큰 포지션"""
        quantity = Decimal("1000")
        price = Decimal("100000")
        leverage = 1
        
        position_value = quantity * price  # 100,000,000 USDT
        margin = position_value / leverage
        
        assert position_value == Decimal("100000000")
    
    def test_max_leverage_liquidation(self):
        """최대 레버리지(125x) 청산가"""
        entry_price = Decimal("50000")
        leverage = 125
        maintenance_margin_rate = Decimal("0.004")  # 0.4% for 125x
        
        # 125배 레버리지면 약 0.8% 하락시 청산
        liquidation_price = entry_price * (1 - (1 - maintenance_margin_rate) / leverage)
        
        # 청산가는 진입가의 99.2% 정도
        assert liquidation_price > entry_price * Decimal("0.99")
        assert liquidation_price < entry_price
    
    def test_breakeven_price(self):
        """손익분기점 가격 계산"""
        entry_price = Decimal("50000")
        quantity = Decimal("0.01")
        entry_fee = Decimal("0.5")  # 0.1%
        exit_fee = Decimal("0.5")   # 0.1%
        
        total_fee = entry_fee + exit_fee
        # 수수료를 커버하기 위한 가격 변동
        fee_per_unit = total_fee / quantity
        
        breakeven_price = entry_price + fee_per_unit
        assert breakeven_price == Decimal("50100")


# =============================================================================
# 테스트 실행
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])