from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any

import yaml

from src.data.load_datasets import load_csv_dataset
from src.evaluation.metrics import compute_binary_metrics, write_confusion_matrix, write_dict_csv
from src.pipeline.defense_pipeline import DefensePipeline
from src.pipeline.ml_detector import MLDetector
from src.pipeline.normalizer import InputNormalizer
from src.pipeline.rule_detector import RuleBasedDetector
from src.pipeline.transformer_detector import TransformerDetector


def load_config(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as config_file:
        return yaml.safe_load(config_file)


def evaluate(mode: str, config_path: str | Path) -> dict[str, float | int]:
    config = load_config(config_path)
    data_config = _data_config(config)
    report_dir = Path(config.get("reports", {}).get("output_dir", "reports"))
    report_dir.mkdir(parents=True, exist_ok=True)
    dataset = load_csv_dataset(
        data_config["eval_path"],
        data_config["text_column"],
        data_config["label_column"],
        data_config["attack_type_column"],
    )

    if mode == "rule":
        normalizer = InputNormalizer()
        detector = RuleBasedDetector()
        results = [detector.detect(normalizer.normalize(text)) for text in dataset.texts]
        scores = [_rule_score(result.risk_hint) for result in results]
        predictions = [1 if result.matched else 0 for result in results]
    elif mode == "ml":
        detector = MLDetector(config["model"]["output_path"])
        normalizer = InputNormalizer()
        results = [detector.detect(normalizer.normalize(text).normalized) for text in dataset.texts]
        scores = [result.score for result in results]
        predictions = [result.prediction for result in results]
    elif mode == "transformer":
        detector = TransformerDetector(
            os.environ.get("TRANSFORMER_OUTPUT_DIR", config["model"]["output_dir"]),
            threshold=float(config["model"]["threshold"]),
            max_length=int(config["model"]["max_length"]),
        )
        scores = [detector.detect(text).score for text in dataset.texts]
        predictions = [detector.detect(text).prediction for text in dataset.texts]
    elif mode == "full":
        pipeline = DefensePipeline(config_path)
        decisions = [pipeline.detect(text) for text in dataset.texts]
        scores = [decision["risk_score"] / 100 for decision in decisions]
        predictions = [1 if decision["is_injection"] else 0 for decision in decisions]
    else:
        raise ValueError("mode must be one of: rule, ml, transformer, full")

    metrics = compute_binary_metrics(dataset.labels, predictions)
    metrics_row = {"mode": mode, **metrics}
    write_dict_csv(report_dir / f"{mode}_metrics_summary.csv", [metrics_row])
    write_confusion_matrix(report_dir / f"{mode}_confusion_matrix.csv", metrics)
    write_errors(report_dir, mode, dataset.texts, dataset.labels, dataset.attack_types, predictions, scores)
    return metrics


def write_errors(
    report_dir: Path,
    mode: str,
    texts: list[str],
    labels: list[int],
    attack_types: list[str],
    predictions: list[int],
    scores: list[float],
) -> None:
    rows = [
        {
            "text": text,
            "attack_type": attack_type,
            "actual": actual,
            "predicted": predicted,
            "score": round(float(score), 4),
        }
        for text, attack_type, actual, predicted, score in zip(texts, attack_types, labels, predictions, scores)
        if actual != predicted
    ]
    write_dict_csv(report_dir / f"{mode}_false_positives.csv", [row for row in rows if row["actual"] == 0])
    write_dict_csv(report_dir / f"{mode}_false_negatives.csv", [row for row in rows if row["actual"] == 1])


def _data_config(config: dict[str, Any]) -> dict[str, str]:
    data_config = config.get("data", {})
    return {
        "train_path": data_config.get("train_path", "data/samples/prompt_injection_samples.csv"),
        "eval_path": data_config.get(
            "eval_path",
            data_config.get("test_path", data_config.get("train_path", "data/samples/prompt_injection_samples.csv")),
        ),
        "text_column": data_config.get("text_column", "text"),
        "label_column": data_config.get("label_column", "label"),
        "attack_type_column": data_config.get("attack_type_column", "attack_type"),
    }


def _rule_score(risk_hint: str) -> float:
    return {
        "low": 0.0,
        "medium": 0.5,
        "high": 0.75,
        "critical": 1.0,
    }.get(risk_hint, 0.0)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate a detector layer or full defense pipeline.")
    parser.add_argument("--mode", choices=["rule", "ml", "transformer", "full"], default="full")
    parser.add_argument("--config", default="configs/ml.yaml")
    args = parser.parse_args()
    print(evaluate(args.mode, args.config))


if __name__ == "__main__":
    main()
