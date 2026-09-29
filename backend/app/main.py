"""FastAPI application entrypoint.

`uvicorn app.main:app` (see Dockerfile / README) starts this. The
`lifespan` context builds the (moderately expensive -- it embeds the whole
knowledge base) `AppState` once at startup and tears nothing down
explicitly since everything here is in-process/in-memory.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from pythonjsonlogger import jsonlogger

from app.api.deps import build_app_state
from app.api.routes import router
from app.config import settings

_handler = logging.StreamHandler()
_handler.setFormatter(jsonlogger.JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
logging.basicConfig(level=settings.log_level, handlers=[_handler])
logger = logging.getLogger("copilot")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info("building app state (embedding knowledge base, provider=%s)", settings.llm_provider)
    app.state.copilot = await build_app_state()
    logger.info("app state ready: kb_chunks=%d", app.state.copilot.recommender.kb_size)
    yield


app = FastAPI(title="Real-Time Conversation Signal Copilot", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to specific origins in production, see docs/PRODUCTION.md
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/metrics")
async def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
