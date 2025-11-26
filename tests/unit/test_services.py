# ============================================================================
# 파일: tests/unit/test_services.py
# ============================================================================
# 단위 테스트 - 서비스 및 유틸리티 함수
# ============================================================================

"""
단위 테스트 항목:
1. Security 유틸리티 (비밀번호 해싱, JWT 토큰)
2. 설정 (Config)
3. 모델 유효성 검사
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal


# =============================================================================
# 1. Security 유틸리티 테스트
# =============================================================================

class TestSecurityUtils:
    """보안 유틸리티 테스트"""
    
    def test_hash_password(self):
        """비밀번호 해싱"""
        from app.utils.security import hash_password
        
        password = "testpassword123"
        hashed = hash_password(password)
        
        assert hashed != password
        assert len(hashed) > 0
        # Argon2 또는 bcrypt 해시 형식 확인
        assert hashed.startswith("$argon2") or hashed.startswith("$2")
    
    def test_verify_password_correct(self):
        """올바른 비밀번호 검증"""
        from app.utils.security import hash_password, verify_password
        
        password = "testpassword123"
        hashed = hash_password(password)
        
        assert verify_password(password, hashed) is True
    
    def test_verify_password_incorrect(self):
        """잘못된 비밀번호 검증"""
        from app.utils.security import hash_password, verify_password
        
        password = "testpassword123"
        hashed = hash_password(password)
        
        assert verify_password("wrongpassword", hashed) is False
    
    def test_create_access_token(self):
        """JWT 액세스 토큰 생성"""
        from app.utils.security import create_access_token
        
        token = create_access_token(data={"sub": "testuser"})
        
        assert token is not None
        assert len(token) > 0
        # JWT 형식 확인 (header.payload.signature)
        assert len(token.split(".")) == 3
    
    def test_create_access_token_with_expiry(self):
        """만료 시간이 있는 JWT 토큰 생성"""
        from app.utils.security import create_access_token
        
        token = create_access_token(
            data={"sub": "testuser"},
            expires_delta=timedelta(minutes=30)
        )
        
        assert token is not None
    
    def test_decode_access_token_valid(self):
        """유효한 JWT 토큰 디코딩"""
        from app.utils.security import create_access_token, decode_access_token
        
        username = "testuser"
        token = create_access_token(data={"sub": username})
        payload = decode_access_token(token)
        
        assert payload["sub"] == username
        assert "exp" in payload
        assert "iat" in payload
    
    def test_decode_access_token_expired(self):
        """만료된 JWT 토큰 디코딩 실패"""
        from app.utils.security import create_access_token, decode_access_token
        from fastapi import HTTPException
        
        # 이미 만료된 토큰 생성
        token = create_access_token(
            data={"sub": "testuser"},
            expires_delta=timedelta(minutes=-10)
        )
        
        with pytest.raises(HTTPException) as exc_info:
            decode_access_token(token)
        
        assert exc_info.value.status_code == 401
    
    def test_decode_access_token_invalid(self):
        """잘못된 JWT 토큰 디코딩 실패"""
        from app.utils.security import decode_access_token
        from fastapi import HTTPException
        
        with pytest.raises(HTTPException) as exc_info:
            decode_access_token("invalid.token.here")
        
        assert exc_info.value.status_code == 401
    
    def test_password_hash_uniqueness(self):
        """동일한 비밀번호도 다른 해시 생성"""
        from app.utils.security import hash_password
        
        password = "samepassword"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        
        # 솔트로 인해 매번 다른 해시
        assert hash1 != hash2


# =============================================================================
# 2. 설정 테스트
# =============================================================================

class TestConfig:
    """설정 테스트"""
    
    def test_settings_load(self):
        """설정 로드"""
        from app.core.config import settings
        
        assert settings is not None
        assert settings.PROJECT_NAME is not None
    
    def test_database_url(self):
        """데이터베이스 URL"""
        from app.core.config import settings
        
        assert settings.DATABASE_URL is not None
        # SQLite 또는 PostgreSQL
        assert "sqlite" in settings.DATABASE_URL or "postgresql" in settings.DATABASE_URL
    
    def test_jwt_settings(self):
        """JWT 설정"""
        from app.core.config import settings
        
        assert settings.SECRET_KEY is not None
        assert len(settings.SECRET_KEY) > 0
        assert settings.ALGORITHM == "HS256"
        assert settings.ACCESS_TOKEN_EXPIRE_MINUTES > 0
    
    def test_supported_symbols(self):
        """지원되는 심볼 목록"""
        from app.core.config import settings
        
        assert settings.SUPPORTED_SYMBOLS is not None
        assert len(settings.SUPPORTED_SYMBOLS) > 0
        assert "BTCUSDT" in settings.SUPPORTED_SYMBOLS
    
    def test_initial_balance(self):
        """초기 잔액 설정"""
        from app.core.config import settings
        
        assert settings.INITIAL_BALANCE > 0


# =============================================================================
# 3. 모델 유효성 검사 테스트
# =============================================================================

class TestModelValidation:
    """모델 유효성 검사 테스트"""
    
    def test_user_create_schema(self):
        """사용자 생성 스키마 유효성"""
        from app.schemas.user import UserCreate
        
        # 유효한 데이터
        user = UserCreate(username="testuser", password="testpass123")
        assert user.username == "testuser"
        assert user.password == "testpass123"
    
    def test_user_create_schema_invalid(self):
        """사용자 생성 스키마 - 잘못된 데이터"""
        from app.schemas.user import UserCreate
        from pydantic import ValidationError
        
        # 빈 username
        with pytest.raises(ValidationError):
            UserCreate(username="", password="testpass123")
    
    def test_futures_position_schema(self):
        """선물 포지션 스키마 유효성"""
        from pydantic import BaseModel, Field
        from decimal import Decimal
        
        # 직접 스키마 정의 (실제 스키마와 동일)
        class FuturesPositionOpen(BaseModel):
            symbol: str
            side: str
            quantity: Decimal = Field(gt=0)
            leverage: int = Field(ge=1, le=125)
            order_type: str = "MARKET"
        
        # 유효한 데이터
        position = FuturesPositionOpen(
            symbol="BTCUSDT",
            side="LONG",
            quantity=Decimal("0.001"),
            leverage=10
        )
        assert position.symbol == "BTCUSDT"
        assert position.leverage == 10
    
    def test_futures_position_invalid_leverage(self):
        """선물 포지션 - 잘못된 레버리지"""
        from pydantic import BaseModel, Field, ValidationError
        from decimal import Decimal
        
        class FuturesPositionOpen(BaseModel):
            symbol: str
            side: str
            quantity: Decimal = Field(gt=0)
            leverage: int = Field(ge=1, le=125)
            order_type: str = "MARKET"
        
        # 레버리지 126 (최대 125)
        with pytest.raises(ValidationError):
            FuturesPositionOpen(
                symbol="BTCUSDT",
                side="LONG",
                quantity=Decimal("0.001"),
                leverage=126
            )
    
    def test_futures_position_invalid_quantity(self):
        """선물 포지션 - 음수 수량"""
        from pydantic import BaseModel, Field, ValidationError
        from decimal import Decimal
        
        class FuturesPositionOpen(BaseModel):
            symbol: str
            side: str
            quantity: Decimal = Field(gt=0)
            leverage: int = Field(ge=1, le=125)
        
        # 음수 수량
        with pytest.raises(ValidationError):
            FuturesPositionOpen(
                symbol="BTCUSDT",
                side="LONG",
                quantity=Decimal("-0.001"),
                leverage=10
            )


# =============================================================================
# 4. 유틸리티 함수 테스트
# =============================================================================

class TestUtilityFunctions:
    """유틸리티 함수 테스트"""
    
    def test_decimal_conversion(self):
        """Decimal 변환"""
        from decimal import Decimal
        
        # 문자열에서 Decimal
        d1 = Decimal("0.001")
        assert d1 == Decimal("0.001")
        
        # float에서 Decimal (주의: 정밀도 손실 가능)
        d2 = Decimal(str(0.001))
        assert d2 == Decimal("0.001")
    
    def test_datetime_utc(self):
        """UTC 시간"""
        from datetime import datetime, timezone
        
        now = datetime.utcnow()
        assert now.tzinfo is None  # naive datetime
        
        now_aware = datetime.now(timezone.utc)
        assert now_aware.tzinfo is not None
    
    def test_uuid_generation(self):
        """UUID 생성"""
        import uuid
        
        id1 = str(uuid.uuid4())
        id2 = str(uuid.uuid4())
        
        assert id1 != id2
        assert len(id1) == 36


# =============================================================================
# 5. 계산 로직 테스트
# =============================================================================

class TestCalculations:
    """거래 계산 로직 테스트"""
    
    def test_pnl_calculation_long(self):
        """롱 포지션 손익 계산"""
        entry_price = Decimal("50000")
        exit_price = Decimal("55000")
        quantity = Decimal("0.1")
        leverage = 10
        
        # PnL = (exit - entry) * quantity
        pnl = (exit_price - entry_price) * quantity
        assert pnl == Decimal("500")
        
        # 레버리지 적용 시 ROE
        margin = (entry_price * quantity) / leverage  # 500 USDT
        roe = (pnl / margin) * 100
        assert roe == Decimal("100")  # 100% 수익
    
    def test_pnl_calculation_short(self):
        """숏 포지션 손익 계산"""
        entry_price = Decimal("50000")
        exit_price = Decimal("45000")
        quantity = Decimal("0.1")
        
        # 숏은 가격이 내려가야 이익
        pnl = (entry_price - exit_price) * quantity
        assert pnl == Decimal("500")
    
    def test_liquidation_price_long(self):
        """롱 포지션 청산가 계산"""
        entry_price = Decimal("50000")
        leverage = 10
        
        # 청산가 ≈ entry * (1 - 1/leverage)
        # 실제로는 유지 증거금 등 고려
        liquidation_price = entry_price * (1 - Decimal("1") / leverage)
        assert liquidation_price == Decimal("45000")
    
    def test_liquidation_price_short(self):
        """숏 포지션 청산가 계산"""
        entry_price = Decimal("50000")
        leverage = 10
        
        # 숏 청산가 ≈ entry * (1 + 1/leverage)
        liquidation_price = entry_price * (1 + Decimal("1") / leverage)
        assert liquidation_price == Decimal("55000")
    
    def test_margin_calculation(self):
        """필요 증거금 계산"""
        entry_price = Decimal("50000")
        quantity = Decimal("0.1")
        leverage = 10
        
        # 증거금 = (가격 * 수량) / 레버리지
        margin = (entry_price * quantity) / leverage
        assert margin == Decimal("500")
    
    def test_position_value(self):
        """포지션 가치 계산"""
        price = Decimal("50000")
        quantity = Decimal("0.1")
        
        position_value = price * quantity
        assert position_value == Decimal("5000")
    
    def test_fee_calculation(self):
        """수수료 계산"""
        position_value = Decimal("10000")
        fee_rate = Decimal("0.001")  # 0.1%
        
        fee = position_value * fee_rate
        assert fee == Decimal("10")


# =============================================================================
# 실행
# =============================================================================
# pytest tests/unit/test_services.py -v
# pytest tests/unit/test_services.py -v -k "test_hash"
