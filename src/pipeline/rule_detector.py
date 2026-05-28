from __future__ import annotations

import re
from dataclasses import dataclass

from src.pipeline.normalizer import NormalizedInput


@dataclass(frozen=True)
class RuleMatch:
    pattern: str
    attack_type: str
    evidence: str
    risk_hint: str


@dataclass(frozen=True)
class RuleDetectionResult:
    matched: bool
    patterns: list[str]
    evidence: list[str]
    risk_hint: str
    attack_types: list[str]


HARD_NEGATIVE_PATTERNS = [
    r"무엇인지\s*설명",
    r"개념.*정리",
    r"보안\s*수업",
    r"위험성.*(설명|분석|알려)",
    r"왜\s*위험한지",
    r"교육",
    r"발표용",
]

RULES: list[tuple[str, str, str, str, list[str]]] = [
    (
        "ignore_previous_instruction",
        "DIRECT_INJECTION",
        "high",
        r"(ignore|disregard).{0,20}(previous|prior|above).{0,20}(instruction|command)|이전\s*지시.{0,10}무시|앞의\s*명령.{0,10}무시",
        ["이전지시를무시", "앞의명령을무시", "ignorepreviousinstructions"],
    ),
    (
        "system_prompt_extraction",
        "SYSTEM_PROMPT_EXTRACTION",
        "critical",
        r"(system\s*prompt|시스템\s*프롬프트).{0,30}(출력|보여|공개|print|show|reveal|알려)",
        ["시스템프롬프트출력", "시스템프롬프트보여", "systempromptreveal"],
    ),
    (
        "developer_message_extraction",
        "SYSTEM_PROMPT_EXTRACTION",
        "critical",
        r"(developer\s*message|개발자\s*메시지|내부\s*규칙|숨겨진\s*지시).{0,30}(출력|보여|공개|알려|show|reveal)",
        ["개발자메시지보여", "내부규칙알려", "hiddeninstructionreveal"],
    ),
    (
        "policy_bypass",
        "POLICY_BYPASS",
        "high",
        r"(bypass|우회).{0,20}(policy|정책|제한|필터|가드레일)|제한.{0,10}우회",
        ["제한우회", "정책우회", "bypasspolicy"],
    ),
    (
        "jailbreak",
        "JAILBREAK",
        "high",
        r"jailbreak|탈옥|dan\s*mode|무제한\s*모드",
        ["jailbreak", "탈옥", "danmode"],
    ),
    (
        "role_play_attack",
        "ROLE_PLAY_ATTACK",
        "medium",
        r"(너는|you\s*are).{0,20}(개발자|관리자|system|admin|root)|역할.{0,10}(변경|바꿔)",
        ["너는관리자", "youaresystem", "역할변경"],
    ),
    (
        "data_exfiltration",
        "DATA_EXFILTRATION",
        "critical",
        r"(api\s*key|token|credential|비밀|시크릿|토큰|키).{0,20}(출력|보여|공개|알려|show|reveal)",
        ["apikey보여", "토큰출력", "credentialreveal"],
    ),
    (
        "tool_misuse",
        "TOOL_MISUSE",
        "high",
        r"(tool|api|file|파일|도구).{0,20}(접근|실행|삭제|읽어|열어|호출)",
        ["파일삭제", "toolcall", "api호출"],
    ),
]


class RuleBasedDetector:
    """Fast, explainable detector for clear prompt injection patterns."""

    def detect(self, normalized_input: NormalizedInput) -> RuleDetectionResult:
        text = normalized_input.normalized
        compact = normalized_input.compact
        hard_negative = self._is_hard_negative(text)
        matches: list[RuleMatch] = []

        for name, attack_type, risk_hint, pattern, compact_terms in RULES:
            evidence = self._match_rule(text, compact, pattern, compact_terms)
            if not evidence:
                continue
            if hard_negative and attack_type in {
                "DIRECT_INJECTION",
                "JAILBREAK",
                "POLICY_BYPASS",
                "SYSTEM_PROMPT_EXTRACTION",
            }:
                continue
            matches.append(RuleMatch(name, attack_type, evidence, risk_hint))

        if "contains_korean_jamo" in normalized_input.signals and matches:
            matches.append(
                RuleMatch(
                    "obfuscated_korean_attack",
                    "OBFUSCATED_KOREAN_ATTACK",
                    "korean jamo obfuscation detected",
                    "high",
                )
            )

        if not matches:
            return RuleDetectionResult(False, [], [], "low", [])

        risk_hint = self._max_risk_hint([match.risk_hint for match in matches])
        return RuleDetectionResult(
            matched=True,
            patterns=[match.pattern for match in matches],
            evidence=[match.evidence for match in matches],
            risk_hint=risk_hint,
            attack_types=list(dict.fromkeys(match.attack_type for match in matches)),
        )

    def _match_rule(
        self,
        text: str,
        compact: str,
        pattern: str,
        compact_terms: list[str],
    ) -> str | None:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(0)
        for term in compact_terms:
            if term in compact:
                return term
        return None

    def _is_hard_negative(self, text: str) -> bool:
        return any(re.search(pattern, text) for pattern in HARD_NEGATIVE_PATTERNS)

    def _max_risk_hint(self, hints: list[str]) -> str:
        order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        return max(hints, key=lambda hint: order[hint])
