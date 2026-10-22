from __future__ import annotations

from fastapi import APIRouter, Depends

from aeris import SAFETY_DISCLAIMER, __version__
from aeris.config import Settings, get_settings
from aeris.schemas import HealthResponse

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse, summary="Liveness check")
def health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    return HealthResponse(
        version=__version__,
        environment=settings.app_env,
        llm_provider=settings.llm_provider,
        embedding_provider=settings.embedding_provider,
        disclaimer=SAFETY_DISCLAIMER,
    )
