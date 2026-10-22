from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from aeris import SAFETY_DISCLAIMER, __version__
from aeris.api import ask, health
from aeris.config import get_settings
from aeris.rag.errors import (
    ConfigError,
    IndexEmptyError,
    IndexMismatchError,
    RetrievalError,
    UnknownDocumentError,
)


def create_app() -> FastAPI:
    settings = get_settings()
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )

    app = FastAPI(
        title="AERIS API",
        version=__version__,
        description=f"Source-grounded aviation RAG. {SAFETY_DISCLAIMER}",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )
    app.include_router(health.router)
    app.include_router(ask.router)

    def handler(status: int, code: str):
        async def _handle(_: Request, exc: Exception) -> JSONResponse:
            return JSONResponse(status_code=status, content={"error": code, "detail": str(exc)})

        return _handle

    # Failures are explicit and typed (NFR: reliability), never a bare 500 traceback.
    app.add_exception_handler(IndexEmptyError, handler(503, "index_empty"))
    app.add_exception_handler(IndexMismatchError, handler(503, "index_mismatch"))
    app.add_exception_handler(ConfigError, handler(503, "misconfigured"))
    app.add_exception_handler(RetrievalError, handler(502, "retrieval_failed"))
    app.add_exception_handler(UnknownDocumentError, handler(422, "unknown_document"))
    app.add_exception_handler(ValueError, handler(422, "invalid_request"))
    return app


app = create_app()
