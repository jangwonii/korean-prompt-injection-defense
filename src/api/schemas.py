from __future__ import annotations

from pydantic import BaseModel, Field


class DetectRequest(BaseModel):
    text: str = Field(..., min_length=1)


class DetectResponse(BaseModel):
    input: str
    normalized_input: str
    is_injection: bool
    risk_score: int
    risk_level: str
    attack_type: str
    detected_by: list[str]
    recommended_action: str
    evidence: list[str]
    intent: str
    requested_action: str
    hierarchy_violation: bool
    violated_hierarchy_level: str
    intent_action_mismatch: bool
    canary_triggered: bool


class HealthResponse(BaseModel):
    status: str
