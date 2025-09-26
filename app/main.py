from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from app.models.database import create_db_and_tables
from app.routers import auth, orders, account, websocket
from app.background_tasks.celery_app import celery_app
from app.background_tasks.tasks import update_all_positions

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

app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(orders.router, prefix=settings.API_V1_STR)
app.include_router(account.router, prefix=settings.API_V1_STR)
app.include_router(websocket.router, prefix=settings.API_V1_STR)

app.mount("/static", StaticFiles(directory="client/build", html=True), name="static")

@app.on_event("startup")
async def startup_event():
    create_db_and_tables()
    celery_app.conf.beat_schedule = {
        'update-positions-every-5-minutes': {
            'task': 'app.background_tasks.tasks.update_all_positions',
            'schedule': 300.0,
        },
    }

@app.get("/")
async def root():
    return {"message": "BeenCoin API 서버가 실행 중입니다!"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
