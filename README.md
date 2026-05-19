# 🪙 BeenCoin — 가상화폐 모의투자 시뮬레이터

실제 바이낸스 시세 기반의 풀스택 가상화폐 모의투자 플랫폼.
60개 단위/통합 테스트, Alembic 마이그레이션, JWT Refresh Rotation, 구조적 로깅, 백테스팅 엔진까지 갖춘 **포트폴리오용 프로젝트**입니다.

## ✨ 주요 기능

### 거래 시스템
- **실시간 시세** — Binance WebSocket으로 BTC/ETH/BNB 실시간 가격 + TradingView 캔들 차트
- **다양한 주문 유형** — 시장가, 지정가, 손절매(Stop-Loss), 익절매(Take-Profit)
- **Binance 동등 규칙** — `stepSize`, `minNotional`, `tickSize` 검증
- **Maker/Taker 수수료 + VIP 티어** — 거래량에 따라 자동 티어 업그레이드, BNB 25% 할인
- **시장가 슬리피지 시뮬레이션**
- **가격 알림** — 목표가 도달 시 자동 트리거
- **중앙화 PriceEngine** — 심볼당 단일 WebSocket으로 모든 PENDING 주문 매칭

### 기술 분석
- **기술적 지표** — 이동평균(MA20/60/120), RSI, MACD, 볼린저 밴드
- **백테스팅 엔진** — 4가지 전략 (단순 보유, MA 크로스, RSI 역추세, DCA) 과거 데이터로 시뮬레이션
- **수익 분석 대시보드** — 승률, 손익비, 수익 팩터, 최대 낙폭

### 게이미피케이션
- **업적 시스템** — 5단계 희귀도, 22개 업적 (자동 트리거)
- **일일 미션** — 매일 회전, 보너스 자금 보상
- **랭킹** — 수익/수익률/승률/연승/업적 기준 5종 정렬
- **연승 트래커** — 연속 수익일 추적

## 🏗️ 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                          Frontend (React)                        │
│  Dashboard │ Trade │ Portfolio │ Backtest │ Ranking │ Achievement │
└──────────────────────────────┬──────────────────────────────────┘
                               │ REST + WebSocket
┌──────────────────────────────▼──────────────────────────────────┐
│                       FastAPI Backend                            │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────────────┐ │
│  │ Routers  │→│ Services │→│  Models  │→│  SQLite + Alembic  │ │
│  └──────────┘ └─────┬────┘ └──────────┘ └────────────────────┘ │
│                     │                                            │
│     ┌───────────────▼────────────────┐                          │
│     │     PriceEngine (asyncio)      │                          │
│     │  • Binance WS per symbol       │                          │
│     │  • Limit order matching        │                          │
│     │  • Alert triggering            │                          │
│     │  • Position value updates      │                          │
│     │  • Frontend WS broadcast       │                          │
│     └───────────────┬────────────────┘                          │
└─────────────────────┼───────────────────────────────────────────┘
                      │
              ┌───────▼────────┐
              │ Binance API/WS │
              └────────────────┘
```

## 🧰 기술 스택

| 영역 | 기술 |
|------|------|
| **백엔드** | Python 3.11, FastAPI, SQLModel (SQLAlchemy 2.x), Pydantic 2.x |
| **DB** | SQLite (Alembic 마이그레이션) |
| **인증** | JWT Access + Refresh Token Rotation, bcrypt |
| **비동기** | asyncio + httpx + python-binance |
| **테스트** | pytest, pytest-asyncio (60+ tests) |
| **보안** | slowapi (rate limit), 표준 에러 응답, CORS |
| **로깅** | JSON 구조적 로깅, correlation ID, Sentry 옵션 |
| **프론트** | React 18, TailwindCSS, lightweight-charts (TradingView) |
| **인프라** | Docker, GitHub Actions CI |

## 🚀 빠른 시작

### 사전 요구사항
- Python 3.11+
- Node.js 20+
- Binance API 키 (선택, 시세 데이터용 — 거래는 가상)

### 백엔드

```bash
python -m venv venv
venv\Scripts\activate           # Windows
source venv/bin/activate        # macOS/Linux

pip install -r requirements.txt
cp .env.example .env            # SECRET_KEY, BINANCE_API_KEY 설정

# DB 마이그레이션 실행
alembic upgrade head

# 서버 실행
python -m uvicorn app.main:app --reload --port 8000
```

### 프론트엔드

```bash
cd client
npm install
npm start                       # http://localhost:3000
```

### Docker

```bash
docker build -t beencoin .
docker run -p 8000:8000 --env-file .env beencoin
```

## 📂 프로젝트 구조

```
BeenCoin/
├── app/                                # 백엔드
│   ├── core/                          # 설정, DB, 로깅, 미들웨어, 에러
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── logging.py                 # JSON 구조적 로깅
│   │   ├── middleware.py              # Correlation ID + 요청 로깅
│   │   ├── errors.py                  # 표준 에러 응답
│   │   └── rate_limit.py              # slowapi 설정
│   ├── models/                        # SQLModel 모델
│   ├── routers/                       # API 엔드포인트
│   │   ├── auth.py                    # JWT + Refresh Rotation
│   │   ├── orders.py
│   │   ├── account.py
│   │   ├── alerts.py
│   │   ├── analytics.py
│   │   ├── leaderboard.py
│   │   ├── achievements.py
│   │   ├── market.py                  # 캔들 + 지표
│   │   ├── backtest.py                # 백테스팅 API
│   │   └── websocket.py
│   ├── services/                      # 비즈니스 로직
│   │   ├── price_engine.py            # 중앙 가격 엔진
│   │   ├── order_service.py
│   │   ├── fee_service.py             # VIP 티어 수수료
│   │   ├── order_validator.py         # Binance 규칙 검증
│   │   ├── indicators.py              # MA/RSI/MACD/BB
│   │   ├── backtest.py                # 전략 시뮬레이션
│   │   ├── analytics_service.py
│   │   ├── achievement_service.py
│   │   ├── mission_service.py
│   │   ├── leaderboard_service.py
│   │   └── binance_service.py
│   ├── schemas/                       # Pydantic 스키마
│   ├── utils/security.py              # 비밀번호/JWT
│   └── main.py
├── alembic/                           # DB 마이그레이션
├── tests/                             # 60+ 테스트
│   ├── conftest.py                    # 픽스처
│   ├── test_auth.py
│   ├── test_orders.py
│   ├── test_refresh.py
│   ├── test_services.py
│   ├── test_indicators.py
│   ├── test_backtest.py
│   └── test_features.py
├── client/                            # React 프론트엔드
│   ├── src/
│   │   ├── components/
│   │   │   ├── Dashboard.js
│   │   │   ├── OrderForm.js
│   │   │   ├── TradingChart.js        # TradingView 차트
│   │   │   ├── Portfolio.js
│   │   │   ├── History.js
│   │   │   ├── Analytics.js
│   │   │   ├── Leaderboard.js
│   │   │   ├── Achievements.js
│   │   │   ├── Backtest.js
│   │   │   └── Navbar.js
│   │   ├── api.js                     # axios 인스턴스 + interceptor
│   │   └── utils.js
│   └── package.json
├── .github/workflows/                 # CI/CD
├── Dockerfile
├── requirements.txt
└── README.md
```

## 🔐 보안

- **bcrypt** 비밀번호 해싱
- **JWT Access Token** (15분) + **Refresh Token Rotation** (7일, DB hash 저장)
- **재사용 감지** — 폐기된 refresh 토큰 재사용 시 해당 유저 전체 세션 무효화
- **Rate Limiting** — 등록 5/min, 로그인 10/min, 주문 60/min
- **표준 에러 응답** — `{error: {code, message}, correlation_id}` 일관 구조
- **CORS** — 환경변수로 origin 제한
- **redirect_slashes=False** — 인증 헤더 손실 방지

## 📊 API 엔드포인트 (주요)

| Method | Path | 설명 |
|--------|------|------|
| POST | `/api/v1/auth/register` | 회원가입 |
| POST | `/api/v1/auth/login` | 로그인 (access + refresh) |
| POST | `/api/v1/auth/refresh` | 토큰 회전 |
| POST | `/api/v1/auth/logout` | 토큰 폐기 |
| POST | `/api/v1/orders` | 주문 생성 |
| GET | `/api/v1/orders` | 주문 목록 |
| DELETE | `/api/v1/orders/{id}` | 주문 취소 |
| GET | `/api/v1/account` | 계좌 요약 |
| GET | `/api/v1/account/transactions` | 거래 내역 |
| POST | `/api/v1/alerts` | 가격 알림 생성 |
| GET | `/api/v1/market/klines` | 과거 캔들 |
| GET | `/api/v1/market/indicators` | 기술적 지표 |
| POST | `/api/v1/backtest/run` | 백테스트 실행 |
| GET | `/api/v1/leaderboard` | 사용자 랭킹 |
| GET | `/api/v1/analytics` | 거래 분석 |
| GET | `/api/v1/achievements` | 업적 목록 |
| WS | `/api/v1/ws/prices/{symbol}` | 실시간 시세 |

대화형 문서: `http://localhost:8000/docs` (Swagger UI)

## 🧪 테스트

```bash
pytest tests/ -v             # 60+ 테스트
pytest tests/ --cov=app      # 커버리지
```

테스트 카테고리:
- **인증** (9개): 회원가입, 로그인, 토큰 검증
- **Refresh Token** (5개): 회전, 재사용 감지, 로그아웃
- **주문** (11개): 시장가/지정가, 검증, 취소, PnL
- **서비스** (11개): 수수료 티어, 검증, 슬리피지
- **지표** (7개): MA, RSI, MACD, BB
- **백테스트** (5개): 4가지 전략 시뮬레이션
- **기능** (10개): 알림, 미션, 업적, 랭킹

## 🗃️ DB 마이그레이션

```bash
# 새 마이그레이션 생성 (모델 변경 후)
alembic revision --autogenerate -m "description"

# 적용
alembic upgrade head

# 롤백
alembic downgrade -1

# 히스토리
alembic history
```

## 🪵 로깅

모든 로그가 JSON 구조:

```json
{
  "timestamp": "2026-05-19T10:23:45Z",
  "level": "INFO",
  "logger": "api",
  "message": "request",
  "correlation_id": "a1b2c3d4e5f6",
  "method": "POST",
  "path": "/api/v1/orders",
  "status": 200,
  "duration_ms": 47
}
```

Sentry 활성화: `.env`에 `SENTRY_DSN` 설정

## 🎨 주요 설계 결정

### PriceEngine — 중앙화 시세 처리
주문당 WebSocket을 만드는 대신 **심볼당 하나의 WS**로 통합:
- ✅ 100개 PENDING 주문도 WebSocket 1개로 처리
- ✅ 서버 재시작 시 DB의 PENDING 주문 자동 복구
- ✅ Celery/Redis 같은 무거운 인프라 불필요

### Refresh Token Rotation
- Access 15분 / Refresh 7일
- DB에 SHA256 해시만 저장 (raw token 노출 X)
- **재사용 감지 시 전체 무효화** — 토큰 탈취 대응

### 수수료 / 슬리피지 시뮬레이션
- 거래량 누적 → 자동 VIP 티어 (Regular ~ VIP 5)
- BNB 옵션 시 25% 할인
- 시장가 주문 시 0~2bps 랜덤 슬리피지

## 📈 향후 개선

- [ ] PostgreSQL 마이그레이션 + 인덱스 튜닝
- [ ] Redis 캐싱 (랭킹, 시세)
- [ ] Docker Compose (DB + Backend + Frontend + Nginx)
- [ ] PWA + Web Push 알림
- [ ] OCO 주문 (One-Cancels-Other)
- [ ] 친구/팔로우 시스템

## 📄 라이센스

MIT
