from __future__ import annotations

import warnings
from dataclasses import replace
from pathlib import Path
from typing import Any

import yaml

from src.pipeline.canary_guard import CanaryGuard
from src.pipeline.hierarchy_guard import HierarchyGuard
from src.pipeline.intent_analyzer import IntentAnalyzer
from src.pipeline.ml_detector import MLDetector
from src.pipeline.normalizer import InputNormalizer
from src.pipeline.risk_policy import RiskPolicy
from src.pipeline.risk_policy import RiskDecision
from src.pipeline.risk_signals import RiskSignals
from src.pipeline.risk_signals import RiskSignalsResult
from src.pipeline.rule_detector import RuleBasedDetector
from src.pipeline.rule_detector import RuleDetectionResult
from src.pipeline.schemas import PipelineDetectionResult
from src.pipeline.transformer_detector import TransformerDetector


class DefensePipeline:
    """Run the layered prompt injection defense pipeline."""

    def __init__(self, config_path: str | Path = "configs/runtime/baseline.yaml") -> None:
        self.config_path = Path(config_path)
        self.normalizer = InputNormalizer()
        self.rule_detector = RuleBasedDetector()
        self.risk_signals = RiskSignals()
        self.intent_analyzer = IntentAnalyzer()
        self.hierarchy_guard = HierarchyGuard()
        self.canary_guard = CanaryGuard()
        self.risk_policy = RiskPolicy(config_path)
        self.ml_detector = self._load_ml_detector(self.config_path)
        self.transformer_detector = self._load_transformer_detector(self.config_path)

    def detect(self, text: str) -> dict[str, Any]:
        normalized = self.normalizer.normalize(text)
        rule_result = self.rule_detector.detect(normalized)
        signal_result = self.risk_signals.analyze(normalized)
        intent_result = self.intent_analyzer.analyze(normalized)
        hierarchy_result = self.hierarchy_guard.analyze(normalized, intent_result)
        canary_result = self.canary_guard.analyze(normalized)

        pre_model_decision = self.risk_policy.decide(
            rule_result,
            signal_result,
            intent_result=intent_result,
            hierarchy_result=hierarchy_result,
            canary_result=canary_result,
        )
        early_exit_reason = self._early_exit_reason(
            pre_model_decision,
            rule_result,
            signal_result,
        )
        if early_exit_reason:
            return PipelineDetectionResult.from_decision(
                normalized.original,
                normalized.normalized,
                self._mark_early_exit(pre_model_decision, early_exit_reason),
            ).to_dict()

        ml_result = self.ml_detector.detect(normalized.normalized) if self.ml_detector else None
        transformer_result = (
            self.transformer_detector.detect(normalized.normalized) if self.transformer_detector else None
        )
        decision = self.risk_policy.decide(
            rule_result,
            signal_result,
            ml_result=ml_result,
            intent_result=intent_result,
            hierarchy_result=hierarchy_result,
            canary_result=canary_result,
            transformer_result=transformer_result,
        )

        return PipelineDetectionResult.from_decision(
            normalized.original,
            normalized.normalized,
            decision,
        ).to_dict()

    def enabled_layers(self) -> list[str]:
        layers = [
            "normalizer",
            "rule_based",
            "risk_signals",
            "intent_analyzer",
            "hierarchy_guard",
            "canary_guard",
            "risk_policy",
        ]
        if self.ml_detector is not None:
            layers.append("ml")
        if self.transformer_detector is not None:
            layers.append("transformer")
        return layers

    def _early_exit_reason(
        self,
        decision: RiskDecision,
        rule_result: RuleDetectionResult,
        signal_result: RiskSignalsResult,
    ) -> str | None:
        config = self.risk_policy.config.get("early_exit", {})
        if not config.get("enabled", False):
            return None
        if self._should_block_early(decision, config):
            return "block_clear_attack"
        if self._should_allow_early(decision, rule_result, signal_result, config):
            return "allow_clear_benign"
        return None

    def _should_block_early(self, decision: RiskDecision, config: dict[str, Any]) -> bool:
        block_levels = set(config.get("block_levels", ["CRITICAL"]))
        block_actions = set(config.get("block_actions", ["BLOCK"]))
        block_sources = set(config.get("block_sources", ["rule_based", "hierarchy_guard", "canary_guard"]))
        return (
            decision.risk_level in block_levels
            and decision.recommended_action in block_actions
            and bool(block_sources & set(decision.detected_by))
        )

    def _should_allow_early(
        self,
        decision: RiskDecision,
        rule_result: RuleDetectionResult,
        signal_result: RiskSignalsResult,
        config: dict[str, Any],
    ) -> bool:
        if rule_result.matched:
            return False
        if decision.risk_level != config.get("allow_level", "LOW"):
            return False
        if decision.recommended_action != config.get("allow_action", "ALLOW"):
            return False
        if decision.hierarchy_violation or decision.canary_triggered:
            return False
        if signal_result.obfuscation_score > int(config.get("allow_max_obfuscation_score", 0)):
            return False
        if signal_result.instruction_override_score > int(config.get("allow_max_instruction_override_score", 0)):
            return False
        if signal_result.mixed_language_score > int(config.get("allow_max_mixed_language_score", 25)):
            return False

        max_sensitive_target = int(config.get("allow_max_sensitive_target_score", 0))
        if signal_result.sensitive_target_score <= max_sensitive_target:
            return True

        return (
            bool(config.get("allow_security_education", True))
            and decision.intent == "SECURITY_EDUCATION"
            and decision.requested_action == "EXPLAIN"
            and signal_result.hard_negative_context_score >= 30
        )

    def _mark_early_exit(self, decision: RiskDecision, reason: str) -> RiskDecision:
        detected_by = decision.detected_by
        if decision.is_injection:
            detected_by = [*detected_by, "early_exit_rule_gate"]
        return replace(
            decision,
            detected_by=list(dict.fromkeys(detected_by)),
            evidence=[*decision.evidence, f"early_exit: {reason}"],
        )

    def _load_ml_detector(self, config_path: Path) -> MLDetector | None:
        with config_path.open("r", encoding="utf-8") as config_file:
            config = yaml.safe_load(config_file) or {}
        model_path = config.get("model", {}).get("output_path")
        if not model_path:
            return None
        path = Path(model_path)
        if not path.exists():
            return None
        return MLDetector(path)

    def _load_transformer_detector(self, config_path: Path) -> TransformerDetector | None:
        with config_path.open("r", encoding="utf-8") as config_file:
            config = yaml.safe_load(config_file) or {}
        model_config = config.get("model", {})
        model_dir = model_config.get("output_dir")
        if not model_dir:
            return None
        path = Path(model_dir)
        if not path.exists():
            warnings.warn(
                f"Transformer checkpoint not found: {path}. "
                "Transformer layer is disabled for this pipeline instance.",
                RuntimeWarning,
                stacklevel=2,
            )
            return None
        return TransformerDetector(
            path,
            threshold=float(model_config.get("threshold", 0.5)),
            max_length=int(model_config.get("max_length", 256)),
        )
