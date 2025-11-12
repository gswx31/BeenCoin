# 🪙 BeenCoin - 실시간 암호화폐 모의투자 플랫폼

<div align="center">


</div>

## 📋 목차

- [소개](#-소개)
- [주요 기능](#-주요-기능)
- [기술 스택](#-기술-스택)
- [시작하기](#-시작하기)
- [프로젝트 구조](#-프로젝트-구조)
- [API 문서](#-api-문서)
- [개발 가이드](#-개발-가이드)
- [트러블슈팅](#-트러블슈팅)

## 🎯 소개

BeenCoin은 실제 Binance API를 활용한 암호화폐 모의투자 플랫폼입니다. 
실시간 시세 데이터를 기반으로 안전하게 투자 연습을 할 수 있습니다.

### 특징

- ✅ **실시간 시세**: Binance Public API를 통한 실제 시장 데이터
- ✅ **WebSocket 스트리밍**: 실시간 가격 업데이트
- ✅ **주문 시스템**: 시장가/지정가 매수/매도
- ✅ **포트폴리오 관리**: 실시간 수익률 계산

## 🚀 주요 기능

### 1. 사용자 관리
- JWT 기반 인증/인가
- 회원가입/로그인
- 초기 자본금 100만원 지급

### 2. 실시간 시장 데이터
- BTC, ETH, BNB, ADA 등 주요 코인 지원
- 실시간 가격 차트
- 24시간 변동률, 거래량 표시
- 
### Backend
- **FastAPI**: 웹 프레임워크
- **SQLModel**: ORM (SQLAlchemy + Pydantic)
- **SQLite**: 데이터베이스
- **JWT**: 인증
- **httpx**: Binance API 통신
- **WebSocket**: 실시간 데이터 스트리밍

### DevOps
- **Uvicorn**: ASGI 서버
- **Git**: 버전 관리

#### 인증
```
POST /api/v1/auth/register  # 회원가입
POST /api/v1/auth/login     # 로그인
```

#### 계정
```
GET  /api/v1/account/                # 계정 요약
GET  /api/v1/account/transactions    # 거래 내역
```

#### 주문
```
POST /api/v1/orders/   # 주문 생성
GET  /api/v1/orders/   # 주문 목록
```

#### 마켓
```
GET  /api/v1/market/coins                    # 모든 코인 정보
GET  /api/v1/market/coin/{symbol}            # 특정 코인 상세
GET  /api/v1/market/historical/{symbol}      # 과거 데이터
```

#### WebSocket
```
ws://localhost:8000/ws/realtime   # 실시간 가격 스트림

### User (사용자)
```sql
- id: INTEGER (PK)
- username: VARCHAR(50) UNIQUE
- hashed_password: VARCHAR(255)
- is_active: BOOLEAN
- created_at: DATETIME
```

### TradingAccount (거래 계정)
```sql
- id: INTEGER (PK)
- user_id: INTEGER (FK -> User)
- balance: DECIMAL(20,8)
- total_profit: DECIMAL(20,8)
```

### Order (주문)
```sql
- id: INTEGER (PK)
- user_id: INTEGER (FK -> User)
- symbol: VARCHAR(20)
- side: VARCHAR(10)  # BUY/SELL
- order_type: VARCHAR(10)  # MARKET/LIMIT
- order_status: VARCHAR(20)  # PENDING/FILLED/CANCELLED
- price: DECIMAL(20,8)
- quantity: DECIMAL(20,8)
- filled_quantity: DECIMAL(20,8)
- created_at: DATETIME
- updated_at: DATETIME
```

### Position (포지션)
```sql
- id: INTEGER (PK)
- account_id: INTEGER (FK -> TradingAccount)
- symbol: VARCHAR(20)
- quantity: DECIMAL(20,8)
- average_price: DECIMAL(20,8)
- current_value: DECIMAL(20,8)
- unrealized_profit: DECIMAL(20,8)
```

### TransactionHistory (거래 내역)
```sql
- id: INTEGER (PK)
- user_id: INTEGER (FK -> User)
- order_id: INTEGER (FK -> Order)
- symbol: VARCHAR(20)
- side: VARCHAR(10)
- quantity: DECIMAL(20,8)
- price: DECIMAL(20,8)
- fee: DECIMAL(20,8)
- timestamp: DATETIME
```

## 🔒 보안

### 구현된 보안 기능

1. **비밀번호 해싱**: bcrypt 사용
2. **JWT 토큰**: 액세스 토큰 기반 인증
3. **CORS 설정**: 허용된 오리진만 접근 가능
4. **입력 검증**: Pydantic을 통한 데이터 검증
5. **SQL Injection 방지**: ORM 사용
<div align="center">

**⭐ 이 프로젝트가 도움이 되었다면 스타를 눌러주세요!**

Made with ❤️ by BeenCoin Team

</div>
