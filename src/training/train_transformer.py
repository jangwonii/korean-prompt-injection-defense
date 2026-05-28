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
        import torch
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
    if bool(training_config.get("require_cuda", False)) and not torch.cuda.is_available():
        raise RuntimeError(
            "This training config requires CUDA, but torch.cuda.is_available() is false. "
            "Install a CUDA-enabled PyTorch build and run on a GPU machine."
        )

    train_data = load_csv_datasets(
        _config_paths(data_config, "train_paths", "train_path"),
        data_config["text_column"],
        data_config["label_column"],
        data_config["attack_type_column"],
    )
    eval_paths = _optional_config_paths(data_config, "eval_paths", "eval_path", "validation_path")
    test_paths = _optional_config_paths(data_config, "test_paths", "test_path")

    if eval_paths:
        eval_data = load_csv_datasets(
            eval_paths,
            data_config["text_column"],
            data_config["label_column"],
            data_config["attack_type_column"],
        )
        train_texts = train_data.texts
        train_labels = train_data.labels
        eval_texts = eval_data.texts
        eval_labels = eval_data.labels
        eval_attack_types = eval_data.attack_types
    else:
        indices = list(range(len(train_data.texts)))
        train_idx, eval_idx = train_test_split(
            indices,
            test_size=float(data_config["test_size"]),
            random_state=seed,
            stratify=train_data.labels,
        )
        train_texts = [train_data.texts[index] for index in train_idx]
        train_labels = [train_data.labels[index] for index in train_idx]
        eval_texts = [train_data.texts[index] for index in eval_idx]
        eval_labels = [train_data.labels[index] for index in eval_idx]
        eval_attack_types = [train_data.attack_types[index] for index in eval_idx]

    if test_paths:
        test_data = load_csv_datasets(
            test_paths,
            data_config["text_column"],
            data_config["label_column"],
            data_config["attack_type_column"],
        )
        report_texts = test_data.texts
        report_labels = test_data.labels
        report_attack_types = test_data.attack_types
        report_split_name = "test"
    else:
        report_texts = eval_texts
        report_labels = eval_labels
        report_attack_types = eval_attack_types
        report_split_name = "validation"

    train_dataset = Dataset.from_dict(
        {
            "text": train_texts,
            "label": train_labels,
        }
    )
    eval_dataset = Dataset.from_dict({"text": eval_texts, "label": eval_labels})
    report_dataset = Dataset.from_dict({"text": report_texts, "label": report_labels})

    tokenizer = AutoTokenizer.from_pretrained(model_config["name"])

    def tokenize(batch: dict[str, list[str]]) -> dict[str, Any]:
        return tokenizer(batch["text"], truncation=True, max_length=int(model_config["max_length"]))

    tokenized_train = train_dataset.map(tokenize, batched=True)
    tokenized_eval = eval_dataset.map(tokenize, batched=True)
    data_collator = DataCollatorWithPadding(tokenizer=tokenizer)

    model = AutoModelForSequenceClassification.from_pretrained(model_config["name"], num_labels=2)
    if bool(model_config.get("freeze_base_model", False)):
        base_model = getattr(model, model.base_model_prefix)
        for parameter in base_model.parameters():
            parameter.requires_grad = False
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

    trainer_kwargs = {
        "model": model,
        "args": args,
        "train_dataset": tokenized_train,
        "eval_dataset": tokenized_eval,
        "data_collator": data_collator,
        "compute_metrics": compute_metrics,
    }
    try:
        trainer = Trainer(**trainer_kwargs, processing_class=tokenizer)
    except TypeError:
        trainer = Trainer(**trainer_kwargs, tokenizer=tokenizer)
    trainer.train()
    trainer.save_model(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))

    tokenized_report = report_dataset.map(tokenize, batched=True)
    predictions_output = trainer.predict(tokenized_report)
    probabilities = _softmax(predictions_output.predictions)
    scores = probabilities[:, 1].tolist()
    threshold = float(model_config["threshold"])
    predictions = [1 if score >= threshold else 0 for score in scores]
    metrics = compute_binary_metrics(report_labels, predictions)

    metrics_row = {
        "model": model_config["name"],
        "threshold": threshold,
        "report_split": report_split_name,
        "train_rows": len(train_texts),
        "validation_rows": len(eval_texts),
        "test_rows": len(report_texts) if report_split_name == "test" else 0,
        **metrics,
    }
    write_dict_csv(report_dir / "transformer_metrics_summary.csv", [metrics_row])
    write_confusion_matrix(report_dir / "transformer_confusion_matrix.csv", metrics)
    _write_errors(report_dir, report_texts, report_labels, report_attack_types, predictions, scores)
    _write_report(
        report_dir / "transformer_experiment_report.md",
        metrics_row,
        output_dir,
        data_config,
        model_config,
        training_config,
    )
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


def _optional_config_paths(config: dict[str, Any], *keys: str) -> list[str]:
    for key in keys:
        if key not in config:
            continue
        value = config[key]
        if isinstance(value, list):
            return [str(path) for path in value]
        return [str(value)]
    return []


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


def _write_report(
    path: Path,
    metrics: dict[str, Any],
    model_path: Path,
    data_config: dict[str, Any],
    model_config: dict[str, Any],
    training_config: dict[str, Any],
) -> None:
    content = f"""# Transformer Experiment Report

## 설정
- Model: `{metrics["model"]}`
- Saved checkpoint: `{model_path}`
- Detector: Transformer sequence classification
- Dataset source: `{data_config.get("dataset_source", "not specified")}`
- Train dataset: `{data_config.get("train_path")}`
- Validation dataset: `{data_config.get("eval_path", data_config.get("validation_path", "random split"))}`
- Test dataset: `{data_config.get("test_path", metrics["report_split"])}`
- Report split: `{metrics["report_split"]}`
- Train rows: {metrics["train_rows"]}
- Validation rows: {metrics["validation_rows"]}
- Test rows: {metrics["test_rows"]}
- Max length: {model_config["max_length"]}
- Epochs: {training_config["num_train_epochs"]}
- Batch size: {training_config["per_device_train_batch_size"]}
- Freeze base model: {model_config.get("freeze_base_model", False)}

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
