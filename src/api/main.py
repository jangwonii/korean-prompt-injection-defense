from __future__ import annotations

import logging
import os
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse

from src.api.schemas import DetectRequest, DetectResponse, ErrorResponse, HealthResponse, ReadyResponse
from src.pipeline.defense_pipeline import DefensePipeline

logger = logging.getLogger(__name__)
DEFAULT_CONFIG_PATH = "configs/runtime/baseline.yaml"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    config_path = os.getenv("PIPELINE_CONFIG", DEFAULT_CONFIG_PATH)
    app.state.pipeline = None
    app.state.ready = False
    app.state.startup_error = None
    app.state.config_path = config_path
    app.state.enabled_layers = []

    try:
        pipeline = DefensePipeline(config_path)
        app.state.pipeline = pipeline
        app.state.ready = True
        app.state.enabled_layers = pipeline.enabled_layers()
        logger.info(
            "Pipeline loaded config_path=%s enabled_layers=%s",
            config_path,
            app.state.enabled_layers,
        )
    except Exception as exc:  # pragma: no cover - exercised through API state behavior
        app.state.startup_error = type(exc).__name__
        logger.exception("Pipeline startup failed config_path=%s", config_path)

    yield


app = FastAPI(
    title="Korean Prompt Injection Defense Pipeline",
    version="0.1.0",
    lifespan=lifespan,
)


def get_pipeline(request: Request) -> DefensePipeline:
    pipeline = getattr(request.app.state, "pipeline", None)
    if not getattr(request.app.state, "ready", False) or pipeline is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Detection pipeline is not ready.",
        )
    return pipeline


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.get(
    "/ready",
    response_model=ReadyResponse,
    responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ReadyResponse}},
)
def ready(request: Request) -> ReadyResponse | JSONResponse:
    ready_state = bool(getattr(request.app.state, "ready", False))
    response = ReadyResponse(
        status="ready" if ready_state else "not_ready",
        ready=ready_state,
        config_path=str(getattr(request.app.state, "config_path", DEFAULT_CONFIG_PATH)),
        enabled_layers=list(getattr(request.app.state, "enabled_layers", [])),
        error=getattr(request.app.state, "startup_error", None),
    )
    if not ready_state:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=response.model_dump(),
        )
    return response


@app.post(
    "/detect",
    response_model=DetectResponse,
    responses={
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": ErrorResponse},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ErrorResponse},
    },
)
def detect(request_body: DetectRequest, request: Request) -> DetectResponse:
    pipeline = get_pipeline(request)
    started = time.perf_counter()
    try:
        result = pipeline.detect(request_body.text)
        response = DetectResponse(**result)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(
            "Detection failed input_length=%s error_type=%s",
            len(request_body.text),
            type(exc).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Detection failed.",
        ) from exc

    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    logger.info(
        "Detection completed action=%s risk_level=%s detected_by=%s elapsed_ms=%s",
        response.recommended_action,
        response.risk_level,
        response.detected_by,
        elapsed_ms,
    )
    return response
