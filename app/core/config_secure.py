# app/core/config_secure.py
"""
보안 강화된 설정 모듈
- SECRET_KEY 자동 생성 및 프로덕션 강제
- 환경별 설정 분리
"""
import os
import secrets
from pathlib import Path
from typing import List

from dotenv import load_dotenv

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError:
    from pydantic import BaseSettings

load_dotenv()

def generate_secret_key() -> str:
    """
    암호학적으로 안전한 시크릿 키 생성
    64바이트 = 512비트 (현재 권장 수준)
    """
    return secrets.token_urlsafe(64)

class SecureSettings(BaseSettings):
    """
    보안 강화된 설정 클래스
    """

    # ===========================================
    # 환경 설정
    # ===========================================
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # ===========================================
    # API 설정
    # ===========================================
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "BeenCoin API"
    VERSION: str = "2.1.0"
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))

    # ===========================================
    # 데이터베이스 설정
    # ===========================================
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./beencoin.db")
    DB_ECHO: bool = False
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_PRE_PING: bool = True
    DB_POOL_TIMEOUT: int = 30

    # ===========================================
    # 🔐 JWT 보안 설정 (강화됨)
    # ===========================================
    # SECRET_KEY는 환경변수에서 가져오거나 자동 생성
    # 프로덕션에서는 반드시 환경변수로 설정해야 함
    _secret_key: str | None = None

    @property
    def SECRET_KEY(self) -> str:
        """
        시크릿 키 반환
        - 프로덕션: 환경변수 필수
        - 개발: 자동 생성 (경고 출력)
        """
        if self._secret_key:
            return self._secret_key

        env_secret = os.getenv("SECRET_KEY")

        if self.ENVIRONMENT == "production":
            if not env_secret:
                raise ValueError(
                    "🚨 프로덕션 환경에서는 SECRET_KEY 환경변수가 필수입니다!\n"
                    "다음 명령어로 안전한 키를 생성하세요:\n"
                    "python -c \"import secrets; print(secrets.token_urlsafe(64))\""
                )
            if len(env_secret) < 32:
                raise ValueError(
                    "🚨 SECRET_KEY가 너무 짧습니다! 최소 32자 이상이어야 합니다."
                )
            self._secret_key = env_secret
        else:
            # 개발 환경에서는 자동 생성 (세션마다 변경됨)
            if env_secret:
                self._secret_key = env_secret
            else:
                self._secret_key = generate_secret_key()
                print(
                    "⚠️  개발 환경: SECRET_KEY가 자동 생성되었습니다.\n"
                    "   서버 재시작 시 모든 JWT 토큰이 무효화됩니다.\n"
                    "   프로덕션에서는 반드시 환경변수로 설정하세요!"
                )

        return self._secret_key

    ALGORITHM: str = "HS256"

    # 토큰 만료 시간 (보안 강화: 기본값 축소)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")  # 1시간 (기존 24시간에서 축소)
    )
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(
        os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7")  # 7일
    )

    # ===========================================
    # 🔐 Rate Limiting 설정
    # ===========================================
    RATE_LIMIT_ENABLED: bool = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"

    # 엔드포인트별 제한 (요청 수/시간)
    RATE_LIMIT_LOGIN: str = os.getenv("RATE_LIMIT_LOGIN", "5/minute")
    RATE_LIMIT_REGISTER: str = os.getenv("RATE_LIMIT_REGISTER", "3/minute")
    RATE_LIMIT_API: str = os.getenv("RATE_LIMIT_API", "100/minute")
    RATE_LIMIT_TRADING: str = os.getenv("RATE_LIMIT_TRADING", "30/minute")

    # ===========================================
    # 🔐 CORS 설정 (보안 강화)
    # ===========================================
    @property
    def CORS_ORIGINS(self) -> List[str]:
        """
        환경별 CORS 오리진 설정
        """
        if self.ENVIRONMENT == "production":
            # 프로덕션: 명시적 도메인만 허용
            origins = os.getenv("CORS_ORIGINS", "")
            if not origins:
                raise ValueError(
                    "🚨 프로덕션 환경에서는 CORS_ORIGINS 환경변수가 필수입니다!"
                )
            return [o.strip() for o in origins.split(",")]
        else:
            # 개발: 로컬호스트 허용
            default = "http://localhost:3000,http://localhost:8000,http://127.0.0.1:3000,http://127.0.0.1:8000"
            origins = os.getenv("CORS_ORIGINS", default)
            return [o.strip() for o in origins.split(",")]

    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    CORS_ALLOW_HEADERS: List[str] = ["Authorization", "Content-Type", "X-Request-ID"]

    # ===========================================
    # 🔐 보안 헤더 설정
    # ===========================================
    SECURITY_HEADERS: dict = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Content-Security-Policy": "default-src 'self'",
        "Referrer-Policy": "strict-origin-when-cross-origin",
    }

    # ===========================================
    # Binance API
    # ===========================================
    BINANCE_API_URL: str = "https://api.binance.com/api/v3"
    BINANCE_API_KEY: str | None = os.getenv("BINANCE_API_KEY")
    BINANCE_API_SECRET: str | None = os.getenv("BINANCE_API_SECRET")
    BINANCE_TIMEOUT: int = 10

    # ===========================================
    # 거래 설정
    # ===========================================
    INITIAL_BALANCE: float = float(os.getenv("INITIAL_BALANCE", "1000000"))

    @property
    def SUPPORTED_SYMBOLS(self) -> List[str]:
        symbols_str = os.getenv(
            "SUPPORTED_SYMBOLS",
            "BTCUSDT,ETHUSDT,BNBUSDT,ADAUSDT,XRPUSDT,SOLUSDT,DOGEUSDT"
        )
        return [s.strip() for s in symbols_str.split(",")]

    # 레버리지 설정
    MAX_LEVERAGE: int = int(os.getenv("MAX_LEVERAGE", "125"))

    # 손절/익절 기본 비율
    DEFAULT_STOP_LOSS_PERCENT: float = 3.0
    DEFAULT_TAKE_PROFIT_PERCENT: float = 6.0
    AUTO_STOP_LOSS_ENABLED: bool = True
    AUTO_TAKE_PROFIT_ENABLED: bool = True
    OCO_ENABLED: bool = True

    # ===========================================
    # 로깅
    # ===========================================
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_SENSITIVE_DATA: bool = False  # 민감 데이터 로깅 비활성화

    # ===========================================
    # HTTP 설정
    # ===========================================
    HTTP_TIMEOUT: int = 30

    # ===========================================
    # 캐시 설정
    # ===========================================
    CACHE_TTL: int = 5
    CACHE_ENABLED: bool = True

    # Pydantic 설정
    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=".env",
        extra="allow"
    )

# 싱글톤 설정 인스턴스
settings = SecureSettings()

# 시작 시 설정 검증
def validate_settings():
    """설정 유효성 검증"""
    errors = []

    # SECRET_KEY 검증 (프로퍼티 접근 시 자동 검증됨)
    try:
        _ = settings.SECRET_KEY
    except ValueError as e:
        errors.append(str(e))

    # 프로덕션 환경 추가 검증
    if settings.ENVIRONMENT == "production":
        if settings.DEBUG:
            errors.append("🚨 프로덕션 환경에서 DEBUG=true는 위험합니다!")

        if "localhost" in str(settings.CORS_ORIGINS):
            print("⚠️  경고: 프로덕션 CORS에 localhost가 포함되어 있습니다.")

    if errors:
        raise ValueError("\n".join(errors))

# 개발 환경에서 설정 출력
if settings.LOG_LEVEL == "DEBUG" or settings.ENVIRONMENT == "development":
    print("=" * 60)
    print("⚙️  BeenCoin Secure Configuration")
    print("=" * 60)
    print(f"Environment: {settings.ENVIRONMENT}")
    print(f"Database: {settings.DATABASE_URL}")
    print(f"Token Expiry: {settings.ACCESS_TOKEN_EXPIRE_MINUTES} minutes")
    print(f"Rate Limiting: {'Enabled' if settings.RATE_LIMIT_ENABLED else 'Disabled'}")
    print(f"CORS Origins: {len(settings.CORS_ORIGINS)} domains")
    print("=" * 60)
