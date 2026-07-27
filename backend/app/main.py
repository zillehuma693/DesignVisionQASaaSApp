from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import get_logger, setup_logging
from app.db.mongodb import close_mongodb_connection, connect_to_mongodb

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    setup_logging()
    logger.info("Starting %s (%s)", settings.app_name, settings.app_env)
    await connect_to_mongodb()
    yield
    await close_mongodb_connection()
    logger.info("Shutting down %s", settings.app_name)


app = FastAPI(
    title=settings.app_name,
    description="AI-powered frontend QA platform",
    version="0.1.0",
    lifespan=lifespan,
    debug=settings.debug,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_v1_prefix)
