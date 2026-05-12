from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any

import yaml


REQUIRED_COLUMNS = ["text", "label", "attack_type"]
DEFAULT_INPUT_PATH = "data/samples/prompt_injection_samples.csv"


def validate_dataset(path: str | Path) -> dict[str, int]:
    dataset_path = Path(path)
    with dataset_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        fieldnames = reader.fieldnames or []
        missing = [column for column in REQUIRED_COLUMNS if column not in fieldnames]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        total = 0
        positives = 0
        negatives = 0
        for row in reader:
            total += 1
            if row["label"] == "1":
                positives += 1
            elif row["label"] == "0":
                negatives += 1
            else:
                raise ValueError(f"Invalid label: {row['label']}")

    return {"rows": total, "positive": positives, "negative": negatives}


def load_config(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as config_file:
        return yaml.safe_load(config_file) or {}


def resolve_input_path(input_path: str | None, config_path: str | None) -> str:
    if input_path:
        return input_path
    if not config_path:
        return DEFAULT_INPUT_PATH

    config = load_config(config_path)
    data_config = config.get("data", {})
    return str(data_config.get("train_path", DEFAULT_INPUT_PATH))


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate prompt injection dataset schema.")
    parser.add_argument("--config", help="YAML config containing data.train_path.")
    parser.add_argument("--input", help="Dataset CSV path. Overrides --config when both are provided.")
    args = parser.parse_args()
    print(validate_dataset(resolve_input_path(args.input, args.config)))


if __name__ == "__main__":
    main()
