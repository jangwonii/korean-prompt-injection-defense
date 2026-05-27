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
    return load_csv_datasets([path], text_column, label_column, attack_type_column)


def load_csv_datasets(
    paths: list[str | Path],
    text_column: str = "text",
    label_column: str = "label",
    attack_type_column: str = "attack_type",
) -> Dataset:
    texts: list[str] = []
    labels: list[int] = []
    attack_types: list[str] = []
    seen: dict[str, tuple[int, str]] = {}

    if not paths:
        raise ValueError("At least one dataset path is required.")

    for path in paths:
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
                label = int(row[label_column])
                attack_type = row[attack_type_column].strip() or "UNKNOWN"
                existing = seen.get(text)
                if existing:
                    if existing != (label, attack_type):
                        raise ValueError(f"Conflicting duplicate dataset row for text: {text}")
                    continue
                seen[text] = (label, attack_type)
                texts.append(text)
                labels.append(label)
                attack_types.append(attack_type)

    if len(set(labels)) < 2:
        raise ValueError("Dataset must contain both benign and injection labels.")

    return Dataset(texts=texts, labels=labels, attack_types=attack_types)
