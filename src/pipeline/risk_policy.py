from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from src.pipeline.rule_detector import RuleDetectionResult
from src.pipeline.risk_signals import RiskSignalsResult


DEFAULT_CONFIG_PATH = Path("configs/baseline.yaml")


@dataclass(frozen=True)
class RiskDecision:
    is_injection: bool
    risk_score: int
    risk_level: str
    attack_type: str
    detected_by: list[str]
    recommended_action: str
    evidence: list[str]


class RiskPolicy:
    """Combine layered detector outputs into a defense decision."""

    def __init__(self, config_path: str | Path = DEFAULT_CONFIG_PATH) -> None:
        self.config = self._load_config(config_path)

    def decide(
        self,
        rule_result: RuleDetectionResult,
        signal_result: RiskSignalsResult,
    ) -> RiskDecision:
        detected_by: list[str] = []
        evidence: list[str] = []

        rule_score = self._rule_score(rule_result)
        if rule_result.matched:
            detected_by.append("rule_based")
            evidence.extend(f"matched pattern: {pattern}" for pattern in rule_result.patterns)
            evidence.extend(rule_result.evidence)

        signal_score = self._signal_score(signal_result)
        if signal_score >= 20:
            detected_by.append("risk_signals")
        evidence.extend(signal_result.evidence)

        score = max(rule_score, signal_score)
        if rule_result.matched and signal_score > 0:
            score = min(100, score + 10)

        if signal_result.hard_negative_context_score >= 30 and not self._has_critical_rule(rule_result):
            score = max(0, score - 30)

        level = self._risk_level(score)
        action = self.config["actions"][level]
        attack_type = self._attack_type(rule_result, signal_result, score)

        return RiskDecision(
            is_injection=level in {"MEDIUM", "HIGH", "CRITICAL"},
            risk_score=score,
            risk_level=level,
            attack_type=attack_type,
            detected_by=list(dict.fromkeys(detected_by)),
            recommended_action=action,
            evidence=evidence,
        )

    def _load_config(self, config_path: str | Path) -> dict[str, Any]:
        with Path(config_path).open("r", encoding="utf-8") as config_file:
            return yaml.safe_load(config_file)

    def _rule_score(self, rule_result: RuleDetectionResult) -> int:
        if not rule_result.matched:
            return 0
        weights = self.config["rule_weights"]
        return max(weights.get(attack_type, 45) for attack_type in rule_result.attack_types)

    def _signal_score(self, signal_result: RiskSignalsResult) -> int:
        weights = self.config["signal_weights"]
        weighted = 0.0
        for name, value in signal_result.as_dict().items():
            weighted += value * weights.get(name, 0)
        return max(0, min(100, round(weighted)))

    def _risk_level(self, score: int) -> str:
        thresholds = self.config["thresholds"]
        if score >= thresholds["critical"]:
            return "CRITICAL"
        if score >= thresholds["high"]:
            return "HIGH"
        if score >= thresholds["medium"]:
            return "MEDIUM"
        return "LOW"

    def _attack_type(
        self,
        rule_result: RuleDetectionResult,
        signal_result: RiskSignalsResult,
        score: int,
    ) -> str:
        priority = [
            "SYSTEM_PROMPT_EXTRACTION",
            "DATA_EXFILTRATION",
            "POLICY_BYPASS",
            "JAILBREAK",
            "TOOL_MISUSE",
            "DIRECT_INJECTION",
            "OBFUSCATED_KOREAN_ATTACK",
            "MIXED_LANGUAGE_ATTACK",
            "ROLE_PLAY_ATTACK",
        ]
        for attack_type in priority:
            if attack_type in rule_result.attack_types:
                return attack_type
        if signal_result.mixed_language_score >= 70:
            return "MIXED_LANGUAGE_ATTACK"
        if signal_result.obfuscation_score >= 45 and score >= 35:
            return "OBFUSCATED_KOREAN_ATTACK"
        if score >= 35:
            return "UNKNOWN_SUSPICIOUS"
        return "BENIGN"

    def _has_critical_rule(self, rule_result: RuleDetectionResult) -> bool:
        return bool({"SYSTEM_PROMPT_EXTRACTION", "DATA_EXFILTRATION"} & set(rule_result.attack_types))
