# BeenCoin - 실시간 암호화폐 모의투자 플랫폼

## 🚀 주요 기능
- 실시간 암호화폐 시세 조회 (Binance API)
- 모의투자 주문 시스템
- WebSocket 실시간 데이터 스트리밍
- 포트폴리오 관리

## ⚡ 빠른 시작
```bash
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
│   ├── api/v1/        # API 엔드포인트
│   ├── services/      # 비즈니스 로직
│   └── utils/         # 유틸리티
├── tests/
└── requirements.txt
```
