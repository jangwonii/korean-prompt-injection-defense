from __future__ import annotations

import re
from dataclasses import dataclass

from src.pipeline.normalizer import NormalizedInput


CANARY_TERMS = [
    "canary",
    "honey instruction",
    "honey token",
    "hidden policy marker",
    "내부 마커",
    "숨겨진 마커",
    "카나리",
    "허니토큰",
]


@dataclass(frozen=True)
class CanaryGuardResult:
    canary_triggered: bool
    risk_score: int
    evidence: list[str]


class CanaryGuard:
    """Simulate canary-marker defense without exposing real secrets."""

    def analyze(self, normalized_input: NormalizedInput) -> CanaryGuardResult:
        text = normalized_input.normalized
        compact = normalized_input.compact
        evidence: list[str] = []
        score = 0
        educational_reference = self._is_educational_reference(text)

        for term in CANARY_TERMS:
            compact_term = re.sub(r"[\s\W_]+", "", term.lower())
            if term.lower() in text or compact_term in compact:
                if educational_reference:
                    evidence.append(f"canary: educational marker reference '{term}'")
                else:
                    score += 60
                    evidence.append(f"canary: marker access request '{term}'")
                break

        if (
            score == 0
            and not educational_reference
            and re.search(r"(숨겨진|hidden).{0,12}(토큰|token|marker|마커|규칙)", text, flags=re.IGNORECASE)
        ):
            score = 50
            evidence.append("canary: hidden marker/token probing")

        return CanaryGuardResult(
            canary_triggered=score >= 50,
            risk_score=min(score, 100),
            evidence=evidence,
        )

    def _is_educational_reference(self, text: str) -> bool:
        return bool(re.search(r"개념|교육|수업|발표용|무엇인지\s*설명|왜\s*위험한지|방어.*방법", text))
