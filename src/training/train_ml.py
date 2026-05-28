from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import joblib
import yaml
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from src.data.load_datasets import load_csv_datasets
from src.evaluation.metrics import compute_binary_metrics, write_confusion_matrix, write_dict_csv
from src.pipeline.normalizer import InputNormalizer
from src.utils.seed import set_seed


def load_config(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as config_file:
        return yaml.safe_load(config_file)


def train(config_path: str | Path = "configs/runtime/ml.yaml") -> dict[str, Any]:
    config = load_config(config_path)
    seed = int(config.get("seed", 42))
    set_seed(seed)

    data_config = config["data"]
    model_config = config["model"]
    report_dir = Path(config["reports"]["output_dir"])
    report_dir.mkdir(parents=True, exist_ok=True)
    normalizer = InputNormalizer()

    train_paths = _config_paths(data_config, "train_paths", "train_path")
    train_dataset = load_csv_datasets(
        train_paths,
        data_config["text_column"],
        data_config["label_column"],
        data_config["attack_type_column"],
    )

    eval_paths = _optional_config_paths(data_config, "eval_paths", "eval_path", "test_path")
    if eval_paths:
        eval_dataset = load_csv_datasets(
            eval_paths,
            data_config["text_column"],
            data_config["label_column"],
            data_config["attack_type_column"],
        )
        train_texts = _normalize_texts(train_dataset.texts, normalizer)
        test_texts = _normalize_texts(eval_dataset.texts, normalizer)
        y_train = train_dataset.labels
        y_test = eval_dataset.labels
    else:
        indices = list(range(len(train_dataset.texts)))
        train_idx, test_idx = train_test_split(
            indices,
            test_size=float(data_config["test_size"]),
            random_state=seed,
            stratify=train_dataset.labels,
        )

        train_texts = _normalize_texts([train_dataset.texts[index] for index in train_idx], normalizer)
        test_texts = _normalize_texts([train_dataset.texts[index] for index in test_idx], normalizer)
        y_train = [train_dataset.labels[index] for index in train_idx]
        y_test = [train_dataset.labels[index] for index in test_idx]

    pipeline = Pipeline(
        steps=[
            (
                "tfidf",
                TfidfVectorizer(
                    max_features=int(model_config["max_features"]),
                    ngram_range=tuple(model_config["ngram_range"]),
                    analyzer="char_wb",
                ),
            ),
            (
                "classifier",
                LogisticRegression(
                    class_weight=model_config.get("class_weight", "balanced"),
                    random_state=seed,
                    max_iter=1000,
                ),
            ),
        ]
    )
    pipeline.fit(train_texts, y_train)

    probabilities = pipeline.predict_proba(test_texts)[:, 1]
    threshold_rows = _threshold_sweep(y_test, probabilities, model_config.get("calibration", {}))
    threshold = _select_threshold(
        threshold_rows,
        float(model_config["threshold"]),
        model_config.get("calibration", {}),
    )
    predictions = [1 if probability >= threshold else 0 for probability in probabilities]
    metrics = compute_binary_metrics(y_test, predictions)

    model_path = Path(model_config["output_path"])
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "model": pipeline,
            "threshold": threshold,
            "model_name": model_config["name"],
            "config": config,
        },
        model_path,
    )

    metrics_row = {"model": model_config["name"], "threshold": threshold, **metrics}
    write_dict_csv(report_dir / "metrics_summary.csv", [metrics_row])
    if threshold_rows:
        write_dict_csv(report_dir / "ml_threshold_sweep.csv", threshold_rows)
    write_confusion_matrix(report_dir / "confusion_matrix.csv", metrics)

    error_rows = []
    for text, actual, predicted, probability in zip(test_texts, y_test, predictions, probabilities):
        if actual != predicted:
            error_rows.append(
                {
                    "text": text,
                    "actual": actual,
                    "predicted": predicted,
                    "score": round(float(probability), 4),
                }
            )

    write_dict_csv(report_dir / "false_positives.csv", [row for row in error_rows if row["actual"] == 0])
    write_dict_csv(report_dir / "false_negatives.csv", [row for row in error_rows if row["actual"] == 1])
    write_dict_csv(
        report_dir / "korean_obfuscation_results.csv",
        [
            {
                "text": text,
                "actual": actual,
                "predicted": predicted,
                "score": round(float(probability), 4),
            }
            for text, actual, predicted, probability in zip(test_texts, y_test, predictions, probabilities)
            if "ㅅ" in text or "  " in text or "이 전" in text
        ],
    )
    write_report(
        report_dir / "experiment_report.md",
        model_config["name"],
        metrics_row,
        model_path,
        train_path=", ".join(train_paths),
        eval_path=", ".join(eval_paths) if eval_paths else f"random {data_config['test_size']} split from train_path",
        train_size=len(train_texts),
        eval_size=len(test_texts),
    )
    return {"model_path": str(model_path), "metrics": metrics_row}


def _normalize_texts(texts: list[str], normalizer: InputNormalizer) -> list[str]:
    return [normalizer.normalize(text).normalized for text in texts]


def _config_paths(config: dict[str, Any], list_key: str, single_key: str) -> list[str]:
    value = config.get(list_key, config[single_key])
    if isinstance(value, list):
        return [str(path) for path in value]
    return [str(value)]


def _optional_config_paths(config: dict[str, Any], *keys: str) -> list[str]:
    for key in keys:
        if key not in config:
            continue
        value = config[key]
        if isinstance(value, list):
            return [str(path) for path in value]
        return [str(value)]
    return []


def write_report(
    path: Path,
    model_name: str,
    metrics: dict[str, Any],
    model_path: Path,
    train_path: str = "data/samples/prompt_injection_samples.csv",
    eval_path: str = "random split",
    train_size: int | None = None,
    eval_size: int | None = None,
) -> None:
    train_size_line = f"- Train rows: {train_size}" if train_size is not None else "- Train rows: unknown"
    eval_size_line = f"- Eval rows: {eval_size}" if eval_size is not None else "- Eval rows: unknown"
    content = f"""# Experiment Report

## 설정
- Model: `{model_name}`
- Saved checkpoint: `{model_path}`
- Detector: TF-IDF char n-gram + Logistic Regression
- Train dataset: `{train_path}`
- Evaluation dataset: `{eval_path}`
{train_size_line}
{eval_size_line}

## 성능
- Accuracy: {metrics["accuracy"]:.4f}
- Precision: {metrics["precision"]:.4f}
- Recall: {metrics["recall"]:.4f}
- F1: {metrics["f1"]:.4f}
- FPR: {metrics["fpr"]:.4f}
- FNR: {metrics["fnr"]:.4f}

## 보안 관점 해석
Recall과 FNR을 핵심 위험 지표로 본다. 공개 데이터셋 holdout을 사용할 때는 `eval_path`를 기준으로 성능을 해석하고, sample dataset 결과는 smoke/regression 확인으로만 사용한다.
ML 계층은 단독 차단 판단자가 아니라 rule/transformer/risk policy를 보조하는 경량 신호로 사용한다. Threshold sweep 결과가 있으면 `ml_threshold_sweep.csv`에서 FPR 통제 조건과 Recall 유지 여부를 함께 확인한다.

## 한계점
- 현재 공개 데이터셋은 영어 중심이므로 한국어 운영 성능을 직접 대표하지 않는다.
- Public dataset에는 prompt injection, jailbreak, harmful-content safety 요청이 섞여 있어 attack taxonomy 정제가 필요하다.
- Transformer 문맥 탐지 계층과 한국어 번역/우회형 holdout 평가는 별도로 수행해야 한다.

## 개선 방향
- 한국어 번역/우회형 데이터 증강
- threshold sweep으로 FNR 우선 운영점 선택
- attack-type별 recall/FNR 리포트 추가
"""
    path.write_text(content, encoding="utf-8")


def _threshold_sweep(
    y_true: list[int],
    probabilities: Any,
    calibration_config: dict[str, Any],
) -> list[dict[str, Any]]:
    if not calibration_config.get("enabled", False):
        return []

    min_threshold = float(calibration_config.get("min_threshold", 0.1))
    max_threshold = float(calibration_config.get("max_threshold", 0.95))
    step = float(calibration_config.get("step", 0.05))
    if step <= 0:
        raise ValueError("model.calibration.step must be greater than 0")

    rows: list[dict[str, Any]] = []
    threshold = min_threshold
    while threshold <= max_threshold + 1e-9:
        rounded_threshold = round(threshold, 4)
        predictions = [1 if probability >= rounded_threshold else 0 for probability in probabilities]
        metrics = compute_binary_metrics(y_true, predictions)
        rows.append({"threshold": rounded_threshold, **metrics})
        threshold += step
    return rows


def _select_threshold(
    threshold_rows: list[dict[str, Any]],
    fallback_threshold: float,
    calibration_config: dict[str, Any],
) -> float:
    if not threshold_rows:
        return fallback_threshold

    max_fpr = float(calibration_config.get("max_fpr", 1.0))
    min_recall = float(calibration_config.get("min_recall", 0.0))
    candidates = [
        row for row in threshold_rows if float(row["fpr"]) <= max_fpr and float(row["recall"]) >= min_recall
    ]
    if not candidates:
        candidates = threshold_rows

    selected = max(
        candidates,
        key=lambda row: (
            float(row["recall"]),
            -float(row["fnr"]),
            -float(row["fpr"]),
            float(row["f1"]),
            float(row["threshold"]),
        ),
    )
    return float(selected["threshold"])


def main() -> None:
    parser = argparse.ArgumentParser(description="Train TF-IDF Logistic Regression detector.")
    parser.add_argument("--config", default="configs/runtime/ml.yaml")
    args = parser.parse_args()
    result = train(args.config)
    print(result)


if __name__ == "__main__":
    main()
