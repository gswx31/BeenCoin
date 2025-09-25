# BeenCoin - 실시간 암호화폐 모의투자 플랫폼

## 🚀 주요 기능
- 회원가입/로그인 (아이디/비밀번호 기반)
- 실시간 암호화폐 시세 조회 (Binance API)
- 모의투자 주문 시스템 (시장가/지정가, 매수/매도)
- 실제 시장 데이터 기반 주문 실행 (지정가 주문은 WebSocket 모니터링)
- 포트폴리오 관리 및 수익률 표시
- WebSocket 실시간 데이터 스트리밍

## ⚡ 빠른 시작
1. 환경 변수 설정: .env 파일 생성 (.env.example 참조)
2. ```bash
   pip install -r requirements.txt
   uvicorn app.main:app --reload
   ```

## 📊 API 문서
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 🏗️ 프로젝트 구조
```
BeenCoin/
├── app/
│   ├── main.py
│   ├── core/          # 설정 관리
│   ├── models/        # 데이터베이스 모델
│   ├── schemas/       # Pydantic 스키마
│   ├── routers/       # API 라우터
│   ├── services/      # 비즈니스 로직 (Binance, Order 처리)
│   ├── utils/         # 유틸리티 (보안 등)
│   ├── api/v1/        # API 엔드포인트 (미사용 시 삭제 가능)
│   └── __init__.py
├── tests/
├── .env.example
└── requirements.txt
```

## 📝 추가 설명
- 회원가입: POST /api/v1/auth/register {username, password}
- 로그인: POST /api/v1/auth/login {username, password} → JWT 토큰 반환
- 주문: POST /api/v1/orders {symbol, side, order_type, quantity, price?} (Authorization: Bearer <token>)
- 계좌 조회: GET /api/v1/account (Authorization: Bearer <token>) → balance, total_profit, positions, profit_rate
- 주문 처리: 시장가는 즉시 실행, 지정가는 WebSocket으로 가격 모니터링 후 실행.
- 수익률: (현재 총 가치 - 초기 잔고) / 초기 잔고 * 100
