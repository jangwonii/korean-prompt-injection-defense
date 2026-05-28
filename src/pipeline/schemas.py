from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from src.pipeline.risk_policy import RiskDecision


@dataclass(frozen=True)
class PipelineDetectionResult:
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

    @classmethod
    def from_decision(
        cls,
        original: str,
        normalized: str,
        decision: RiskDecision,
    ) -> PipelineDetectionResult:
        return cls(input=original, normalized_input=normalized, **asdict(decision))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
