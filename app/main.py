# app/main.py 파일을 열고 이렇게 수정하세요:

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from app.models.database import create_db_and_tables
from app.routers import auth, orders, account, websocket, market  # market은 그대로 둠
# from app.api.v1.endpoints import auth as v1_auth, orders as v1_orders, account as v1_account, market as v1_market  # 이 줄 주석 처리

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# v1 라우터 대신 기본 라우터 사용
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(orders.router, prefix=settings.API_V1_STR)
app.include_router(account.router, prefix=settings.API_V1_STR)
app.include_router(websocket.router, prefix=settings.API_V1_STR)
app.include_router(market.router, prefix=settings.API_V1_STR)

app.mount("/static", StaticFiles(directory="client/", html=True), name="static")

@app.on_event("startup")
async def startup_event():
    create_db_and_tables()

@app.get("/")
async def root():
    return {"message": "BeenCoin API 서버가 실행 중입니다!"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)