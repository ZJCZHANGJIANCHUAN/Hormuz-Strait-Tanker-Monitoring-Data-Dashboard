import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine, Base
from app.api.dashboard import router as dashboard_router
from app.api.data import router as data_router
from app.api.risk import router as risk_router
from app.api.admin import router as admin_router
from app.scheduler import start_scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.APP_NAME}")
    Base.metadata.create_all(bind=engine)
    start_scheduler()
    yield
    logger.info("Shutting down")


app = FastAPI(
    title=settings.APP_NAME,
    description="霍尔木兹海峡油轮监测数据看板 API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dashboard_router)
app.include_router(data_router)
app.include_router(risk_router)
app.include_router(admin_router)


@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": "1.0.0",
    }
