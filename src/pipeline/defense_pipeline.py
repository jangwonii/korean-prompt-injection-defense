from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from src.pipeline.canary_guard import CanaryGuard
from src.pipeline.hierarchy_guard import HierarchyGuard
from src.pipeline.intent_analyzer import IntentAnalyzer
from src.pipeline.normalizer import InputNormalizer
from src.pipeline.risk_policy import RiskPolicy
from src.pipeline.risk_signals import RiskSignals
from src.pipeline.rule_detector import RuleBasedDetector


class DefensePipeline:
    """Run the layered prompt injection defense pipeline."""

    def __init__(self, config_path: str | Path = "configs/baseline.yaml") -> None:
        self.normalizer = InputNormalizer()
        self.rule_detector = RuleBasedDetector()
        self.risk_signals = RiskSignals()
        self.intent_analyzer = IntentAnalyzer()
        self.hierarchy_guard = HierarchyGuard()
        self.canary_guard = CanaryGuard()
        self.risk_policy = RiskPolicy(config_path)

    def detect(self, text: str) -> dict[str, Any]:
        normalized = self.normalizer.normalize(text)
        rule_result = self.rule_detector.detect(normalized)
        signal_result = self.risk_signals.analyze(normalized)
        intent_result = self.intent_analyzer.analyze(normalized)
        hierarchy_result = self.hierarchy_guard.analyze(normalized, intent_result)
        canary_result = self.canary_guard.analyze(normalized)
        decision = self.risk_policy.decide(
            rule_result,
            signal_result,
            intent_result,
            hierarchy_result,
            canary_result,
        )

        return {
            "input": normalized.original,
            "normalized_input": normalized.normalized,
            **asdict(decision),
        }
