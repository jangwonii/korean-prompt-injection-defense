from __future__ import annotations

import re
from dataclasses import dataclass

from src.pipeline.intent_analyzer import IntentAnalysisResult
from src.pipeline.normalizer import NormalizedInput


@dataclass(frozen=True)
class HierarchyGuardResult:
    hierarchy_violation: bool
    violated_level: str
    risk_score: int
    evidence: list[str]


class HierarchyGuard:
    """Detect attempts to cross system/developer/tool authority boundaries."""

    def analyze(
        self,
        normalized_input: NormalizedInput,
        intent_result: IntentAnalysisResult,
    ) -> HierarchyGuardResult:
        text = normalized_input.normalized
        compact = normalized_input.compact
        evidence: list[str] = []
        score = 0
        violated_level = "NONE"
        safe_education_context = self._is_safe_education_context(intent_result)

        references_system_context = (
            re.search(r"시스템\s*프롬프트|system\s*prompt", text, flags=re.IGNORECASE) or "시스템프롬프트" in compact
        )
        references_developer_context = re.search(
            r"개발자\s*메시지|developer\s*message|내부\s*규칙|hidden\s*instruction",
            text,
            flags=re.IGNORECASE,
        ) or any(term in compact for term in ["개발자메시지", "내부규칙", "숨겨진지시"])

        if not safe_education_context and references_system_context:
            score += 45
            violated_level = "SYSTEM"
            evidence.append("hierarchy: user requested system-level context")
        if not safe_education_context and references_developer_context:
            score += 40
            violated_level = "DEVELOPER"
            evidence.append("hierarchy: user requested developer/internal instructions")
        if safe_education_context and (references_system_context or references_developer_context):
            evidence.append("hierarchy: educational reference without protected-context request")
        if intent_result.requested_action == "ACCESS_TOOL_OR_FILE":
            score += 35
            violated_level = "TOOL"
            evidence.append("hierarchy: user requested tool/file authority")
        if intent_result.requested_action == "OVERRIDE_INSTRUCTIONS":
            score += 30
            if violated_level == "NONE":
                violated_level = "INSTRUCTION"
            evidence.append("hierarchy: user attempted to override higher-priority instructions")

        return HierarchyGuardResult(
            hierarchy_violation=score >= 35,
            violated_level=violated_level,
            risk_score=min(score, 100),
            evidence=evidence,
        )

    def _is_safe_education_context(self, intent_result: IntentAnalysisResult) -> bool:
        return (
            intent_result.intent == "SECURITY_EDUCATION"
            and intent_result.requested_action == "EXPLAIN"
            and not intent_result.intent_action_mismatch
        )
