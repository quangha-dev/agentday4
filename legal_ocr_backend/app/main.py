from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.rag_router import router as rag_router
from app.api.router import router
from app.core.config import get_settings
from app.core.database import init_database

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings.ensure_directories()
    init_database()
    yield


app = FastAPI(
    title=settings.app_name,
    version="2.0.0",
    description="OCR, legal structure extraction and semantic retrieval API",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router, prefix=settings.api_prefix)
app.include_router(rag_router, prefix=settings.api_prefix)
