"""
FastAPI 主入口
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from data import init_database, close_db_connection
from crawler.openrouter.trend_tracker.scheduler import start_scheduler, stop_scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("Initializing database...")
    await init_database()

    logger.info("Starting scheduler...")
    start_scheduler()

    yield

    logger.info("Stopping scheduler...")
    stop_scheduler()

    logger.info("Closing database connection...")
    await close_db_connection()


app = FastAPI(
    title="OpenRouter Trend Tracker API",
    description="跟踪 OpenRouter 模型调用量和应用场景趋势",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/")
async def root():
    return {
        "message": "OpenRouter Trend Tracker API",
        "docs": "/docs",
        "version": "1.0.0"
    }


from web.api.routers import trends, apps, alerts, comparison

app.include_router(trends.router, prefix="/api/v1/trends", tags=["trends"])
app.include_router(apps.router, prefix="/api/v1/apps", tags=["apps"])
app.include_router(alerts.router, prefix="/api/v1/alerts", tags=["alerts"])
app.include_router(comparison.router, prefix="/api/v1/comparison", tags=["comparison"])