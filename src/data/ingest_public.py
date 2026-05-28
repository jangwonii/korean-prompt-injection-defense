from __future__ import annotations

import argparse
import csv
import hashlib
import random
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from src.evaluation.metrics import write_dict_csv


DEFAULT_DATASET = "neuralchemy/Prompt-injection-dataset"
DEFAULT_CONFIG = "core"
DEFAULT_SPLIT = "train"


@dataclass(frozen=True)
class PublicDatasetRow:
    text: str
    label: int
    attack_type: str
    source: str
    severity: str
    group_id: str
    original_category: str
    original_label: str

    def as_dict(self, split: str | None = None) -> dict[str, str | int]:
        row: dict[str, str | int] = {
            "text": self.text,
            "label": self.label,
            "attack_type": self.attack_type,
            "source": self.source,
            "severity": self.severity,
            "group_id": self.group_id,
            "original_category": self.original_category,
            "original_label": self.original_label,
        }
        if split is not None:
            row["split"] = split
        return row


def load_huggingface_rows(
    dataset_name: str = DEFAULT_DATASET,
    config_name: str | None = DEFAULT_CONFIG,
    split: str = DEFAULT_SPLIT,
    limit: int | None = None,
) -> list[PublicDatasetRow]:
    try:
        from datasets import load_dataset
    except ImportError as exc:
        raise RuntimeError("Install `datasets` with `python -m pip install -r requirements.txt`.") from exc

    dataset_args = [dataset_name]
    if config_name:
        dataset_args.append(config_name)
    dataset = load_dataset(*dataset_args, split=split)

    rows: list[PublicDatasetRow] = []
    for index, item in enumerate(dataset):
        if limit is not None and index >= limit:
            break
        normalized = normalize_public_row(item)
        if normalized is not None:
            rows.append(normalized)
    if len({row.label for row in rows}) < 2:
        raise ValueError("Ingested dataset must contain both benign and injection labels.")
    return rows


def load_csv_rows(path: str | Path, limit: int | None = None) -> list[PublicDatasetRow]:
    rows: list[PublicDatasetRow] = []
    with Path(path).open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        for index, item in enumerate(reader):
            if limit is not None and index >= limit:
                break
            normalized = normalize_public_row(item)
            if normalized is not None:
                rows.append(normalized)
    if len({row.label for row in rows}) < 2:
        raise ValueError("Ingested dataset must contain both benign and injection labels.")
    return rows


def normalize_public_row(item: dict[str, Any]) -> PublicDatasetRow | None:
    text = _first_text(item)
    if not text:
        return None

    label_value = item.get("label", item.get("is_malicious", item.get("malicious", "")))
    label = normalize_label(label_value)
    category = str(item.get("category", item.get("original_category", item.get("attack_type", ""))) or "").strip()
    source = str(item.get("source", "") or "").strip()
    severity = str(item.get("severity", "") or "").strip()
    group_id = str(item.get("group_id", "") or "").strip()
    if not group_id:
        group_id = stable_group_id(text, category, source)

    return PublicDatasetRow(
        text=text,
        label=label,
        attack_type="BENIGN" if label == 0 else map_attack_type(category, text),
        source=source or "unknown",
        severity=severity or "unknown",
        group_id=group_id,
        original_category=category or "unknown",
        original_label=str(label_value),
    )


def normalize_label(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return 1 if value == 1 else 0
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "malicious", "attack", "injection", "jailbreak"}:
        return 1
    if normalized in {"0", "false", "no", "benign", "safe", "normal"}:
        return 0
    raise ValueError(f"Unsupported public dataset label: {value!r}")


def map_attack_type(category: str, text: str = "") -> str:
    value = f"{category} {text}".lower()
    category_key = category.lower().replace("-", "_").replace(" ", "_")
    category_mapping = {
        "direct_injection": "DIRECT_INJECTION",
        "instruction_override": "DIRECT_INJECTION",
        "prompt_leaking": "SYSTEM_PROMPT_EXTRACTION",
        "prompt_leak": "SYSTEM_PROMPT_EXTRACTION",
        "prompt_extraction": "SYSTEM_PROMPT_EXTRACTION",
        "system_prompt_extraction": "SYSTEM_PROMPT_EXTRACTION",
        "policy_bypass": "POLICY_BYPASS",
        "jailbreak": "JAILBREAK",
        "role_play": "ROLE_PLAY_ATTACK",
        "roleplay": "ROLE_PLAY_ATTACK",
        "data_exfiltration": "DATA_EXFILTRATION",
        "tool_misuse": "TOOL_MISUSE",
        "obfuscation": "OBFUSCATED_KOREAN_ATTACK",
        "encoding": "OBFUSCATED_KOREAN_ATTACK",
        "encoding_obfuscation": "OBFUSCATED_KOREAN_ATTACK",
        "multilingual": "MIXED_LANGUAGE_ATTACK",
        "adversarial": "DIRECT_INJECTION",
        "agent_manipulation": "DIRECT_INJECTION",
        "context_confusion": "DIRECT_INJECTION",
        "control": "DIRECT_INJECTION",
        "many_shot": "DIRECT_INJECTION",
        "output_manipulation": "DIRECT_INJECTION",
        "prompt_injection": "DIRECT_INJECTION",
        "response_manipulation": "DIRECT_INJECTION",
        "system_manipulation": "DIRECT_INJECTION",
        "chain_of_thought": "SYSTEM_PROMPT_EXTRACTION",
        "system_extraction": "SYSTEM_PROMPT_EXTRACTION",
        "training_extraction": "SYSTEM_PROMPT_EXTRACTION",
        "code_execution": "TOOL_MISUSE",
        "payload_injection": "TOOL_MISUSE",
        "rag_poisoning": "TOOL_MISUSE",
        "crescendo": "JAILBREAK",
        "model_fingerprinting": "UNKNOWN_SUSPICIOUS",
    }
    if category_key in category_mapping:
        return category_mapping[category_key]

    mapping = [
        (("direct", "injection"), "DIRECT_INJECTION"),
        (("system", "prompt", "leak"), "SYSTEM_PROMPT_EXTRACTION"),
        (("prompt", "leak"), "SYSTEM_PROMPT_EXTRACTION"),
        (("prompt", "extract"), "SYSTEM_PROMPT_EXTRACTION"),
        (("developer", "message"), "SYSTEM_PROMPT_EXTRACTION"),
        (("hidden", "instruction"), "SYSTEM_PROMPT_EXTRACTION"),
        (("credential",), "DATA_EXFILTRATION"),
        (("api key",), "DATA_EXFILTRATION"),
        (("token",), "DATA_EXFILTRATION"),
        (("secret",), "DATA_EXFILTRATION"),
        (("tool",), "TOOL_MISUSE"),
        (("file",), "TOOL_MISUSE"),
        (("function",), "TOOL_MISUSE"),
        (("bypass",), "POLICY_BYPASS"),
        (("policy",), "POLICY_BYPASS"),
        (("guardrail",), "POLICY_BYPASS"),
        (("jailbreak",), "JAILBREAK"),
        (("dan",), "JAILBREAK"),
        (("role",), "ROLE_PLAY_ATTACK"),
        (("persona",), "ROLE_PLAY_ATTACK"),
        (("ignore", "instruction"), "DIRECT_INJECTION"),
        (("instruction", "override"), "DIRECT_INJECTION"),
        (("obfuscat",), "OBFUSCATED_KOREAN_ATTACK"),
        (("unicode",), "OBFUSCATED_KOREAN_ATTACK"),
        (("multilingual",), "MIXED_LANGUAGE_ATTACK"),
    ]
    for terms, attack_type in mapping:
        if all(term in value for term in terms):
            return attack_type
    return "UNKNOWN_SUSPICIOUS"


def split_group_aware(
    rows: list[PublicDatasetRow],
    train_ratio: float = 0.8,
    dev_ratio: float = 0.1,
    seed: int = 42,
) -> dict[str, list[PublicDatasetRow]]:
    if train_ratio <= 0 or dev_ratio < 0 or train_ratio + dev_ratio >= 1:
        raise ValueError("Expected train_ratio > 0, dev_ratio >= 0, and train_ratio + dev_ratio < 1.")

    groups: dict[str, list[PublicDatasetRow]] = defaultdict(list)
    for row in rows:
        groups[row.group_id].append(row)

    grouped_rows = list(groups.values())
    rng = random.Random(seed)
    rng.shuffle(grouped_rows)

    total = len(rows)
    train_target = round(total * train_ratio)
    dev_target = round(total * dev_ratio)
    splits: dict[str, list[PublicDatasetRow]] = {"train": [], "dev": [], "test": []}

    for group in grouped_rows:
        if len(splits["train"]) < train_target:
            splits["train"].extend(group)
        elif len(splits["dev"]) < dev_target:
            splits["dev"].extend(group)
        else:
            splits["test"].extend(group)

    for name, split_rows in splits.items():
        if len({row.label for row in split_rows}) < 2:
            raise ValueError(f"Split `{name}` must contain both labels; add data or change split ratios.")
    return splits


def write_public_dataset(
    rows: list[PublicDatasetRow],
    raw_output: str | Path,
    output_dir: str | Path,
    prefix: str,
    train_ratio: float,
    dev_ratio: float,
    seed: int,
) -> dict[str, Any]:
    raw_path = Path(raw_output)
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    write_dict_csv(raw_path, [row.as_dict() for row in rows])

    splits = split_group_aware(rows, train_ratio=train_ratio, dev_ratio=dev_ratio, seed=seed)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    split_paths: dict[str, str] = {}
    for split_name, split_rows in splits.items():
        path = output / f"{prefix}_{split_name}.csv"
        write_dict_csv(path, [row.as_dict(split_name) for row in split_rows])
        split_paths[split_name] = str(path)

    return {
        "raw_path": str(raw_path),
        "split_paths": split_paths,
        "summary": summarize_rows(rows),
        "splits": {name: summarize_rows(split_rows) for name, split_rows in splits.items()},
    }


def summarize_rows(rows: Iterable[PublicDatasetRow]) -> dict[str, int]:
    total = 0
    positive = 0
    negative = 0
    for row in rows:
        total += 1
        if row.label == 1:
            positive += 1
        else:
            negative += 1
    return {"rows": total, "positive": positive, "negative": negative}


def _first_text(item: dict[str, Any]) -> str:
    for key in ("text", "prompt", "instruction", "input", "content"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def stable_group_id(text: str, category: str, source: str) -> str:
    digest = hashlib.sha256(f"{source}\n{category}\n{text}".encode("utf-8")).hexdigest()
    return digest[:16]


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest a public prompt-injection dataset into project CSV splits.")
    parser.add_argument("--dataset", default=DEFAULT_DATASET, help="Hugging Face dataset name.")
    parser.add_argument("--config", default=DEFAULT_CONFIG, help="Optional Hugging Face dataset config name.")
    parser.add_argument("--split", default=DEFAULT_SPLIT, help="Hugging Face split to load.")
    parser.add_argument("--input-csv", help="Existing normalized/raw CSV to remap and split without network access.")
    parser.add_argument("--limit", type=int, help="Optional row limit for smoke ingestion.")
    parser.add_argument("--raw-output", default="data/raw/neuralchemy_core.csv")
    parser.add_argument("--output-dir", default="data/processed")
    parser.add_argument("--prefix", default="public_prompt_injection")
    parser.add_argument("--train-ratio", type=float, default=0.8)
    parser.add_argument("--dev-ratio", type=float, default=0.1)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    if args.input_csv:
        rows = load_csv_rows(args.input_csv, limit=args.limit)
    else:
        rows = load_huggingface_rows(
            dataset_name=args.dataset,
            config_name=args.config or None,
            split=args.split,
            limit=args.limit,
        )
    result = write_public_dataset(
        rows,
        raw_output=args.raw_output,
        output_dir=args.output_dir,
        prefix=args.prefix,
        train_ratio=args.train_ratio,
        dev_ratio=args.dev_ratio,
        seed=args.seed,
    )
    print(result)


if __name__ == "__main__":
    main()
