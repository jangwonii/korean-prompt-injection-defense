from __future__ import annotations

from pathlib import Path
from typing import Any

from src.evaluation.metrics import compute_binary_metrics, write_confusion_matrix, write_dict_csv


def resolve_report_dir(config: dict[str, Any]) -> Path:
    report_config = config.get("reports", {})
    report_dir = Path(report_config.get("output_dir", "reports"))
    experiment_name = report_config.get("experiment_name")
    if experiment_name:
        report_dir = report_dir / "experiments" / str(experiment_name)
    report_dir.mkdir(parents=True, exist_ok=True)
    return report_dir


def write_evaluation_outputs(
    report_dir: Path,
    mode: str,
    texts: list[str],
    labels: list[int],
    attack_types: list[str],
    predictions: list[int],
    scores: list[float],
    risk_levels: list[str],
    detected_by: list[str],
) -> dict[str, float | int]:
    metrics = compute_binary_metrics(labels, predictions)
    write_dict_csv(report_dir / f"{mode}_metrics_summary.csv", [{"mode": mode, **metrics}])
    write_confusion_matrix(report_dir / f"{mode}_confusion_matrix.csv", metrics)
    write_attack_type_metrics(report_dir, mode, labels, attack_types, predictions)
    write_errors(report_dir, mode, texts, labels, attack_types, predictions, scores, risk_levels, detected_by)
    write_korean_obfuscation_results(
        report_dir,
        mode,
        texts,
        labels,
        attack_types,
        predictions,
        scores,
        risk_levels,
        detected_by,
    )
    return metrics


def write_errors(
    report_dir: Path,
    mode: str,
    texts: list[str],
    labels: list[int],
    attack_types: list[str],
    predictions: list[int],
    scores: list[float],
    risk_levels: list[str],
    detected_by: list[str],
) -> None:
    rows = [
        {
            "text": text,
            "attack_type": attack_type,
            "actual": actual,
            "predicted": predicted,
            "score": round(float(score), 4),
            "risk_level": risk_level,
            "detected_by": detectors,
        }
        for text, attack_type, actual, predicted, score, risk_level, detectors in zip(
            texts,
            attack_types,
            labels,
            predictions,
            scores,
            risk_levels,
            detected_by,
        )
        if actual != predicted
    ]
    write_dict_csv(report_dir / f"{mode}_false_positives.csv", [row for row in rows if row["actual"] == 0])
    write_dict_csv(report_dir / f"{mode}_false_negatives.csv", [row for row in rows if row["actual"] == 1])


def write_attack_type_metrics(
    report_dir: Path,
    mode: str,
    labels: list[int],
    attack_types: list[str],
    predictions: list[int],
) -> None:
    rows = []
    for attack_type in sorted(set(attack_types)):
        indices = [index for index, value in enumerate(attack_types) if value == attack_type]
        metrics = compute_binary_metrics(
            [labels[index] for index in indices],
            [predictions[index] for index in indices],
        )
        rows.append({"mode": mode, "attack_type": attack_type, "samples": len(indices), **metrics})
    write_dict_csv(report_dir / f"{mode}_attack_type_metrics.csv", rows)


def write_korean_obfuscation_results(
    report_dir: Path,
    mode: str,
    texts: list[str],
    labels: list[int],
    attack_types: list[str],
    predictions: list[int],
    scores: list[float],
    risk_levels: list[str],
    detected_by: list[str],
) -> None:
    target_types = {"OBFUSCATED_KOREAN_ATTACK", "MIXED_LANGUAGE_ATTACK"}
    rows = [
        {
            "text": text,
            "attack_type": attack_type,
            "actual": actual,
            "predicted": predicted,
            "score": round(float(score), 4),
            "risk_level": risk_level,
            "detected_by": detectors,
        }
        for text, attack_type, actual, predicted, score, risk_level, detectors in zip(
            texts,
            attack_types,
            labels,
            predictions,
            scores,
            risk_levels,
            detected_by,
        )
        if attack_type in target_types
    ]
    write_dict_csv(report_dir / f"{mode}_korean_obfuscation_results.csv", rows)
