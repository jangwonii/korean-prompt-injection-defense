from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

import yaml

from src.pipeline.canary_guard import CanaryGuard
from src.pipeline.hierarchy_guard import HierarchyGuard
from src.pipeline.intent_analyzer import IntentAnalyzer
from src.pipeline.ml_detector import MLDetector
from src.pipeline.normalizer import InputNormalizer
from src.pipeline.risk_policy import RiskPolicy
from src.pipeline.risk_signals import RiskSignals
from src.pipeline.rule_detector import RuleBasedDetector
from src.pipeline.transformer_detector import TransformerDetector


class DefensePipeline:
    """Run the layered prompt injection defense pipeline."""

    def __init__(self, config_path: str | Path = "configs/baseline.yaml") -> None:
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
        ml_result = self.ml_detector.detect(normalized.normalized) if self.ml_detector else None
        transformer_result = (
            self.transformer_detector.detect(normalized.normalized) if self.transformer_detector else None
        )
        intent_result = self.intent_analyzer.analyze(normalized)
        hierarchy_result = self.hierarchy_guard.analyze(normalized, intent_result)
        canary_result = self.canary_guard.analyze(normalized)
        decision = self.risk_policy.decide(
            rule_result,
            signal_result,
            ml_result=ml_result,
            intent_result=intent_result,
            hierarchy_result=hierarchy_result,
            canary_result=canary_result,
            transformer_result=transformer_result,
        )

        return {
            "input": normalized.original,
            "normalized_input": normalized.normalized,
            **asdict(decision),
        }

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
            return None
        return TransformerDetector(
            path,
            threshold=float(model_config.get("threshold", 0.5)),
            max_length=int(model_config.get("max_length", 256)),
        )
