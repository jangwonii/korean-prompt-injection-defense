from __future__ import annotations

import argparse
import csv
from pathlib import Path


REQUIRED_COLUMNS = ["text", "label", "attack_type"]


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


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate prompt injection dataset schema.")
    parser.add_argument("--input", default="data/samples/prompt_injection_samples.csv")
    args = parser.parse_args()
    print(validate_dataset(args.input))


if __name__ == "__main__":
    main()
