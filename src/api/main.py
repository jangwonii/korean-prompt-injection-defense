from __future__ import annotations

import os

from fastapi import FastAPI

from src.api.schemas import DetectRequest, DetectResponse, HealthResponse
from src.pipeline.defense_pipeline import DefensePipeline


app = FastAPI(
    title="Korean Prompt Injection Defense Pipeline",
    version="0.1.0",
)

pipeline = DefensePipeline(os.getenv("PIPELINE_CONFIG", "configs/runtime/baseline.yaml"))


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.post("/detect", response_model=DetectResponse)
def detect(request: DetectRequest) -> DetectResponse:
    return DetectResponse(**pipeline.detect(request.text))
