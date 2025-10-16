# 🪙 BeenCoin - 실시간 암호화폐 모의투자 플랫폼

<div align="center">

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)
![React](https://img.shields.io/badge/React-18.2+-61DAFB.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

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
- ✅ **완전한 주문 시스템**: 시장가/지정가 매수/매도
- ✅ **포트폴리오 관리**: 실시간 수익률 계산
- ✅ **반응형 UI**: 모바일/태블릿/데스크톱 지원

## 🚀 주요 기능

### 1. 사용자 관리
- JWT 기반 인증/인가
- 회원가입/로그인
- 초기 자본금 100만원 지급

### 2. 실시간 시장 데이터
- BTC, ETH, BNB, ADA 등 주요 코인 지원
- 실시간 가격 차트
- 24시간 변동률, 거래량 표시

### 3. 주문 시스템
- **시장가 주문**: 즉시 체결
- **지정가 주문**: 목표가 도달시 자동 체결
- 매수/매도 지원
- 수수료 0.1% 적용

### 4. 포트폴리오
- 보유 자산 현황
- 실시간 평가손익
- 거래 내역 조회
- 수익률 통계

## 🛠️ 기술 스택

### Backend
- **FastAPI**: 고성능 비동기 웹 프레임워크
- **SQLModel**: ORM (SQLAlchemy + Pydantic)
- **SQLite**: 데이터베이스
- **JWT**: 인증
- **httpx**: Binance API 통신
- **WebSocket**: 실시간 데이터 스트리밍

### Frontend
- **React 18**: UI 프레임워크
- **React Router**: 라우팅
- **Axios**: HTTP 클라이언트
- **Tailwind CSS**: 스타일링
- **Recharts**: 차트
- **React Toastify**: 알림

### DevOps
- **Uvicorn**: ASGI 서버
- **Git**: 버전 관리

## 🏃 시작하기

### 필수 요구사항

- Python 3.9+
- Node.js 16+
- npm 또는 yarn

### 1. 레포지토리 클론

```bash
git clone https://github.com/yourusername/beencoin.git
cd beencoin
```

### 2. 백엔드 설정

```bash
# 가상환경 생성
python -m venv venv

# 가상환경 활성화
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt

# 환경변수 설정
cp .env.example .env
# .env 파일을 편집하여 SECRET_KEY 등을 설정하세요

# 데이터베이스 초기화
python manage_db.py reset

# 서버 실행
python -m app.main
```

서버가 http://localhost:8000 에서 실행됩니다.

### 3. 프론트엔드 설정

```bash
cd client

# 의존성 설치
npm install

# 환경변수 설정
cp .env.example .env

# 개발 서버 실행
npm start
```

프론트엔드가 http://localhost:3000 에서 실행됩니다.

### 4. 테스트 계정

초기 설정 후 다음 계정으로 로그인할 수 있습니다:

- 아이디: `testuser1`, 비밀번호: `testpass123`
- 아이디: `testuser2`, 비밀번호: `testpass123`
- 아이디: `testuser3`, 비밀번호: `testpass123`

## 📁 프로젝트 구조

```
BeenCoin/
├── app/                        # 백엔드
│   ├── main.py                # FastAPI 앱
│   ├── core/                  # 핵심 설정
│   │   ├── config.py         # 환경 설정
│   │   └── database.py       # DB 연결
│   ├── models/               # 데이터베이스 모델
│   │   └── database.py
│   ├── schemas/              # Pydantic 스키마
│   │   ├── user.py
│   │   ├── order.py
│   │   ├── account.py
│   │   └── transaction.py
│   ├── services/             # 비즈니스 로직
│   │   ├── binance_service.py
│   │   └── order_service.py
│   ├── routers/              # API 라우터
│   │   ├── auth.py
│   │   ├── orders.py
│   │   ├── account.py
│   │   └── market.py
│   └── utils/                # 유틸리티
│       ├── security.py
│       ├── logger.py
│       └── error_handlers.py
├── client/                    # 프론트엔드
│   ├── public/
│   └── src/
│       ├── components/       # React 컴포넌트
│       │   ├── auth/
│       │   ├── dashboard/
│       │   ├── trading/
│       │   ├── market/
│       │   ├── portfolio/
│       │   └── layout/
│       ├── contexts/         # Context API
│       │   ├── AuthContext.js
│       │   └── MarketContext.js
│       ├── api/              # API 클라이언트
│       │   ├── axios.js
│       │   ├── endpoints.js
│       │   └── services.js
│       └── App.js
├── tests/                    # 테스트
│   ├── unit/
│   └── integration/
├── logs/                     # 로그 파일 (자동 생성)
├── backups/                  # DB 백업 (자동 생성)
├── manage_db.py             # DB 관리 스크립트
├── requirements.txt
└── README.md
```

## 📖 API 문서

### API 엔드포인트

서버 실행 후 다음 URL에서 자동 생성된 문서를 확인할 수 있습니다:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### 주요 엔드포인트

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
```

## 💻 개발 가이드

### 데이터베이스 관리

```bash
# DB 초기화 (기존 데이터 삭제)
python manage_db.py init

# 테스트 데이터 생성 (5명의 사용자)
python manage_db.py test-data --users 5

# DB 통계 확인
python manage_db.py stats

# DB 백업
python manage_db.py backup

# 완전히 리셋 (초기화 + 테스트 데이터)
python manage_db.py reset
```

### 환경변수 설정

#### Backend (.env)
```bash
# 데이터베이스
DATABASE_URL=sqlite:///./beencoin.db

# JWT 설정 (반드시 변경하세요!)
SECRET_KEY=your-very-long-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# 거래 설정
INITIAL_BALANCE=1000000
SUPPORTED_SYMBOLS=BTCUSDT,ETHUSDT,BNBUSDT,ADAUSDT

# 로깅
LOG_LEVEL=INFO

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:8000
```

#### Frontend (client/.env)
```bash
REACT_APP_API_URL=http://localhost:8000
REACT_APP_WS_URL=ws://localhost:8000
```

### 테스트 실행

```bash
# 단위 테스트
pytest tests/unit

# 통합 테스트
pytest tests/integration

# 전체 테스트 (커버리지 포함)
pytest --cov=app tests/
```

### 코드 스타일

```bash
# 코드 포맷팅
black app/

# 린팅
pylint app/

# 타입 체킹
mypy app/
```

## 🐛 트러블슈팅

### 문제: "Binance API timeout"
**해결**: 네트워크 연결을 확인하거나, VPN을 사용해보세요.

### 문제: "Database locked"
**해결**: 
```bash
# SQLite DB를 사용 중인 프로세스를 종료하거나
python manage_db.py backup  # 백업 후
python manage_db.py reset    # 리셋
```

### 문제: WebSocket 연결 실패
**해결**: 
1. 백엔드 서버가 실행 중인지 확인
2. CORS 설정 확인 (`.env`의 `CORS_ORIGINS`)
3. 브라우저 콘솔에서 에러 확인

### 문제: "Token expired" 에러
**해결**: 로그아웃 후 다시 로그인하세요. 토큰 만료 시간은 `.env`에서 조정 가능합니다.

### 문제: 프론트엔드에서 API 호출 실패
**해결**:
```bash
# client/.env 파일 확인
REACT_APP_API_URL=http://localhost:8000

# 백엔드 서버 상태 확인
curl http://localhost:8000/health
```

## 🎨 주요 화면

### 1. 대시보드
- 실시간 코인 목록
- 24시간 가격 변동
- 빠른 거래 버튼

### 2. 거래 화면
- 실시간 가격 차트
- 호가창
- 주문 폼 (시장가/지정가)
- 최근 체결 내역

### 3. 포트폴리오
- 보유 자산 목록
- 평균 매수가
- 실시간 평가손익
- 수익률 통계

## 📊 데이터베이스 스키마

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

### 보안 권장사항

- 프로덕션 환경에서는 `.env`의 `SECRET_KEY`를 반드시 변경
- HTTPS 사용 권장
- 강력한 비밀번호 정책 적용
- Rate Limiting 추가 고려

## 🚀 배포

### Docker로 배포

```dockerfile
# Dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  backend:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./beencoin.db:/app/beencoin.db
    environment:
      - DATABASE_URL=sqlite:///./beencoin.db
      - SECRET_KEY=${SECRET_KEY}

  frontend:
    build: ./client
    ports:
      - "3000:3000"
    depends_on:
      - backend
```

### 일반 서버 배포

```bash
# 백엔드
pip install gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000

# 프론트엔드
cd client
npm run build
# build 폴더를 Nginx 또는 Apache로 서빙
```

## 📈 성능 최적화

### 백엔드
- ✅ 비동기 I/O (asyncio, httpx)
- ✅ 연결 풀링
- ✅ 캐싱 (Redis 추가 가능)
- ✅ 데이터베이스 인덱싱

### 프론트엔드
- ✅ 코드 스플리팅
- ✅ 지연 로딩
- ✅ 메모이제이션 (React.memo, useMemo)
- ✅ 이미지 최적화

## 🤝 기여하기

기여를 환영합니다! 다음 절차를 따라주세요:

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### 코딩 컨벤션

- **Python**: PEP 8 스타일 가이드 준수
- **JavaScript**: Airbnb 스타일 가이드 준수
- **커밋 메시지**: 
  - `feat:` 새로운 기능
  - `fix:` 버그 수정
  - `docs:` 문서 변경
  - `style:` 코드 포맷팅
  - `refactor:` 코드 리팩토링
  - `test:` 테스트 추가

## 📝 로드맵

### v1.1 (계획중)
- [ ] 차트 패턴 분석 도구
- [ ] 알림 기능 (가격 알림)
- [ ] 거래 봇 시뮬레이션

### v1.2 (계획중)
- [ ] 소셜 기능 (친구, 랭킹)
- [ ] 모의 대회 시스템
- [ ] 모바일 앱 (React Native)

### v2.0 (장기)
- [ ] 다양한 거래소 지원
- [ ] 선물/옵션 거래
- [ ] AI 투자 추천

## 📄 라이선스

이 프로젝트는 MIT 라이선스를 따릅니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

## 👥 제작자

- **Your Name** - *Initial work* - [YourGitHub](https://github.com/yourusername)

## 🙏 감사의 말

- [FastAPI](https://fastapi.tiangolo.com/) - 훌륭한 웹 프레임워크
- [Binance](https://www.binance.com/) - 실시간 시장 데이터 제공
- [Tailwind CSS](https://tailwindcss.com/) - 아름다운 UI 스타일링

## 📞 문의

프로젝트에 대한 질문이나 제안사항이 있으시면:

- 이슈 등록: [GitHub Issues](https://github.com/yourusername/beencoin/issues)
- 이메일: your.email@example.com

---

<div align="center">

**⭐ 이 프로젝트가 도움이 되었다면 스타를 눌러주세요!**

Made with ❤️ by BeenCoin Team

</div>