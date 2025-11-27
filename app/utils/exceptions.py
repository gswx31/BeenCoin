# app/utils/exceptions.py
"""
커스텀 예외 클래스
명확한 에러 메시지와 HTTP 상태 코드를 제공
"""
from fastapi import HTTPException, status


class BeenCoinException(HTTPException):
    """기본 예외 클래스 (모든 커스텀 예외의 부모)"""

    def __init__(self, detail: str, status_code: int = 400):
        super().__init__(status_code=status_code, detail=detail)


# ===========================
# 인증 관련 예외
# ===========================


class UnauthorizedException(BeenCoinException):
    """인증 실패 (401)"""

    def __init__(self, detail: str = "인증에 실패했습니다"):
        super().__init__(detail=detail, status_code=status.HTTP_401_UNAUTHORIZED)


class InvalidCredentialsException(UnauthorizedException):
    """잘못된 로그인 정보"""

    def __init__(self):
        super().__init__(detail="아이디 또는 비밀번호가 올바르지 않습니다")


class TokenExpiredException(UnauthorizedException):
    """토큰 만료"""

    def __init__(self):
        super().__init__(detail="토큰이 만료되었습니다. 다시 로그인해주세요")


class InvalidTokenException(UnauthorizedException):
    """유효하지 않은 토큰"""

    def __init__(self):
        super().__init__(detail="유효하지 않은 토큰입니다")


class ForbiddenException(BeenCoinException):
    """권한 없음 (403)"""

    def __init__(self, detail: str = "접근 권한이 없습니다"):
        super().__init__(detail=detail, status_code=status.HTTP_403_FORBIDDEN)


# ===========================
# 사용자 관련 예외
# ===========================


class UserAlreadyExistsException(BeenCoinException):
    """이미 존재하는 사용자"""

    def __init__(self, username: str):
        super().__init__(
            detail=f"사용자 '{username}'은(는) 이미 존재합니다",
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class UserNotFoundException(BeenCoinException):
    """사용자를 찾을 수 없음"""

    def __init__(self):
        super().__init__(detail="사용자를 찾을 수 없습니다", status_code=status.HTTP_404_NOT_FOUND)


class UserInactiveException(ForbiddenException):
    """비활성화된 계정"""

    def __init__(self):
        super().__init__(detail="비활성화된 계정입니다")


# ===========================
# 계정 관련 예외
# ===========================


class InsufficientBalanceException(BeenCoinException):
    """잔액 부족 (400)"""

    def __init__(self, required: float, available: float):
        super().__init__(
            detail=f"잔액이 부족합니다. 필요: ${required:,.2f}, 보유: ${available:,.2f}",
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class InsufficientQuantityException(BeenCoinException):
    """수량 부족 (400)"""

    def __init__(self, symbol: str, required: float, available: float):
        super().__init__(
            detail=f"{symbol} 수량이 부족합니다. 필요: {required}, 보유: {available}",
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class AccountNotFoundException(BeenCoinException):
    """계정을 찾을 수 없음"""

    def __init__(self):
        super().__init__(
            detail="거래 계정을 찾을 수 없습니다", status_code=status.HTTP_404_NOT_FOUND
        )


# ===========================
# 주문 관련 예외
# ===========================


class OrderNotFoundException(BeenCoinException):
    """주문 없음 (404)"""

    def __init__(self, order_id: int):
        super().__init__(
            detail=f"주문을 찾을 수 없습니다 (ID: {order_id})",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class InvalidOrderException(BeenCoinException):
    """잘못된 주문 요청 (400)"""

    def __init__(self, reason: str):
        super().__init__(
            detail=f"잘못된 주문 요청: {reason}", status_code=status.HTTP_400_BAD_REQUEST
        )


class OrderAlreadyFilledException(BeenCoinException):
    """이미 체결된 주문"""

    def __init__(self, order_id: int):
        super().__init__(
            detail=f"이미 체결된 주문입니다 (ID: {order_id})",
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class OrderCancelledException(BeenCoinException):
    """취소된 주문"""

    def __init__(self, order_id: int):
        super().__init__(
            detail=f"취소된 주문입니다 (ID: {order_id})", status_code=status.HTTP_400_BAD_REQUEST
        )


# ===========================
# 시장 데이터 관련 예외
# ===========================


class MarketDataUnavailableException(BeenCoinException):
    """시장 데이터 조회 실패 (503)"""

    def __init__(self, symbol: str):
        super().__init__(
            detail=f"{symbol} 시장 데이터를 가져올 수 없습니다. 잠시 후 다시 시도해주세요.",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


class UnsupportedSymbolException(BeenCoinException):
    """지원하지 않는 심볼 (400)"""

    def __init__(self, symbol: str, supported_symbols: list):
        super().__init__(
            detail=f"지원하지 않는 심볼입니다: {symbol}. "
            f"지원 심볼: {', '.join(supported_symbols)}",
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class BinanceAPIException(BeenCoinException):
    """Binance API 오류 (503)"""

    def __init__(self, detail: str = "Binance API 연결에 실패했습니다"):
        super().__init__(detail=detail, status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
