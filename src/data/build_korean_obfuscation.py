from __future__ import annotations

import argparse
import csv
from pathlib import Path


HANGUL_BASE = 0xAC00
HANGUL_END = 0xD7A3
INITIALS = [
    "ㄱ",
    "ㄲ",
    "ㄴ",
    "ㄷ",
    "ㄸ",
    "ㄹ",
    "ㅁ",
    "ㅂ",
    "ㅃ",
    "ㅅ",
    "ㅆ",
    "ㅇ",
    "ㅈ",
    "ㅉ",
    "ㅊ",
    "ㅋ",
    "ㅌ",
    "ㅍ",
    "ㅎ",
]
MEDIALS = [
    "ㅏ",
    "ㅐ",
    "ㅑ",
    "ㅒ",
    "ㅓ",
    "ㅔ",
    "ㅕ",
    "ㅖ",
    "ㅗ",
    "ㅘ",
    "ㅙ",
    "ㅚ",
    "ㅛ",
    "ㅜ",
    "ㅝ",
    "ㅞ",
    "ㅟ",
    "ㅠ",
    "ㅡ",
    "ㅢ",
    "ㅣ",
]
FINALS = [
    "",
    "ㄱ",
    "ㄲ",
    "ㄳ",
    "ㄴ",
    "ㄵ",
    "ㄶ",
    "ㄷ",
    "ㄹ",
    "ㄺ",
    "ㄻ",
    "ㄼ",
    "ㄽ",
    "ㄾ",
    "ㄿ",
    "ㅀ",
    "ㅁ",
    "ㅂ",
    "ㅄ",
    "ㅅ",
    "ㅆ",
    "ㅇ",
    "ㅈ",
    "ㅊ",
    "ㅋ",
    "ㅌ",
    "ㅍ",
    "ㅎ",
]


def split_hangul_syllable(character: str) -> str:
    code = ord(character)
    if code < HANGUL_BASE or code > HANGUL_END:
        return character

    offset = code - HANGUL_BASE
    initial = offset // 588
    medial = (offset % 588) // 28
    final = offset % 28
    return INITIALS[initial] + MEDIALS[medial] + FINALS[final]


def split_korean_jamo(text: str) -> str:
    return "".join(split_hangul_syllable(character) for character in text)


def add_suspicious_spacing(text: str) -> str:
    return " ".join(text)


def insert_separators(text: str, separator: str = ".") -> str:
    return separator.join(text)


def build_variants(text: str) -> list[tuple[str, str]]:
    return [
        ("jamo_split", split_korean_jamo(text)),
        ("suspicious_spacing", add_suspicious_spacing(text)),
        ("separator_insertion", insert_separators(text)),
    ]


def build_obfuscation_dataset(input_path: str | Path, output_path: str | Path) -> int:
    input_file = Path(input_path)
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with input_file.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        rows = list(reader)
        fieldnames = list(reader.fieldnames or [])

    output_fieldnames = list(dict.fromkeys([*fieldnames, "source_text", "variant_type"]))
    generated: list[dict[str, str]] = []

    for row in rows:
        if row.get("label") != "1":
            continue
        source_text = row["text"]
        for variant_type, variant_text in build_variants(source_text):
            generated_row = dict(row)
            generated_row["text"] = variant_text
            generated_row["source_text"] = source_text
            generated_row["variant_type"] = variant_type
            if generated_row.get("attack_type") == "DIRECT_INJECTION":
                generated_row["attack_type"] = "OBFUSCATED_KOREAN_ATTACK"
            generated.append(generated_row)

    with output_file.open("w", encoding="utf-8-sig", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=output_fieldnames)
        writer.writeheader()
        writer.writerows(generated)

    return len(generated)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Korean obfuscation prompt injection samples.")
    parser.add_argument("--input", default="data/samples/prompt_injection_samples.csv")
    parser.add_argument("--output", default="data/processed/korean_obfuscation.csv")
    args = parser.parse_args()
    count = build_obfuscation_dataset(args.input, args.output)
    print({"output": args.output, "rows": count})


if __name__ == "__main__":
    main()
