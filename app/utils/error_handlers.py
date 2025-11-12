# app/utils/error_handlers.py - 새 파일
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError
from decimal import InvalidOperation
import traceback

class BeenCoinException(Exception):
    """베이스 예외 클래스"""
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

class InsufficientBalanceError(BeenCoinException):
    """잔액 부족 에러"""
    def __init__(self):
        super().__init__("잔액이 부족합니다", status.HTTP_400_BAD_REQUEST)

class InsufficientQuantityError(BeenCoinException):
    """수량 부족 에러"""
    def __init__(self):
        super().__init__("보유 수량이 부족합니다", status.HTTP_400_BAD_REQUEST)

class InvalidSymbolError(BeenCoinException):
    """지원하지 않는 심볼 에러"""
    def __init__(self, symbol: str):
        super().__init__(
            f"지원하지 않는 심볼입니다: {symbol}", 
            status.HTTP_400_BAD_REQUEST
        )

class BinanceAPIError(BeenCoinException):
    """Binance API 에러"""
    def __init__(self, detail: str = "외부 API 오류"):
        super().__init__(detail, status.HTTP_503_SERVICE_UNAVAILABLE)


# 전역 에러 핸들러 등록
def register_error_handlers(app):
    """FastAPI 앱에 에러 핸들러 등록"""
    
    @app.exception_handler(BeenCoinException)
    async def beencoin_exception_handler(request: Request, exc: BeenCoinException):
        """커스텀 예외 처리"""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.__class__.__name__,
                "detail": exc.message,
                "path": str(request.url)
            }
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, 
        exc: RequestValidationError
    ):
        """요청 검증 에러 처리"""
        errors = []
        for error in exc.errors():
            errors.append({
                "field": " -> ".join(str(x) for x in error["loc"]),
                "message": error["msg"],
                "type": error["type"]
            })
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "ValidationError",
                "detail": "입력값 검증 실패",
                "errors": errors
            }
        )
    
    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(request: Request, exc: IntegrityError):
        """데이터베이스 무결성 에러 처리"""
        error_msg = "데이터베이스 오류"
        
        if "UNIQUE constraint failed" in str(exc):
            error_msg = "이미 존재하는 데이터입니다"
        elif "FOREIGN KEY constraint failed" in str(exc):
            error_msg = "참조 데이터가 존재하지 않습니다"
        
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "error": "IntegrityError",
                "detail": error_msg
            }
        )
    
    @app.exception_handler(InvalidOperation)
    async def decimal_error_handler(request: Request, exc: InvalidOperation):
        """Decimal 연산 에러 처리"""
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": "InvalidOperation",
                "detail": "잘못된 숫자 형식입니다"
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """일반 예외 처리 (500 에러)"""
        # 에러 로깅
        print("=" * 60)
        print("❌ Unhandled Exception")
        print("=" * 60)
        traceback.print_exc()
        print("=" * 60)
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "InternalServerError",
                "detail": "서버 내부 오류가 발생했습니다",
                "message": str(exc) if __debug__ else None
            }
        )


# ================================
# app/main.py에 추가
# ================================
from app.utils.error_handlers import register_error_handlers

app = FastAPI(...)

# 에러 핸들러 등록
register_error_handlers(app)


# ================================
# app/services/order_service.py 에러 처리 개선
# ================================
from app.utils.error_handlers import (
    InsufficientBalanceError,
    InsufficientQuantityError,
    InvalidSymbolError
)

async def create_order(session: Session, user_id: str, order_data: OrderCreate) -> Order:
    # 심볼 검증
    if order_data.symbol not in settings.SUPPORTED_SYMBOLS:
        raise InvalidSymbolError(order_data.symbol)
    
    # ... 주문 생성 로직
    
def update_position(
    session: Session, 
    user_id: str, 
    symbol: str, 
    side: str, 
    quantity: Decimal, 
    price: Decimal, 
    fee: Decimal
):
    account = session.exec(
        select(TradingAccount).where(TradingAccount.user_id == user_id)
    ).first()
    
    if not account:
        raise BeenCoinException("계정을 찾을 수 없습니다", 404)
    
    # ... 포지션 처리
    
    if side == 'BUY':
        net_cost = (price * quantity) + fee
        if account.balance < net_cost:
            raise InsufficientBalanceError()
        # ... 매수 처리
        
    elif side == 'SELL':
        if position.quantity < quantity:
            raise InsufficientQuantityError()
        # ... 매도 처리