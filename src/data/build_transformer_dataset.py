from __future__ import annotations

import argparse
import csv
import random
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from datasets import load_dataset


FIELDNAMES = ["text", "label", "attack_type", "source"]
LOCAL_SAMPLE_PATHS = [
    "data/samples/prompt_injection_samples.csv",
    "data/samples/local_eval_extension.csv",
]


class DatasetWriter:
    def __init__(self) -> None:
        self.rows: dict[str, list[dict[str, Any]]] = {"train": [], "validation": [], "test": []}
        self.seen: set[str] = set()
        self.sources: list[dict[str, Any]] = []

    def add_many(self, split: str, rows: Iterable[dict[str, Any]], source: str) -> None:
        before = len(self.rows[split])
        for row in rows:
            self.add(split, row["text"], row["label"], row["attack_type"], source)
        self.sources.append({"source": source, "split": split, "rows": len(self.rows[split]) - before})

    def add(self, split: str, text: str, label: int, attack_type: str, source: str) -> None:
        normalized_text = " ".join(str(text).strip().split())
        if not normalized_text:
            return
        key = normalized_text.lower()
        if key in self.seen:
            return
        self.seen.add(key)
        self.rows[split].append(
            {
                "text": normalized_text,
                "label": int(label),
                "attack_type": attack_type or "UNKNOWN",
                "source": source,
            }
        )

    def write(self, output_dir: Path) -> dict[str, dict[str, int]]:
        output_dir.mkdir(parents=True, exist_ok=True)
        summary: dict[str, dict[str, int]] = {}
        for split, rows in self.rows.items():
            with (output_dir / f"{split}.csv").open("w", encoding="utf-8-sig", newline="") as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=FIELDNAMES)
                writer.writeheader()
                writer.writerows(rows)
            positive = sum(int(row["label"]) for row in rows)
            summary[split] = {"rows": len(rows), "positive": positive, "negative": len(rows) - positive}

        with (output_dir / "dataset_sources.csv").open("w", encoding="utf-8-sig", newline="") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=["source", "split", "rows"])
            writer.writeheader()
            writer.writerows(self.sources)
        return summary


def build_dataset(output_dir: str | Path, seed: int = 42, max_korean_safe_per_split: int = 3000) -> dict[str, dict[str, int]]:
    random.seed(seed)
    writer = DatasetWriter()

    _add_neuralchemy(writer)
    _add_deepset(writer)
    _add_wambosec(writer)
    _add_prism_guardrail_ko(writer, max_safe_per_split=max_korean_safe_per_split)
    _add_advbench_korean(writer)
    _add_local_samples(writer)

    return writer.write(Path(output_dir))


def _add_neuralchemy(writer: DatasetWriter) -> None:
    dataset = load_dataset("neuralchemy/Prompt-injection-dataset", "core")
    for split in ["train", "validation", "test"]:
        rows = []
        for item in dataset[split]:
            label = int(item["label"])
            rows.append(
                {
                    "text": item["text"],
                    "label": label,
                    "attack_type": "BENIGN" if label == 0 else str(item.get("category") or "PROMPT_INJECTION").upper(),
                }
            )
        writer.add_many(split, rows, "neuralchemy/Prompt-injection-dataset:core")


def _add_deepset(writer: DatasetWriter) -> None:
    dataset = load_dataset("deepset/prompt-injections")
    train_rows = [
        {
            "text": item["text"],
            "label": int(item["label"]),
            "attack_type": "BENIGN" if int(item["label"]) == 0 else "PROMPT_INJECTION",
        }
        for item in dataset["train"]
    ]
    writer.add_many("train", train_rows, "deepset/prompt-injections:train")

    test_rows = [
        {
            "text": item["text"],
            "label": int(item["label"]),
            "attack_type": "BENIGN" if int(item["label"]) == 0 else "PROMPT_INJECTION",
        }
        for item in dataset["test"]
    ]
    random.shuffle(test_rows)
    midpoint = len(test_rows) // 2
    writer.add_many("validation", test_rows[:midpoint], "deepset/prompt-injections:test-half")
    writer.add_many("test", test_rows[midpoint:], "deepset/prompt-injections:test-half")


def _add_wambosec(writer: DatasetWriter) -> None:
    dataset = load_dataset("wambosec/prompt-injections")
    train_rows = [_wambosec_row(item) for item in dataset["train"]]
    writer.add_many("train", train_rows, "wambosec/prompt-injections:train")

    test_rows = [_wambosec_row(item) for item in dataset["test"]]
    random.shuffle(test_rows)
    midpoint = len(test_rows) // 2
    writer.add_many("validation", test_rows[:midpoint], "wambosec/prompt-injections:test-half")
    writer.add_many("test", test_rows[midpoint:], "wambosec/prompt-injections:test-half")


def _wambosec_row(item: dict[str, Any]) -> dict[str, Any]:
    label = 1 if bool(item["is_malicious"]) else 0
    return {
        "text": item["prompt"],
        "label": label,
        "attack_type": "BENIGN" if label == 0 else str(item.get("category") or "PROMPT_INJECTION").upper(),
    }


def _add_prism_guardrail_ko(writer: DatasetWriter, max_safe_per_split: int) -> None:
    dataset = load_dataset("prismdata/guardrail-ko-11class-dataset")
    for split in ["train", "validation", "test"]:
        safe_rows = []
        attack_rows = []
        for item in dataset[split]:
            label_name = str(item["label"])
            if label_name == "INJECTION":
                attack_rows.append({"text": item["text"], "label": 1, "attack_type": "KOREAN_PROMPT_INJECTION"})
            elif label_name == "SAFE" and len(safe_rows) < max_safe_per_split:
                safe_rows.append({"text": item["text"], "label": 0, "attack_type": "BENIGN"})
        writer.add_many(split, attack_rows, "prismdata/guardrail-ko-11class-dataset:INJECTION")
        writer.add_many(split, safe_rows, "prismdata/guardrail-ko-11class-dataset:SAFE_SAMPLE")


def _add_advbench_korean(writer: DatasetWriter) -> None:
    dataset = load_dataset("leo-bjpark/AdvBench-Korean")
    rows = [{"text": item["prompt"], "label": 1, "attack_type": "KOREAN_ADVERSARIAL"} for item in dataset["train"]]
    writer.add_many("train", rows, "leo-bjpark/AdvBench-Korean:train")


def _add_local_samples(writer: DatasetWriter) -> None:
    rows = []
    for path in LOCAL_SAMPLE_PATHS:
        with Path(path).open("r", encoding="utf-8-sig", newline="") as csv_file:
            rows.extend(
                {
                    "text": row["text"],
                    "label": int(row["label"]),
                    "attack_type": row["attack_type"],
                }
                for row in csv.DictReader(csv_file)
            )
    writer.add_many("train", rows, "local curated Korean samples")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build multi-source Transformer training CSV splits.")
    parser.add_argument("--output-dir", default="data/processed/transformer_multi_source_korean_20ep")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-korean-safe-per-split", type=int, default=3000)
    args = parser.parse_args()
    print(build_dataset(args.output_dir, args.seed, args.max_korean_safe_per_split))


if __name__ == "__main__":
    main()
