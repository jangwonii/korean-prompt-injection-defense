from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class TransformerDetectionResult:
    model: str
    score: float
    prediction: int


class TransformerDetector:
    """Load and run a fine-tuned Hugging Face sequence classifier."""

    def __init__(
        self,
        model_path: str | Path,
        threshold: float = 0.5,
        max_length: int = 256,
        device: int | None = None,
    ) -> None:
        try:
            import torch
            from transformers import AutoModelForSequenceClassification, AutoTokenizer, pipeline
        except ImportError as exc:
            raise RuntimeError(
                "TransformerDetector requires torch and transformers. "
                "Install project dependencies with `python -m pip install -r requirements.txt`."
            ) from exc

        self.model_path = str(model_path)
        self.threshold = threshold
        self.max_length = max_length
        self.model_name = Path(model_path).name

        tokenizer = AutoTokenizer.from_pretrained(self.model_path)
        model = AutoModelForSequenceClassification.from_pretrained(self.model_path)
        if device is None:
            device = 0 if torch.cuda.is_available() else -1
        self.classifier = pipeline(
            "text-classification",
            model=model,
            tokenizer=tokenizer,
            top_k=None,
            truncation=True,
            max_length=self.max_length,
            device=device,
        )

    def detect(self, text: str) -> TransformerDetectionResult:
        outputs: list[dict[str, Any]] = self.classifier(text)[0]
        score = self._positive_score(outputs)
        return TransformerDetectionResult(
            model=self.model_name,
            score=score,
            prediction=1 if score >= self.threshold else 0,
        )

    def _positive_score(self, outputs: list[dict[str, Any]]) -> float:
        for item in outputs:
            label = str(item["label"]).lower()
            if label in {"label_1", "injection", "1"}:
                return float(item["score"])
        if len(outputs) == 2:
            return float(outputs[1]["score"])
        return float(max(item["score"] for item in outputs))
