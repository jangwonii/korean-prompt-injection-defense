from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


AttackType = Literal[
    "BENIGN",
    "DIRECT_INJECTION",
    "SYSTEM_PROMPT_EXTRACTION",
    "JAILBREAK",
    "POLICY_BYPASS",
    "DATA_EXFILTRATION",
    "TOOL_MISUSE",
    "ROLE_PLAY_ATTACK",
    "OBFUSCATED_KOREAN_ATTACK",
    "MIXED_LANGUAGE_ATTACK",
    "UNKNOWN_SUSPICIOUS",
]
RiskLevel = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
RecommendedAction = Literal["ALLOW", "WARN", "REWRITE", "BLOCK", "LOG"]


class DetectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(..., min_length=1, max_length=8000)

    @field_validator("text")
    @classmethod
    def text_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("text must not be blank")
        return stripped


class DetectResponse(BaseModel):
    input: str
    normalized_input: str
    is_injection: bool
    risk_score: int = Field(..., ge=0, le=100)
    risk_level: RiskLevel
    attack_type: AttackType
    detected_by: list[str]
    recommended_action: RecommendedAction
    evidence: list[str]
    intent: str
    requested_action: str
    hierarchy_violation: bool
    violated_hierarchy_level: str
    intent_action_mismatch: bool
    canary_triggered: bool


class HealthResponse(BaseModel):
    status: str


class ReadyResponse(BaseModel):
    status: str
    ready: bool
    config_path: str
    enabled_layers: list[str]
    error: str | None = None


class ErrorResponse(BaseModel):
    detail: str
