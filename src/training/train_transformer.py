from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml
from sklearn.model_selection import train_test_split

from src.data.load_datasets import load_csv_datasets
from src.evaluation.metrics import compute_binary_metrics, write_confusion_matrix, write_dict_csv
from src.utils.seed import set_seed


def load_config(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as config_file:
        return yaml.safe_load(config_file)


def train(config_path: str | Path = "configs/transformer.yaml") -> dict[str, Any]:
    try:
        import numpy as np
        from datasets import Dataset
        from transformers import (
            AutoModelForSequenceClassification,
            AutoTokenizer,
            DataCollatorWithPadding,
            Trainer,
            TrainingArguments,
        )
    except ImportError as exc:
        raise RuntimeError(
            "Transformer training requires datasets, torch, and transformers. "
            "Install project dependencies with `python -m pip install -r requirements.txt`."
        ) from exc

    config = load_config(config_path)
    seed = int(config.get("seed", 42))
    set_seed(seed)

    data_config = config["data"]
    model_config = config["model"]
    training_config = config["training"]
    report_dir = Path(config["reports"]["output_dir"])
    report_dir.mkdir(parents=True, exist_ok=True)

    dataset = load_csv_datasets(
        _config_paths(data_config, "train_paths", "train_path"),
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

    train_dataset = Dataset.from_dict(
        {
            "text": [dataset.texts[index] for index in train_idx],
            "label": [dataset.labels[index] for index in train_idx],
        }
    )
    eval_texts = [dataset.texts[index] for index in test_idx]
    eval_labels = [dataset.labels[index] for index in test_idx]
    eval_attack_types = [dataset.attack_types[index] for index in test_idx]
    eval_dataset = Dataset.from_dict({"text": eval_texts, "label": eval_labels})

    tokenizer = AutoTokenizer.from_pretrained(model_config["name"])

    def tokenize(batch: dict[str, list[str]]) -> dict[str, Any]:
        return tokenizer(batch["text"], truncation=True, max_length=int(model_config["max_length"]))

    tokenized_train = train_dataset.map(tokenize, batched=True)
    tokenized_eval = eval_dataset.map(tokenize, batched=True)
    data_collator = DataCollatorWithPadding(tokenizer=tokenizer)

    model = AutoModelForSequenceClassification.from_pretrained(model_config["name"], num_labels=2)
    output_dir = Path(model_config["output_dir"])
    args = TrainingArguments(
        output_dir=str(output_dir),
        learning_rate=float(training_config["learning_rate"]),
        num_train_epochs=float(training_config["num_train_epochs"]),
        per_device_train_batch_size=int(training_config["per_device_train_batch_size"]),
        per_device_eval_batch_size=int(training_config["per_device_eval_batch_size"]),
        weight_decay=float(training_config["weight_decay"]),
        logging_steps=int(training_config["logging_steps"]),
        save_strategy=training_config["save_strategy"],
        eval_strategy=training_config.get("evaluation_strategy", "epoch"),
        load_best_model_at_end=bool(training_config["load_best_model_at_end"]),
        seed=seed,
        report_to=[],
    )

    def compute_metrics(eval_prediction: Any) -> dict[str, float]:
        logits, labels = eval_prediction
        predictions = np.argmax(logits, axis=-1).tolist()
        metrics = compute_binary_metrics(labels.tolist(), predictions)
        return {
            "accuracy": float(metrics["accuracy"]),
            "precision": float(metrics["precision"]),
            "recall": float(metrics["recall"]),
            "f1": float(metrics["f1"]),
            "fpr": float(metrics["fpr"]),
            "fnr": float(metrics["fnr"]),
        }

    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=tokenized_train,
        eval_dataset=tokenized_eval,
        tokenizer=tokenizer,
        data_collator=data_collator,
        compute_metrics=compute_metrics,
    )
    trainer.train()
    trainer.save_model(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))

    predictions_output = trainer.predict(tokenized_eval)
    probabilities = _softmax(predictions_output.predictions)
    scores = probabilities[:, 1].tolist()
    threshold = float(model_config["threshold"])
    predictions = [1 if score >= threshold else 0 for score in scores]
    metrics = compute_binary_metrics(eval_labels, predictions)

    metrics_row = {
        "model": model_config["name"],
        "threshold": threshold,
        **metrics,
    }
    write_dict_csv(report_dir / "transformer_metrics_summary.csv", [metrics_row])
    write_confusion_matrix(report_dir / "transformer_confusion_matrix.csv", metrics)
    _write_errors(report_dir, eval_texts, eval_labels, eval_attack_types, predictions, scores)
    _write_report(report_dir / "transformer_experiment_report.md", metrics_row, output_dir)
    return {"model_path": str(output_dir), "metrics": metrics_row}


def _softmax(logits: Any) -> Any:
    import numpy as np

    shifted = logits - np.max(logits, axis=1, keepdims=True)
    exp = np.exp(shifted)
    return exp / np.sum(exp, axis=1, keepdims=True)


def _config_paths(config: dict[str, Any], list_key: str, single_key: str) -> list[str]:
    value = config.get(list_key, config[single_key])
    if isinstance(value, list):
        return [str(path) for path in value]
    return [str(value)]


def _write_errors(
    report_dir: Path,
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
    write_dict_csv(report_dir / "transformer_false_positives.csv", [row for row in rows if row["actual"] == 0])
    write_dict_csv(report_dir / "transformer_false_negatives.csv", [row for row in rows if row["actual"] == 1])
    write_dict_csv(
        report_dir / "transformer_korean_obfuscation_results.csv",
        [
            {
                "text": text,
                "attack_type": attack_type,
                "actual": actual,
                "predicted": predicted,
                "score": round(float(score), 4),
            }
            for text, attack_type, actual, predicted, score in zip(texts, attack_types, labels, predictions, scores)
            if attack_type in {"OBFUSCATED_KOREAN_ATTACK", "MIXED_LANGUAGE_ATTACK"}
        ],
    )


def _write_report(path: Path, metrics: dict[str, Any], model_path: Path) -> None:
    content = f"""# Transformer Experiment Report

## 설정
- Model: `{metrics["model"]}`
- Saved checkpoint: `{model_path}`
- Detector: Transformer sequence classification

## 성능
- Accuracy: {metrics["accuracy"]:.4f}
- Precision: {metrics["precision"]:.4f}
- Recall: {metrics["recall"]:.4f}
- F1: {metrics["f1"]:.4f}
- FPR: {metrics["fpr"]:.4f}
- FNR: {metrics["fnr"]:.4f}

## 보안 관점 해석
Transformer 계층은 rule/ML이 놓칠 수 있는 문맥 기반 우회 표현을 보완하기 위한 정밀 탐지 계층이다. 운영 기준은 Accuracy보다 Recall과 FNR을 우선한다.

## 한계점
- 샘플 데이터만으로 학습하면 일반화 성능을 주장할 수 없다.
- 공개 데이터셋과 한국어 확장 데이터로 재학습해야 최종 연구 결과로 사용할 수 있다.

## 개선 방향
- XLM-RoBERTa와 KLUE-BERT 비교
- threshold sweep 기반 FNR 우선 운영점 선택
- hard negative와 한국어 우회형 test split 별도 평가
"""
    path.write_text(content, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Train Transformer prompt injection detector.")
    parser.add_argument("--config", default="configs/transformer.yaml")
    args = parser.parse_args()
    result = train(args.config)
    print(result)


if __name__ == "__main__":
    main()
