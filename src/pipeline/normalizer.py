from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


CHOSEONG = [
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
JUNGSEONG = [
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
JONGSEONG = [
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

VOWELS = set(JUNGSEONG)
CONSONANTS = set(CHOSEONG) | set(JONGSEONG[1:])

COMPACT_PHRASES = {
    "이 전 지 시": "이전 지시",
    "앞 의 명 령": "앞의 명령",
    "무 시 해": "무시해",
    "무 시": "무시",
    "시 스 템 프 롬 프 트": "시스템 프롬프트",
    "개 발 자 메 시 지": "개발자 메시지",
    "내 부 규 칙": "내부 규칙",
    "제 한 우 회": "제한 우회",
}


@dataclass(frozen=True)
class NormalizedInput:
    original: str
    normalized: str
    compact: str
    signals: list[str]


class InputNormalizer:
    """Normalize Korean prompt input while preserving evidence."""

    def normalize(self, text: str) -> NormalizedInput:
        original = text
        signals: list[str] = []

        if re.search(r"[ㄱ-ㅎㅏ-ㅣ]", text):
            signals.append("contains_korean_jamo")
            value = self._compose_jamo(text)
        else:
            value = text

        value = unicodedata.normalize("NFKC", value)
        value = value.lower()

        if re.search(r"\s{2,}", value):
            signals.append("repeated_whitespace")
        value = re.sub(r"\s+", " ", value).strip()

        compacted = value
        for spaced, joined in COMPACT_PHRASES.items():
            compacted = compacted.replace(spaced, joined)
        compacted = re.sub(r"(지시|명령|프롬프트)\s+(를|을)", r"\1\2", compacted)

        compact_no_space = re.sub(r"[\s\W_]+", "", compacted, flags=re.UNICODE)
        if compact_no_space != re.sub(r"[\s\W_]+", "", value, flags=re.UNICODE):
            signals.append("suspicious_spacing_compacted")

        cleaned = re.sub(r"[^\w\s가-힣ㄱ-ㅎㅏ-ㅣ]", " ", compacted, flags=re.UNICODE)
        if cleaned != compacted:
            signals.append("special_character_cleanup")
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        return NormalizedInput(
            original=original,
            normalized=cleaned,
            compact=compact_no_space,
            signals=signals,
        )

    def _compose_jamo(self, text: str) -> str:
        chars = list(text)
        output: list[str] = []
        i = 0
        while i < len(chars):
            current = chars[i]
            if current in CHOSEONG and i + 1 < len(chars) and chars[i + 1] in VOWELS:
                choseong = current
                jungseong = chars[i + 1]
                jongseong = ""
                consumed = 2

                if i + 2 < len(chars) and chars[i + 2] in CONSONANTS:
                    next_char = chars[i + 2]
                    next_next = chars[i + 3] if i + 3 < len(chars) else ""
                    if next_next not in VOWELS:
                        jongseong = next_char
                        consumed = 3

                output.append(self._compose_syllable(choseong, jungseong, jongseong))
                i += consumed
                continue

            output.append(current)
            i += 1

        return "".join(output)

    def _compose_syllable(self, choseong: str, jungseong: str, jongseong: str = "") -> str:
        if choseong not in CHOSEONG or jungseong not in JUNGSEONG or jongseong not in JONGSEONG:
            return choseong + jungseong + jongseong
        codepoint = (
            0xAC00
            + (CHOSEONG.index(choseong) * 21 + JUNGSEONG.index(jungseong)) * 28
            + JONGSEONG.index(jongseong)
        )
        return chr(codepoint)
