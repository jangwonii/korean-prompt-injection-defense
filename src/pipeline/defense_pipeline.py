from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

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
        self.risk_policy = RiskPolicy(config_path)

    def detect(self, text: str) -> dict[str, Any]:
        normalized = self.normalizer.normalize(text)
        rule_result = self.rule_detector.detect(normalized)
        signal_result = self.risk_signals.analyze(normalized)
        decision = self.risk_policy.decide(rule_result, signal_result)

        return {
            "input": normalized.original,
            "normalized_input": normalized.normalized,
            **asdict(decision),
        }
