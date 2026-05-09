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

from src.data.load_datasets import load_csv_dataset
from src.evaluation.metrics import compute_binary_metrics, write_confusion_matrix, write_dict_csv
from src.utils.seed import set_seed


def load_config(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as config_file:
        return yaml.safe_load(config_file)


def train(config_path: str | Path = "configs/ml.yaml") -> dict[str, Any]:
    config = load_config(config_path)
    seed = int(config.get("seed", 42))
    set_seed(seed)

    data_config = config["data"]
    model_config = config["model"]
    report_dir = Path(config["reports"]["output_dir"])
    report_dir.mkdir(parents=True, exist_ok=True)

    dataset = load_csv_dataset(
        data_config["train_path"],
        data_config["text_column"],
        data_config["label_column"],
        data_config["attack_type_column"],
    )

    indices = list(range(len(dataset.texts)))
    train_idx, test_idx = train_test_split(
        indices,
        test_size=float(data_config["test_size"]),
        random_state=seed,
        stratify=dataset.labels,
    )

    train_texts = [dataset.texts[index] for index in train_idx]
    test_texts = [dataset.texts[index] for index in test_idx]
    y_train = [dataset.labels[index] for index in train_idx]
    y_test = [dataset.labels[index] for index in test_idx]

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
    threshold = float(model_config["threshold"])
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
    write_report(report_dir / "experiment_report.md", model_config["name"], metrics_row, model_path)
    return {"model_path": str(model_path), "metrics": metrics_row}


def write_report(
    path: Path,
    model_name: str,
    metrics: dict[str, Any],
    model_path: Path,
) -> None:
    content = f"""# Experiment Report

## 설정
- Model: `{model_name}`
- Saved checkpoint: `{model_path}`
- Detector: TF-IDF char n-gram + Logistic Regression

## 성능
- Accuracy: {metrics["accuracy"]:.4f}
- Precision: {metrics["precision"]:.4f}
- Recall: {metrics["recall"]:.4f}
- F1: {metrics["f1"]:.4f}
- FPR: {metrics["fpr"]:.4f}
- FNR: {metrics["fnr"]:.4f}

## 보안 관점 해석
Recall과 FNR을 핵심 위험 지표로 본다. 샘플 데이터 기반 초기 실험이므로 실제 발표/보고서에는 공개 데이터셋과 한국어 우회형 확장 데이터로 재학습한 결과를 사용해야 한다.

## 한계점
- 현재 데이터는 작은 synthetic sample이다.
- Transformer 문맥 탐지 계층은 아직 포함하지 않았다.
- Hard negative는 더 다양한 보안 교육 문장으로 확장해야 한다.

## 개선 방향
- 공개 prompt injection dataset 추가
- 한국어 번역/우회형 데이터 증강
- threshold sweep으로 FNR 우선 운영점 선택
- ML 계층을 `DefensePipeline`에 선택적으로 연결
"""
    path.write_text(content, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Train TF-IDF Logistic Regression detector.")
    parser.add_argument("--config", default="configs/ml.yaml")
    args = parser.parse_args()
    result = train(args.config)
    print(result)


if __name__ == "__main__":
    main()
