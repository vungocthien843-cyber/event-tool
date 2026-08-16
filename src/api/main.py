from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.core.config import settings
from src.core.database import init_db
from src.api.routes import router
from arq import create_pool
from src.worker.main import redis_settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Khởi tạo bảng Database
    await init_db()
    # Khởi tạo kết nối Redis cho Hàng đợi (Queue)
    app.state.redis = await create_pool(redis_settings)
    yield
    # Đóng kết nối khi app tắt
    await app.state.redis.close()

app = FastAPI(title="IDP Webhook Test", lifespan=lifespan)

if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(router)

@app.get("/health")
async def health():
    return {"status": "ok"}
