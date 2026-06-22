from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel

from stoker_server import __version__
from stoker_server.config import Settings

settings = Settings()


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # learn: lifespan — setup до yield, teardown после. Здесь появятся инициализация
    # БД (SQLite/SQLModel) и WS-хаба в будущих вехах. Пока пусто.
    yield


app = FastAPI(title="Stoker Server", version=__version__, lifespan=lifespan)


@app.get("/healthz")
async def healthz() -> HealthResponse:
    return HealthResponse(status="ok", service=settings.service_name, version=__version__)
