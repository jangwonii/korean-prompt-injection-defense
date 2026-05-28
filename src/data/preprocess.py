from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any

import yaml

from src.data.load_datasets import load_csv_datasets


REQUIRED_COLUMNS = ["text", "label", "attack_type"]
DEFAULT_INPUT_PATH = "data/samples/prompt_injection_samples.csv"


def validate_dataset(path: str | Path) -> dict[str, int]:
    return validate_datasets([path])


def validate_datasets(paths: list[str | Path]) -> dict[str, int]:
    for path in paths:
        with Path(path).open("r", encoding="utf-8-sig", newline="") as csv_file:
            reader = csv.DictReader(csv_file)
            fieldnames = reader.fieldnames or []
            missing = [column for column in REQUIRED_COLUMNS if column not in fieldnames]
            if missing:
                raise ValueError(f"Missing required columns in {path}: {missing}")

            for row in reader:
                if row["label"] not in {"0", "1"}:
                    raise ValueError(f"Invalid label in {path}: {row['label']}")

    dataset = load_csv_datasets(paths)
    positives = sum(dataset.labels)
    negatives = len(dataset.labels) - positives
    return {"rows": len(dataset.labels), "positive": positives, "negative": negatives}


def load_config(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as config_file:
        return yaml.safe_load(config_file) or {}


def resolve_input_path(input_path: str | None, config_path: str | None) -> str:
    return resolve_input_paths(input_path, config_path)[0]


def resolve_input_paths(input_path: str | None, config_path: str | None) -> list[str]:
    if input_path:
        return [input_path]
    if not config_path:
        return [DEFAULT_INPUT_PATH]

    config = load_config(config_path)
    data_config = config.get("data", {})
    configured_paths = (
        data_config.get("eval_paths")
        or data_config.get("train_paths")
        or data_config.get("eval_path")
        or data_config.get("test_path")
        or data_config.get("train_path")
        or DEFAULT_INPUT_PATH
    )
    if isinstance(configured_paths, list):
        return [str(path) for path in configured_paths]
    return [str(configured_paths)]


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate prompt injection dataset schema.")
    parser.add_argument("--config", help="YAML config containing data.train_path.")
    parser.add_argument("--input", help="Dataset CSV path. Overrides --config when both are provided.")
    args = parser.parse_args()
    print(validate_datasets(resolve_input_paths(args.input, args.config)))


if __name__ == "__main__":
    main()
