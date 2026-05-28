from __future__ import annotations

import re
from dataclasses import dataclass

from src.pipeline.normalizer import NormalizedInput


@dataclass(frozen=True)
class RiskSignalsResult:
    obfuscation_score: int
    sensitive_target_score: int
    instruction_override_score: int
    mixed_language_score: int
    hard_negative_context_score: int
    evidence: list[str]

    def as_dict(self) -> dict[str, int]:
        return {
            "obfuscation_score": self.obfuscation_score,
            "sensitive_target_score": self.sensitive_target_score,
            "instruction_override_score": self.instruction_override_score,
            "mixed_language_score": self.mixed_language_score,
            "hard_negative_context_score": self.hard_negative_context_score,
        }


class RiskSignals:
    """Security-signal ensemble beyond explicit rule matches."""

    def analyze(self, normalized_input: NormalizedInput) -> RiskSignalsResult:
        text = normalized_input.normalized
        compact = normalized_input.compact
        original = normalized_input.original
        evidence: list[str] = []

        obfuscation = self._obfuscation_score(normalized_input, original, evidence)
        sensitive_target = self._sensitive_target_score(text, compact, evidence)
        instruction_override = self._instruction_override_score(text, compact, evidence)
        mixed_language = self._mixed_language_score(text, evidence)
        hard_negative = self._hard_negative_context_score(text, evidence)

        return RiskSignalsResult(
            obfuscation_score=obfuscation,
            sensitive_target_score=sensitive_target,
            instruction_override_score=instruction_override,
            mixed_language_score=mixed_language,
            hard_negative_context_score=hard_negative,
            evidence=evidence,
        )

    def _obfuscation_score(
        self,
        normalized_input: NormalizedInput,
        original: str,
        evidence: list[str],
    ) -> int:
        score = 0
        if "contains_korean_jamo" in normalized_input.signals:
            score += 45
            evidence.append("signal: korean jamo obfuscation")
        if "repeated_whitespace" in normalized_input.signals:
            score += 20
            evidence.append("signal: repeated whitespace")
        if "special_character_cleanup" in normalized_input.signals:
            score += 20
            evidence.append("signal: special character insertion")
        if re.search(r"[^\w\s가-힣ㄱ-ㅎㅏ-ㅣ]{2,}", original, flags=re.UNICODE):
            score += 15
            evidence.append("signal: repeated non-word separators")
        return min(score, 100)

    def _sensitive_target_score(self, text: str, compact: str, evidence: list[str]) -> int:
        score = 0
        targets = [
            ("system prompt", "system prompt"),
            ("시스템 프롬프트", "시스템 프롬프트"),
            ("developer message", "developer message"),
            ("개발자 메시지", "개발자 메시지"),
            ("내부 규칙", "내부 규칙"),
            ("hidden instruction", "hidden instruction"),
            ("api key", "api key"),
            ("token", "token"),
            ("credential", "credential"),
            ("비밀", "비밀"),
        ]
        for pattern, label in targets:
            if pattern in text or pattern.replace(" ", "") in compact:
                score += 25
                evidence.append(f"signal: sensitive target '{label}'")
        return min(score, 100)

    def _instruction_override_score(self, text: str, compact: str, evidence: list[str]) -> int:
        score = 0
        patterns = [
            (r"이전\s*지시.*무시|앞의\s*명령.*무시", "Korean instruction override"),
            (r"ignore.*(previous|prior|above).*instruction", "English instruction override"),
            (r"역할.*(변경|바꿔)|너는.*(관리자|개발자|시스템)", "role change attempt"),
            (r"(bypass|우회).*(policy|정책|제한|필터)", "policy bypass intent"),
        ]
        compact_terms = ["이전지시무시", "앞의명령무시", "ignorepreviousinstruction", "정책우회", "제한우회"]
        for pattern, label in patterns:
            if re.search(pattern, text, flags=re.IGNORECASE):
                score += 30
                evidence.append(f"signal: {label}")
        for term in compact_terms:
            if term in compact:
                score += 25
                evidence.append(f"signal: compact override '{term}'")
        return min(score, 100)

    def _mixed_language_score(self, text: str, evidence: list[str]) -> int:
        has_korean = bool(re.search(r"[가-힣]", text))
        has_english = bool(re.search(r"[a-zA-Z]", text))
        suspicious_english = bool(
            re.search(r"ignore|instruction|system|prompt|developer|bypass|jailbreak|policy", text)
        )
        if has_korean and has_english and suspicious_english:
            evidence.append("signal: mixed Korean-English suspicious instruction")
            return 70
        if has_korean and has_english:
            evidence.append("signal: mixed Korean-English input")
            return 25
        return 0

    def _hard_negative_context_score(self, text: str, evidence: list[str]) -> int:
        patterns = [
            r"무엇인지\s*설명",
            r"개념.*정리",
            r"보안\s*수업",
            r"보안\s*교육",
            r"위험성.*(설명|분석|알려)",
            r"왜\s*위험한지",
            r"위험한\s*이유",
            r"탐지.*방법",
            r"탐지\s*규칙",
            r"방어.*방법",
            r"방어\s*정책",
            r"구분하는\s*방법",
            r"안전하게\s*관리",
            r"관리하는\s*방법",
            r"요청.*(차단|거절|탐지|검증|분류|막는)",
            r"(차단|거절|탐지|검증|분류).*요청",
            r"공개하면\s*안\s*되는\s*이유",
            r"규칙\s*예시",
            r"체크리스트",
            r"제한하는\s*방법",
            r"방어\s*예시",
            r"문장.*왜\s*공격인지",
            r"사용자\s*안내문",
            r"보호\s*정책",
            r"설계할\s*때\s*주의",
            r"교육",
            r"발표용",
        ]
        score = 0
        for pattern in patterns:
            if re.search(pattern, text):
                score += 30
        if score:
            evidence.append("signal: benign education or analysis context")
        return min(score, 100)
