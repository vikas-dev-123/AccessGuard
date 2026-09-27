from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import models  # noqa: F401  (registers tables on Base.metadata)
from app.api import auth, reviews, uploads
from app.auth import seed_default_users
from app.db import Base, SessionLocal, engine
from app.settings import settings


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed_default_users(db)
    yield


app = FastAPI(
    title="AccessGuard API",
    description="ITGC User Access Review automation for banking.",
    version="0.3.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)
app.include_router(auth.router)
app.include_router(uploads.router)
app.include_router(reviews.router)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}
