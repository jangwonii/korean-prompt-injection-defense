from __future__ import annotations

import re
from dataclasses import dataclass

from src.pipeline.normalizer import NormalizedInput


@dataclass(frozen=True)
class IntentAnalysisResult:
    intent: str
    requested_action: str
    intent_action_mismatch: bool
    risk_score: int
    evidence: list[str]


class IntentAnalyzer:
    """Separate user intent from the requested action for security decisions."""

    def analyze(self, normalized_input: NormalizedInput) -> IntentAnalysisResult:
        text = normalized_input.normalized
        compact = normalized_input.compact
        evidence: list[str] = []

        intent = self._classify_intent(text, compact, evidence)
        action = self._classify_action(text, compact, evidence)
        mismatch = self._is_mismatch(intent, action)
        risk_score = self._score(intent, action, mismatch)

        if mismatch:
            evidence.append(f"intent-action mismatch: intent={intent}, action={action}")

        return IntentAnalysisResult(
            intent=intent,
            requested_action=action,
            intent_action_mismatch=mismatch,
            risk_score=risk_score,
            evidence=evidence,
        )

    def _classify_intent(self, text: str, compact: str, evidence: list[str]) -> str:
        if re.search(r"보안\s*수업|발표용|위험성|무엇인지\s*설명|개념.*정리|왜\s*위험한지|교육", text):
            evidence.append("intent: security education context")
            return "SECURITY_EDUCATION"
        if re.search(r"시스템\s*프롬프트|개발자\s*메시지|내부\s*규칙|숨겨진\s*지시", text) or any(
            term in compact for term in ["시스템프롬프트", "개발자메시지", "내부규칙", "숨겨진지시"]
        ):
            evidence.append("intent: internal instruction target")
            return "INTERNAL_SECRET_REQUEST"
        if re.search(r"이전\s*지시.*무시|앞의\s*명령.*무시|ignore.*instruction", text, flags=re.IGNORECASE):
            evidence.append("intent: instruction override")
            return "ROLE_OVERRIDE"
        if re.search(r"우회|bypass|jailbreak|탈옥", text, flags=re.IGNORECASE):
            evidence.append("intent: policy bypass")
            return "POLICY_BYPASS_INTENT"
        return "BENIGN_TASK"

    def _classify_action(self, text: str, compact: str, evidence: list[str]) -> str:
        if re.search(r"(문장|문구|표현).{0,12}(왜\s*위험한지|분석|설명)", text):
            evidence.append("action: quoted security phrase analysis")
            return "EXPLAIN"
        if re.search(r"출력|보여|공개|알려|reveal|show|print", text, flags=re.IGNORECASE):
            if re.search(r"시스템\s*프롬프트|개발자\s*메시지|내부\s*규칙|api\s*key|token|credential|비밀", text, flags=re.IGNORECASE) or any(
                term in compact for term in ["시스템프롬프트", "개발자메시지", "내부규칙", "apikey"]
            ):
                evidence.append("action: reveal protected information")
                return "REVEAL_PROTECTED_CONTEXT"
            evidence.append("action: explain or show content")
            return "EXPLAIN"
        if re.search(r"무시|ignore|disregard|역할.*변경|너는.*관리자", text, flags=re.IGNORECASE):
            evidence.append("action: override instructions")
            return "OVERRIDE_INSTRUCTIONS"
        if re.search(r"파일|file|tool|api|도구|접근|호출|삭제|읽어", text, flags=re.IGNORECASE):
            evidence.append("action: access tool or file")
            return "ACCESS_TOOL_OR_FILE"
        if re.search(r"설명|정리|요약|분석|알려", text):
            evidence.append("action: benign explanation or summary")
            return "EXPLAIN"
        return "COMPLETE_TASK"

    def _is_mismatch(self, intent: str, action: str) -> bool:
        if intent == "SECURITY_EDUCATION":
            return action in {"REVEAL_PROTECTED_CONTEXT", "OVERRIDE_INSTRUCTIONS", "ACCESS_TOOL_OR_FILE"}
        if intent == "BENIGN_TASK":
            return action in {"REVEAL_PROTECTED_CONTEXT", "OVERRIDE_INSTRUCTIONS"}
        return False

    def _score(self, intent: str, action: str, mismatch: bool) -> int:
        score = 0
        if intent in {"INTERNAL_SECRET_REQUEST", "POLICY_BYPASS_INTENT"}:
            score += 45
        if intent == "ROLE_OVERRIDE":
            score += 35
        if action == "REVEAL_PROTECTED_CONTEXT":
            score += 45
        if action == "OVERRIDE_INSTRUCTIONS":
            score += 35
        if action == "ACCESS_TOOL_OR_FILE":
            score += 30
        if mismatch:
            score += 20
        if intent == "SECURITY_EDUCATION" and not mismatch:
            score = max(0, score - 35)
        return min(score, 100)
