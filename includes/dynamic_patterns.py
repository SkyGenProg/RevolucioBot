# -*- coding: utf-8 -*-
"""
Helpers for dynamic vandalism patterns generated from a labeled corpus.
"""

from __future__ import annotations

import difflib
import hashlib
import re
import unicodedata
from dataclasses import dataclass
from typing import Iterable, List

SPACE_RE = re.compile(r"\s+")
TOKEN_RE = re.compile(r"[a-z0-9à-öø-ÿ_'-]{4,40}", flags=re.IGNORECASE)

LEET_TRANSLATION = str.maketrans(
    {
        "0": "o",
        "1": "i",
        "2": "z",
        "3": "e",
        "4": "a",
        "5": "s",
        "6": "g",
        "7": "t",
        "8": "b",
        "9": "g",
        "@": "a",
        "$": "s",
        "!": "i",
    }
)

HOMOGLYPH_MAP = {
    "а": "a",
    "е": "e",
    "о": "o",
    "р": "p",
    "с": "c",
    "у": "y",
    "х": "x",
    "і": "i",
    "ј": "j",
    "ԁ": "d",
    "ｍ": "m",
    "ｏ": "o",
    "ｌ": "l",
    "ｉ": "i",
    "Ａ": "a",
    "Β": "b",
    "Ε": "e",
    "Ζ": "z",
    "Η": "h",
    "Ι": "i",
    "Κ": "k",
    "Μ": "m",
    "Ν": "n",
    "Ο": "o",
    "Ρ": "p",
    "Τ": "t",
    "Χ": "x",
    "Υ": "y",
}


@dataclass(frozen=True)
class DynamicRule:
    pattern: re.Pattern[str]
    score: int
    label: str
    support: int = 0
    precision: float = 0.0
    status: str = "active"


def normalize_detection_text(text: str) -> str:
    raw = unicodedata.normalize("NFKC", str(text or ""))
    replaced = "".join(HOMOGLYPH_MAP.get(ch, ch) for ch in raw)
    replaced = replaced.translate(LEET_TRANSLATION)
    lowered = replaced.casefold()
    return SPACE_RE.sub(" ", lowered).strip()


def tokenize_training_text(text: str, *, min_len: int = 4) -> list[str]:
    normalized = normalize_detection_text(text)
    tokens: list[str] = []
    for match in TOKEN_RE.finditer(normalized):
        token = match.group(0)
        if len(token) < min_len:
            continue
        tokens.append(token)
    return tokens


def extract_changed_text(old_text: str | None, new_text: str) -> tuple[str, str]:
    if old_text is None:
        return str(new_text or "").strip(), ""

    diff = difflib.unified_diff((old_text or "").splitlines(), (new_text or "").splitlines(), lineterm="")
    additions: list[str] = []
    deletions: list[str] = []

    for line in diff:
        if line.startswith("+++") or line.startswith("---"):
            continue
        if line.startswith("+"):
            additions.append(line[1:])
        elif line.startswith("-"):
            deletions.append(line[1:])

    return "\n".join(additions).strip(), "\n".join(deletions).strip()


def holdout_bucket(value: str) -> int:
    digest = hashlib.sha1(str(value).encode("utf-8")).hexdigest()[:8]
    return int(digest, 16) % 100


def phrase_candidates(tokens: Iterable[str], *, min_words: int = 2, max_words: int = 4) -> List[str]:
    token_list = [token for token in tokens if token]
    out: list[str] = []
    for size in range(min_words, max_words + 1):
        for i in range(len(token_list) - size + 1):
            out.append(" ".join(token_list[i : i + size]))
    return out


def escape_phrase_to_regex(phrase: str) -> str:
    words = [re.escape(part) for part in phrase.split() if part]
    if not words:
        return ""
    return r"\b" + r"\s+".join(words) + r"\b"


def parse_dynamic_rule_line(line: str) -> DynamicRule | None:
    parts = [part.strip() for part in line.split("\t")]
    if not parts or not parts[0]:
        return None
    pattern_text = parts[0]
    try:
        score = int(parts[1]) if len(parts) >= 2 and parts[1] else -2
    except ValueError:
        score = -2
    label = parts[2] if len(parts) >= 3 and parts[2] else "dynamic_regex"
    try:
        support = int(parts[3]) if len(parts) >= 4 and parts[3] else 0
    except ValueError:
        support = 0
    try:
        precision = float(parts[5]) if len(parts) >= 6 and parts[5] else 0.0
    except ValueError:
        precision = 0.0
    status = parts[6].strip().casefold() if len(parts) >= 7 and parts[6] else "active"
    if status not in {"active", "review"}:
        return None
    try:
        compiled = re.compile(pattern_text, flags=re.IGNORECASE)
    except re.error:
        return None
    return DynamicRule(
        pattern=compiled,
        score=score,
        label=label[:80],
        support=support,
        precision=precision,
        status=status,
    )
