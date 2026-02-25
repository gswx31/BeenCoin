# app/utils/rate_limiter.py


import logging
import random
import secrets
import time
from collections import defaultdict
from functools import wraps
from threading import Lock
from typing import Callable, Dict, Optional

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


# =============================================================================
# 설정 상수
# =============================================================================

MAX_USERNAME_FAILURES  = 5      # username 기준 차단 임계값
MAX_IP_FAILURES        = 10     # IP 기준 차단 임계값
BLOCK_DURATION         = 900    # 차단 지속 시간 (15분)
FAILURE_WINDOW         = 300    # 실패 카운트 윈도우 (5분)

CAPTCHA_AFTER          = 3      # 몇 번 실패부터 CAPTCHA 요구
CAPTCHA_TTL            = 300    # CAPTCHA 토큰 유효 시간 (5분)


# =============================================================================
# 내부 데이터 구조
# =============================================================================

class _Record:
    __slots__ = ("failures", "blocked_until", "timestamps")

    def __init__(self):
        self.failures: int = 0
        self.blocked_until: float = 0.0
        self.timestamps: list[float] = []   # 실패 시각 목록


class _CaptchaEntry:
    __slots__ = ("answer", "expires_at", "solved")

    def __init__(self, answer: int, ttl: int):
        self.answer    = answer
        self.expires_at = time.time() + ttl
        self.solved    = False


# =============================================================================
# LoginTracker  (IP / username 이중 추적)
# =============================================================================

class LoginTracker:
    """
    실패 횟수를 추적하고 임계값 도달 시 차단.

    핵심 원칙:
    - 존재하지 않는 username도 동일하게 카운트 → 계정 존재 여부 노출 방지
    - IP / username 두 키 모두 독립적으로 추적
    - 성공 시 해당 키 카운트 초기화
    """

    def __init__(self):
        self._data: Dict[str, _Record] = defaultdict(_Record)
        self._lock = Lock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def record_failure(self, key: str, max_failures: int = MAX_USERNAME_FAILURES) -> int:
        """
        실패 1회 기록.
        반환값: 현재 누적 실패 횟수 (차단 포함)
        """
        with self._lock:
            rec = self._data[key]
            now = time.time()

            # 윈도우 밖 기록 제거
            rec.timestamps = [t for t in rec.timestamps if now - t < FAILURE_WINDOW]
            rec.timestamps.append(now)
            rec.failures = len(rec.timestamps)

            if rec.failures >= max_failures and rec.blocked_until <= now:
                rec.blocked_until = now + BLOCK_DURATION
                logger.warning(
                    f"🔒 차단 발동: key={key!r} "
                    f"failures={rec.failures} duration={BLOCK_DURATION}s"
                )

            return rec.failures

    def record_success(self, key: str) -> None:
        """성공 시 해당 키 초기화"""
        with self._lock:
            rec = self._data[key]
            rec.failures = 0
            rec.timestamps.clear()
            rec.blocked_until = 0.0

    def is_blocked(self, key: str) -> tuple[bool, int]:
        """
        (차단여부, 남은초) 반환.
        차단 만료 시 자동 해제.
        """
        with self._lock:
            rec = self._data[key]
            now = time.time()

            if rec.blocked_until > now:
                return True, int(rec.blocked_until - now)

            # 만료된 차단 정리
            if rec.blocked_until and rec.blocked_until <= now:
                rec.blocked_until = 0.0
                rec.failures = 0
                rec.timestamps.clear()

            return False, 0

    def current_failures(self, key: str) -> int:
        """현재 윈도우 내 실패 횟수"""
        with self._lock:
            rec = self._data[key]
            now = time.time()
            rec.timestamps = [t for t in rec.timestamps if now - t < FAILURE_WINDOW]
            return len(rec.timestamps)


# 전역 인스턴스
login_tracker = LoginTracker()


# =============================================================================
# CaptchaManager  (서버사이드 수학 CAPTCHA)
# =============================================================================

class CaptchaManager:
    """
    네이버/구글처럼 봇 방지 CAPTCHA.
    여기서는 서버가 수학 문제를 만들고, 클라이언트가 답을 보내는 방식.

    실제 서비스라면 Google reCAPTCHA / hCaptcha 연동 권장.
    """

    def __init__(self):
        self._challenges: Dict[str, _CaptchaEntry] = {}
        self._lock = Lock()

    def issue(self) -> dict:
        """
        CAPTCHA 발급.
        반환: {"captcha_token": "...", "question": "3 + 7 = ?"}
        """
        a = random.randint(1, 20)
        b = random.randint(1, 20)
        ops = [
            ("+", a + b),
            ("-", a - b),
            ("×", a * b),
        ]
        op_sym, answer = random.choice(ops)

        token = secrets.token_urlsafe(32)

        with self._lock:
            self._cleanup()
            self._challenges[token] = _CaptchaEntry(answer, CAPTCHA_TTL)

        logger.debug(f"CAPTCHA 발급: token={token[:8]}... q={a}{op_sym}{b}={answer}")

        return {
            "captcha_token": token,
            "question": f"{a} {op_sym} {b} = ?",
            "expires_in": CAPTCHA_TTL,
        }

    def verify(self, token: str, answer: str) -> bool:
        """
        CAPTCHA 검증.
        - 토큰이 없거나 만료 → False
        - 정답 불일치 → False
        - 이미 사용된 토큰 → False (재사용 방지)
        """
        if not token or not answer:
            return False

        try:
            int_answer = int(answer)
        except (ValueError, TypeError):
            return False

        with self._lock:
            entry = self._challenges.get(token)
            if not entry:
                return False
            if entry.solved:
                return False
            if time.time() > entry.expires_at:
                del self._challenges[token]
                return False
            if entry.answer != int_answer:
                return False

            entry.solved = True   # 일회용
            return True

    def _cleanup(self):
        """만료된 CAPTCHA 정리 (lock 내부에서 호출)"""
        now = time.time()
        expired = [t for t, e in self._challenges.items() if now > e.expires_at]
        for t in expired:
            del self._challenges[t]


# 전역 인스턴스
captcha_manager = CaptchaManager()


# =============================================================================
# InMemoryRateLimiter  (엔드포인트 데코레이터용)
# =============================================================================

class InMemoryRateLimiter:

    def __init__(self):
        self._requests: Dict[str, list] = defaultdict(list)
        self._lock = Lock()

    def _parse(self, rate_limit: str) -> tuple[int, int]:
        try:
            count, period = rate_limit.split("/")
            windows = {"second": 1, "minute": 60, "hour": 3600, "day": 86400}
            return int(count), windows.get(period.lower(), 60)
        except Exception:
            return 100, 60

    def is_allowed(self, key: str, rate_limit: str, endpoint: str = "default") -> tuple[bool, dict]:
        max_req, window = self._parse(rate_limit)
        now = time.time()
        cutoff = now - window

        with self._lock:
            self._requests[key] = [
                r for r in self._requests[key]
                if r[0] > cutoff and r[1] == endpoint
            ]
            recent = self._requests[key]
            remaining = max_req - len(recent)

            if recent and remaining <= 0:
                reset_time = min(r[0] for r in recent) + window
            else:
                reset_time = now + window

            info = {
                "limit": max_req,
                "remaining": max(0, remaining),
                "reset": int(reset_time),
                "retry_after": max(0, int(reset_time - now)) if remaining <= 0 else 0,
            }

            if remaining > 0:
                self._requests[key].append((now, endpoint))
                return True, info
            return False, info

    def get_client_ip(self, request: Request) -> str:
        fwd = request.headers.get("X-Forwarded-For")
        if fwd:
            return fwd.split(",")[0].strip()
        real = request.headers.get("X-Real-IP")
        if real:
            return real
        return request.client.host if request.client else "unknown"


rate_limiter = InMemoryRateLimiter()


# =============================================================================
# rate_limit 데코레이터
# =============================================================================

def rate_limit(limit: str):
    """
    엔드포인트별 IP 기반 Rate Limit 데코레이터.
    사용: @rate_limit("5/minute")
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request: Optional[Request] = kwargs.get("request")
            if request is None:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break

            if request is None:
                return await func(*args, **kwargs)

            client_ip = rate_limiter.get_client_ip(request)
            endpoint  = f"{func.__module__}.{func.__name__}"
            allowed, info = rate_limiter.is_allowed(client_ip, limit, endpoint)

            if not allowed:
                logger.warning(f"🚫 Rate limit 초과: ip={client_ip} endpoint={endpoint}")
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "message": "요청이 너무 많습니다. 잠시 후 다시 시도해주세요.",
                        "retry_after": info["retry_after"],
                    },
                    headers={"Retry-After": str(info["retry_after"])},
                )

            return await func(*args, **kwargs)
        return wrapper
    return decorator


# =============================================================================
# 전역 Rate Limit 미들웨어
# =============================================================================

async def rate_limit_middleware(request: Request, call_next):
    if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json"]:
        return await call_next(request)

    try:
        from app.core.config_secure import settings
        if not getattr(settings, "RATE_LIMIT_ENABLED", True):
            return await call_next(request)
        default_limit = settings.RATE_LIMIT_API
    except ImportError:
        try:
            from app.core.config import settings
            default_limit = getattr(settings, "RATE_LIMIT_API", "100/minute")
        except ImportError:
            default_limit = "100/minute"

    client_ip = rate_limiter.get_client_ip(request)
    allowed, info = rate_limiter.is_allowed(client_ip, default_limit, "global")

    if not allowed:
        return JSONResponse(
            status_code=429,
            content={"detail": "요청이 너무 많습니다. 잠시 후 다시 시도해주세요.",
                     "retry_after": info["retry_after"]},
            headers={"Retry-After": str(info["retry_after"])},
        )

    response = await call_next(request)
    response.headers["X-RateLimit-Limit"]     = str(info["limit"])
    response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
    response.headers["X-RateLimit-Reset"]     = str(info["reset"])
    return response