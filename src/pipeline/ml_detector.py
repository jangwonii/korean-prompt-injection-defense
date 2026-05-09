from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import joblib


@dataclass(frozen=True)
class MLDetectionResult:
    model: str
    score: float
    prediction: int


class MLDetector:
    """Load and run the trained classical ML detector."""

    def __init__(self, model_path: str | Path) -> None:
        artifact = joblib.load(model_path)
        self.model = artifact["model"]
        self.threshold = float(artifact["threshold"])
        self.model_name = artifact["model_name"]

    def detect(self, text: str) -> MLDetectionResult:
        score = float(self.model.predict_proba([text])[:, 1][0])
        return MLDetectionResult(
            model=self.model_name,
            score=score,
            prediction=1 if score >= self.threshold else 0,
        )
