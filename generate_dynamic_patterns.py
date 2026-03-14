# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import csv
import json
import os
import re
from collections import Counter
from datetime import datetime, timezone

from includes.dynamic_patterns import (
    escape_phrase_to_regex,
    extract_changed_text,
    holdout_bucket,
    normalize_detection_text,
    phrase_candidates,
    tokenize_training_text,
)


def _utc_iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _files_dir() -> str:
    return "." if os.path.basename(os.getcwd()) == "files" else "files"


def _safe_bool(value: object) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _load_rows(csv_file: str) -> list[dict[str, str]]:
    with open(csv_file, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _collect_texts(rows: list[dict[str, str]], holdout_ratio: int) -> tuple[list[str], list[str], list[str], list[str], Counter[str], Counter[str]]:
    train_positives: list[str] = []
    train_negatives: list[str] = []
    holdout_positives: list[str] = []
    holdout_negatives: list[str] = []
    token_counter: Counter[str] = Counter()
    phrase_counter: Counter[str] = Counter()

    for row in rows:
        old_text = row.get("old") or ""
        new_text = row.get("new") or ""
        added_text, _removed_text = extract_changed_text(old_text, new_text)
        focus_raw = added_text if added_text else new_text
        focus = normalize_detection_text(focus_raw)
        if not focus:
            continue

        reverted = _safe_bool(row.get("reverted"))
        bucket_seed = row.get("revid") or row.get("diff") or row.get("page") or focus[:100]
        in_holdout = holdout_bucket(bucket_seed) < holdout_ratio

        if reverted:
            if in_holdout:
                holdout_positives.append(focus)
            else:
                train_positives.append(focus)
                tokens = tokenize_training_text(focus)
                token_counter.update(tokens)
                phrase_counter.update(phrase_candidates(tokens))
        else:
            if in_holdout:
                holdout_negatives.append(focus)
            else:
                train_negatives.append(focus)

    return train_positives, train_negatives, holdout_positives, holdout_negatives, token_counter, phrase_counter


def _precision_for_pattern(pattern: str, positives: list[str], negatives: list[str]) -> tuple[int, int, float]:
    try:
        regex = re.compile(pattern, flags=re.IGNORECASE)
    except re.error:
        return 0, 0, 0.0

    support = sum(1 for text in positives if regex.search(text))
    false_hits = sum(1 for text in negatives if regex.search(text))
    precision = support / (support + false_hits) if (support + false_hits) else 0.0
    return support, false_hits, precision


def _score_from_precision(precision: float) -> int:
    if precision >= 0.96:
        return -4
    if precision >= 0.90:
        return -3
    return -2


def _build_rules(
    token_counter: Counter[str],
    phrase_counter: Counter[str],
    *,
    positives: list[str],
    negatives: list[str],
    min_token_hits: int,
    min_phrase_hits: int,
    min_precision: float,
    review_support_threshold: int,
    max_rules: int,
) -> list[dict[str, object]]:
    candidate_patterns: list[tuple[str, str, int]] = []

    for token, count in token_counter.items():
        if count >= min_token_hits:
            candidate_patterns.append((rf"\b{re.escape(token)}\b", f"token:{token}", count))
    for phrase, count in phrase_counter.items():
        if count >= min_phrase_hits:
            pattern = escape_phrase_to_regex(phrase)
            if pattern:
                candidate_patterns.append((pattern, f"phrase:{phrase}", count))

    dedup: dict[str, tuple[str, int]] = {}
    for pattern, label, count in candidate_patterns:
        previous = dedup.get(pattern)
        if previous is None or count > previous[1]:
            dedup[pattern] = (label, count)

    rules: list[dict[str, object]] = []
    for pattern, (label, raw_count) in dedup.items():
        support, false_hits, precision = _precision_for_pattern(pattern, positives, negatives)
        if support <= 0 or precision < min_precision:
            continue
        status = "active" if support >= review_support_threshold else "review"
        rules.append(
            {
                "pattern": pattern,
                "score": _score_from_precision(precision),
                "label": label,
                "support": support,
                "false_hits": false_hits,
                "precision": round(precision, 4),
                "raw_count": raw_count,
                "status": status,
            }
        )

    rules.sort(key=lambda rule: (rule["precision"], rule["support"], -rule["false_hits"]), reverse=True)
    return rules[:max_rules]


def _evaluate_rules(rules: list[dict[str, object]], positives: list[str], negatives: list[str]) -> dict[str, float]:
    compiled: list[re.Pattern[str]] = []
    for rule in rules:
        try:
            compiled.append(re.compile(str(rule.get("pattern", "")), flags=re.IGNORECASE))
        except re.error:
            continue

    if not compiled:
        return {"precision": 0.0, "recall": 0.0, "fpr": 0.0}

    tp = sum(1 for text in positives if any(regex.search(text) for regex in compiled))
    fp = sum(1 for text in negatives if any(regex.search(text) for regex in compiled))
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / len(positives) if positives else 0.0
    fpr = fp / len(negatives) if negatives else 0.0
    return {"precision": round(precision, 4), "recall": round(recall, 4), "fpr": round(fpr, 4)}


def _write_common_patterns(path: str, token_counter: Counter[str], phrase_counter: Counter[str], positives_count: int, negatives_count: int) -> None:
    lines = [
        f"# generated_at_utc: {_utc_iso_now()}",
        f"# positive_texts: {positives_count}",
        f"# negative_texts: {negatives_count}",
        "# format: token<TAB>count",
        "",
    ]
    for token, count in token_counter.most_common(250):
        lines.append(f"{token}\t{count}")
    lines.extend(["", "# top_phrases format: phrase<TAB>count", ""])
    for phrase, count in phrase_counter.most_common(200):
        lines.append(f"{phrase}\t{count}")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines).strip() + "\n")


def _write_regex_patterns(path: str, rules: list[dict[str, object]], positives_count: int, negatives_count: int) -> None:
    lines = [
        f"# generated_at_utc: {_utc_iso_now()}",
        f"# positive_texts: {positives_count}",
        f"# negative_texts: {negatives_count}",
        "# format: regex<TAB>score<TAB>label<TAB>support<TAB>false_hits<TAB>precision<TAB>status",
        "",
    ]
    for rule in rules:
        lines.append(
            f"{rule['pattern']}\t{rule['score']}\t{rule['label']}\t"
            f"{rule['support']}\t{rule['false_hits']}\t{rule['precision']:.4f}\t{rule['status']}"
        )
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines).strip() + "\n")


def generate_from_csv(
    *,
    wiki: str,
    lang: str,
    csv_file: str,
    holdout_ratio: int = 20,
    min_token_hits: int = 2,
    min_phrase_hits: int = 3,
    min_precision: float = 0.78,
    review_support_threshold: int = 5,
    max_rules: int = 180,
) -> dict[str, object]:
    rows = _load_rows(csv_file)
    os.makedirs(_files_dir(), exist_ok=True)

    (
        train_positives,
        train_negatives,
        holdout_positives,
        holdout_negatives,
        token_counter,
        phrase_counter,
    ) = _collect_texts(rows, holdout_ratio)

    rules = _build_rules(
        token_counter,
        phrase_counter,
        positives=train_positives,
        negatives=train_negatives,
        min_token_hits=min_token_hits,
        min_phrase_hits=min_phrase_hits,
        min_precision=min_precision,
        review_support_threshold=review_support_threshold,
        max_rules=max_rules,
    )
    validation = _evaluate_rules(rules, holdout_positives, holdout_negatives)

    common_path = os.path.join(_files_dir(), f"dynamic_common_patterns_{wiki}_{lang}.txt")
    regex_path = os.path.join(_files_dir(), f"dynamic_patterns_{wiki}_{lang}.txt")
    validation_path = os.path.join(_files_dir(), f"dynamic_patterns_validation_{wiki}_{lang}.json")

    _write_common_patterns(common_path, token_counter, phrase_counter, len(train_positives), len(train_negatives))
    _write_regex_patterns(regex_path, rules, len(train_positives), len(train_negatives))
    with open(validation_path, "w", encoding="utf-8") as handle:
        json.dump(
            {
                "generated_at_utc": _utc_iso_now(),
                "train_positive_count": len(train_positives),
                "train_negative_count": len(train_negatives),
                "holdout_positive_count": len(holdout_positives),
                "holdout_negative_count": len(holdout_negatives),
                "rules_count": len(rules),
                "precision": validation["precision"],
                "recall": validation["recall"],
                "false_positive_rate": validation["fpr"],
            },
            handle,
            ensure_ascii=False,
            indent=2,
        )
        handle.write("\n")

    return {
        "common_path": common_path,
        "regex_path": regex_path,
        "validation_path": validation_path,
        "rules_count": len(rules),
        "precision": validation["precision"],
        "recall": validation["recall"],
        "false_positive_rate": validation["fpr"],
        "train_positive_count": len(train_positives),
        "train_negative_count": len(train_negatives),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate dynamic vandalism patterns from a labeled CSV corpus.")
    parser.add_argument("--wiki", required=True)
    parser.add_argument("--lang", required=True)
    parser.add_argument("--csv_file", required=True)
    parser.add_argument("--holdout_ratio", type=int, default=20)
    parser.add_argument("--min_token_hits", type=int, default=2)
    parser.add_argument("--min_phrase_hits", type=int, default=3)
    parser.add_argument("--min_precision", type=float, default=0.78)
    parser.add_argument("--review_support_threshold", type=int, default=5)
    parser.add_argument("--max_rules", type=int, default=180)
    args = parser.parse_args()

    result = generate_from_csv(
        wiki=args.wiki,
        lang=args.lang,
        csv_file=args.csv_file,
        holdout_ratio=args.holdout_ratio,
        min_token_hits=args.min_token_hits,
        min_phrase_hits=args.min_phrase_hits,
        min_precision=args.min_precision,
        review_support_threshold=args.review_support_threshold,
        max_rules=args.max_rules,
    )

    print(f"Common patterns: {result['common_path']}")
    print(f"Dynamic rules: {result['regex_path']}")
    print(f"Validation: {result['validation_path']}")
    print(
        "Summary:",
        json.dumps(
            {
                "rules_count": result["rules_count"],
                "precision": result["precision"],
                "recall": result["recall"],
                "false_positive_rate": result["false_positive_rate"],
            },
            ensure_ascii=False,
        ),
    )


if __name__ == "__main__":
    main()
