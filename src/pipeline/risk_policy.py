from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from src.pipeline.canary_guard import CanaryGuardResult
from src.pipeline.hierarchy_guard import HierarchyGuardResult
from src.pipeline.intent_analyzer import IntentAnalysisResult
from src.pipeline.ml_detector import MLDetectionResult
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
    intent: str
    requested_action: str
    hierarchy_violation: bool
    violated_hierarchy_level: str
    intent_action_mismatch: bool
    canary_triggered: bool


class RiskPolicy:
    """Combine layered detector outputs into a defense decision."""

    def __init__(self, config_path: str | Path = DEFAULT_CONFIG_PATH) -> None:
        self.config = self._load_config(config_path)

    def decide(
        self,
        rule_result: RuleDetectionResult,
        signal_result: RiskSignalsResult,
        ml_result: MLDetectionResult | None = None,
        intent_result: IntentAnalysisResult | None = None,
        hierarchy_result: HierarchyGuardResult | None = None,
        canary_result: CanaryGuardResult | None = None,
    ) -> RiskDecision:
        intent_result = intent_result or self._default_intent_result()
        hierarchy_result = hierarchy_result or self._default_hierarchy_result()
        canary_result = canary_result or self._default_canary_result()

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

        ml_score = self._ml_score(ml_result)
        if ml_result is not None:
            evidence.append(f"ml_score: {ml_result.score:.4f}")
            evidence.append(f"ml_prediction: {ml_result.prediction}")
            if ml_result.prediction == 1:
                detected_by.append("ml")

        semantic_score = self._semantic_score(intent_result, hierarchy_result, canary_result)
        if intent_result.risk_score >= 35:
            detected_by.append("intent_analyzer")
        if hierarchy_result.hierarchy_violation:
            detected_by.append("hierarchy_guard")
        if canary_result.canary_triggered:
            detected_by.append("canary_guard")
        evidence.extend(intent_result.evidence)
        evidence.extend(hierarchy_result.evidence)
        evidence.extend(canary_result.evidence)

        score = max(rule_score, signal_score, semantic_score)
        if ml_result is not None and ml_result.prediction == 1:
            score = max(score, ml_score, self._ml_positive_min_score())
        if rule_result.matched and signal_score > 0:
            score = min(100, score + 10)
        if hierarchy_result.hierarchy_violation and rule_result.matched:
            score = min(100, score + 10)
        if canary_result.canary_triggered:
            score = max(score, 80)

        if (
            signal_result.hard_negative_context_score >= 30
            and not self._has_critical_rule(rule_result)
            and not hierarchy_result.hierarchy_violation
            and not canary_result.canary_triggered
        ):
            score = max(0, score - 35)

        level = self._risk_level(score)
        action = self.config["actions"][level]
        attack_type = self._attack_type(
            rule_result,
            signal_result,
            intent_result,
            hierarchy_result,
            canary_result,
            score,
        )

        return RiskDecision(
            is_injection=level in {"MEDIUM", "HIGH", "CRITICAL"},
            risk_score=score,
            risk_level=level,
            attack_type=attack_type,
            detected_by=list(dict.fromkeys(detected_by)),
            recommended_action=action,
            evidence=evidence,
            intent=intent_result.intent,
            requested_action=intent_result.requested_action,
            hierarchy_violation=hierarchy_result.hierarchy_violation,
            violated_hierarchy_level=hierarchy_result.violated_level,
            intent_action_mismatch=intent_result.intent_action_mismatch,
            canary_triggered=canary_result.canary_triggered,
        )

    def _load_config(self, config_path: str | Path) -> dict[str, Any]:
        config = self._read_yaml(config_path)
        if Path(config_path) == DEFAULT_CONFIG_PATH:
            return config
        return self._merge_dicts(self._read_yaml(DEFAULT_CONFIG_PATH), config)

    def _read_yaml(self, config_path: str | Path) -> dict[str, Any]:
        with Path(config_path).open("r", encoding="utf-8") as config_file:
            return yaml.safe_load(config_file) or {}

    def _merge_dicts(self, base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        merged = dict(base)
        for key, value in override.items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key] = self._merge_dicts(merged[key], value)
            else:
                merged[key] = value
        return merged

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

    def _ml_score(self, ml_result: MLDetectionResult | None) -> int:
        if ml_result is None:
            return 0
        return max(0, min(100, round(ml_result.score * 100)))

    def _ml_positive_min_score(self) -> int:
        return int(self.config.get("ml_policy", {}).get("positive_min_score", self.config["thresholds"]["medium"]))

    def _semantic_score(
        self,
        intent_result: IntentAnalysisResult,
        hierarchy_result: HierarchyGuardResult,
        canary_result: CanaryGuardResult,
    ) -> int:
        weights = self.config["semantic_weights"]
        weighted = (
            intent_result.risk_score * weights["intent_score"]
            + hierarchy_result.risk_score * weights["hierarchy_score"]
            + canary_result.risk_score * weights["canary_score"]
        )
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
        intent_result: IntentAnalysisResult,
        hierarchy_result: HierarchyGuardResult,
        canary_result: CanaryGuardResult,
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
        if canary_result.canary_triggered:
            return "DATA_EXFILTRATION"
        if hierarchy_result.hierarchy_violation and hierarchy_result.violated_level in {"SYSTEM", "DEVELOPER"}:
            return "SYSTEM_PROMPT_EXTRACTION"
        if intent_result.intent == "POLICY_BYPASS_INTENT":
            return "POLICY_BYPASS"
        if signal_result.mixed_language_score >= 70:
            return "MIXED_LANGUAGE_ATTACK"
        if intent_result.requested_action == "OVERRIDE_INSTRUCTIONS":
            return "DIRECT_INJECTION"
        if signal_result.obfuscation_score >= 45 and score >= 35:
            return "OBFUSCATED_KOREAN_ATTACK"
        if score >= 35:
            return "UNKNOWN_SUSPICIOUS"
        return "BENIGN"

    def _default_intent_result(self) -> IntentAnalysisResult:
        return IntentAnalysisResult(
            intent="BENIGN_TASK",
            requested_action="COMPLETE_TASK",
            intent_action_mismatch=False,
            risk_score=0,
            evidence=[],
        )

    def _default_hierarchy_result(self) -> HierarchyGuardResult:
        return HierarchyGuardResult(
            hierarchy_violation=False,
            violated_level="NONE",
            risk_score=0,
            evidence=[],
        )

    def _default_canary_result(self) -> CanaryGuardResult:
        return CanaryGuardResult(
            canary_triggered=False,
            risk_score=0,
            evidence=[],
        )

    def _has_critical_rule(self, rule_result: RuleDetectionResult) -> bool:
        return bool({"SYSTEM_PROMPT_EXTRACTION", "DATA_EXFILTRATION"} & set(rule_result.attack_types))
