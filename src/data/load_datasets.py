from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Dataset:
    texts: list[str]
    labels: list[int]
    attack_types: list[str]


def load_csv_dataset(
    path: str | Path,
    text_column: str = "text",
    label_column: str = "label",
    attack_type_column: str = "attack_type",
) -> Dataset:
    texts: list[str] = []
    labels: list[int] = []
    attack_types: list[str] = []

    with Path(path).open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        required = {text_column, label_column, attack_type_column}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Missing required dataset columns: {sorted(missing)}")

        for row in reader:
            text = row[text_column].strip()
            if not text:
                continue
            texts.append(text)
            labels.append(int(row[label_column]))
            attack_types.append(row[attack_type_column].strip() or "UNKNOWN")

    if len(set(labels)) < 2:
        raise ValueError("Dataset must contain both benign and injection labels.")

    return Dataset(texts=texts, labels=labels, attack_types=attack_types)
