# app/utils/error_handlers.py
"""
통합 에러 핸들러
================

⚠️ 수정 내용: 
- 예제 코드 제거 (F821 오류 수정)
- 실제 사용하는 에러 핸들러만 남김
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import traceback
import logging

logger = logging.getLogger(__name__)


# ================================
# 커스텀 예외 클래스
# ================================

class BeenCoinException(Exception):
    """기본 예외 클래스"""
    def __init__(self, detail: str, status_code: int = 400, error_code: str = None):
        self.detail = detail
        self.status_code = status_code
        self.error_code = error_code or "BEENCOIN_ERROR"
        super().__init__(detail)


class InsufficientBalanceError(BeenCoinException):
    """잔액 부족"""
    def __init__(self, required: float = 0, available: float = 0):
        detail = f"잔액이 부족합니다. 필요: ${required:,.2f}, 보유: ${available:,.2f}"
        super().__init__(detail, 400, "INSUFFICIENT_BALANCE")


class InsufficientQuantityError(BeenCoinException):
    """수량 부족"""
    def __init__(self, required: float = 0, available: float = 0):
        detail = f"수량이 부족합니다. 필요: {required}, 보유: {available}"
        super().__init__(detail, 400, "INSUFFICIENT_QUANTITY")


class InvalidSymbolError(BeenCoinException):
    """잘못된 심볼"""
    def __init__(self, symbol: str):
        detail = f"지원하지 않는 심볼입니다: {symbol}"
        super().__init__(detail, 400, "INVALID_SYMBOL")


class PositionNotFoundError(BeenCoinException):
    """포지션 없음"""
    def __init__(self, position_id: str = None):
        detail = f"포지션을 찾을 수 없습니다" + (f" (ID: {position_id})" if position_id else "")
        super().__init__(detail, 404, "POSITION_NOT_FOUND")


class AccountNotFoundError(BeenCoinException):
    """계정 없음"""
    def __init__(self):
        super().__init__("계정을 찾을 수 없습니다", 404, "ACCOUNT_NOT_FOUND")


class UnauthorizedError(BeenCoinException):
    """인증 오류"""
    def __init__(self, detail: str = "인증이 필요합니다"):
        super().__init__(detail, 401, "UNAUTHORIZED")


class ForbiddenError(BeenCoinException):
    """권한 오류"""
    def __init__(self, detail: str = "권한이 없습니다"):
        super().__init__(detail, 403, "FORBIDDEN")


class MarketDataError(BeenCoinException):
    """시장 데이터 오류"""
    def __init__(self, detail: str = "시장 데이터를 가져올 수 없습니다"):
        super().__init__(detail, 503, "MARKET_DATA_ERROR")


# ================================
# 에러 핸들러 등록 함수
# ================================

def register_error_handlers(app: FastAPI):
    """FastAPI 앱에 에러 핸들러 등록"""
    
    @app.exception_handler(BeenCoinException)
    async def beencoin_exception_handler(request: Request, exc: BeenCoinException):
        """커스텀 예외 핸들러"""
        logger.warning(f"⚠️ {exc.error_code}: {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.error_code,
                "detail": exc.detail,
                "success": False
            }
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """요청 검증 오류 핸들러"""
        errors = []
        for error in exc.errors():
            field = " -> ".join(str(loc) for loc in error["loc"])
            errors.append({
                "field": field,
                "message": error["msg"],
                "type": error["type"]
            })
        
        logger.warning(f"⚠️ Validation Error: {errors}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "ValidationError",
                "detail": "요청 데이터가 올바르지 않습니다",
                "errors": errors,
                "success": False
            }
        )
    
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """HTTP 예외 핸들러"""
        error_messages = {
            400: "잘못된 요청입니다",
            401: "인증이 필요합니다",
            403: "권한이 없습니다",
            404: "리소스를 찾을 수 없습니다",
            405: "허용되지 않은 메서드입니다",
            500: "서버 내부 오류가 발생했습니다",
        }
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": f"HTTP{exc.status_code}Error",
                "detail": exc.detail or error_messages.get(exc.status_code, "오류가 발생했습니다"),
                "success": False
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """일반 예외 핸들러"""
        logger.error(f"❌ Unhandled Exception: {str(exc)}")
        logger.error(traceback.format_exc())
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "InternalServerError",
                "detail": "서버 내부 오류가 발생했습니다",
                "success": False
            }
        )
    
    logger.info("✅ 에러 핸들러 등록 완료")


# ================================
# 유틸리티 함수
# ================================

def create_error_response(
    status_code: int,
    error: str,
    detail: str,
    errors: list = None
) -> JSONResponse:
    """에러 응답 생성 헬퍼"""
    content = {
        "error": error,
        "detail": detail,
        "success": False
    }
    if errors:
        content["errors"] = errors
    
    return JSONResponse(status_code=status_code, content=content)