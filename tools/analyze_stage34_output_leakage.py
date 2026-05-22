#!/usr/bin/env python
"""Audit the intentional public-output leakage of Stage 3.4 explanations."""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = REPO_ROOT / "outputs" / "explainability" / "exact_shap_semantic_groups.csv"
OUT_JSON = REPO_ROOT / "reports" / "stage34_output_leakage_audit.json"
OUT_MD = REPO_ROOT / "reports" / "stage34_output_leakage_audit.md"
GROUPS = ["Protocol", "Application", "ConnectionState", "Ports", "TrafficVolume"]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _entropy(counter: Counter, total: int) -> float:
    if total <= 0:
        return 0.0
    out = 0.0
    for count in counter.values():
        if count:
            p = count / total
            out -= p * math.log2(p)
    return out


def _top_items(counter: Counter, n: int = 10) -> List[Dict[str, object]]:
    return [{"value": str(k), "count": int(v)} for k, v in counter.most_common(n)]


def _pct(count: int, total: int) -> str:
    return f"{(100.0 * count / total):.2f}%" if total else "0.00%"


def _load_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _parse_groups(value: str) -> List[str]:
    return [x for x in str(value).split(";") if x]


def analyze(rows: Sequence[Dict[str, str]]) -> Dict[str, object]:
    n = len(rows)
    y_hat = Counter(row["predicted_label"] for row in rows)
    y_true = Counter(row.get("true_label", "") for row in rows)
    sequence = Counter(row["exact_top3_groups"] for row in rows)
    first_group = Counter(_parse_groups(row["exact_top3_groups"])[0] for row in rows)
    membership = Counter()
    by_true: Dict[str, Counter] = defaultdict(Counter)
    by_pred: Dict[str, Counter] = defaultdict(Counter)
    seq_by_true: Dict[str, Counter] = defaultdict(Counter)
    seq_by_pred: Dict[str, Counter] = defaultdict(Counter)
    for row in rows:
        groups = _parse_groups(row["exact_top3_groups"])
        for group in groups:
            membership[group] += 1
            by_true[row.get("true_label", "")][group] += 1
            by_pred[row.get("predicted_label", "")][group] += 1
        seq_by_true[row.get("true_label", "")][row["exact_top3_groups"]] += 1
        seq_by_pred[row.get("predicted_label", "")][row["exact_top3_groups"]] += 1

    return {
        "created_utc": _utc_now_iso(),
        "sample_count": n,
        "predicted_label_counts": dict(y_hat),
        "true_label_counts": dict(y_true),
        "predicted_label_entropy_bits": _entropy(y_hat, n),
        "exact_top3_sequence_entropy_bits": _entropy(sequence, n),
        "unique_exact_top3_sequences": len(sequence),
        "top_exact_top3_sequences": _top_items(sequence, 10),
        "first_group_counts": dict(first_group),
        "top3_membership_counts": {group: int(membership[group]) for group in GROUPS},
        "top3_membership_rate": {group: float(membership[group] / n) if n else 0.0 for group in GROUPS},
        "membership_by_true_label": {label: dict(counter) for label, counter in by_true.items()},
        "membership_by_predicted_label": {label: dict(counter) for label, counter in by_pred.items()},
        "top_sequence_by_true_label": {label: _top_items(counter, 5) for label, counter in seq_by_true.items()},
        "top_sequence_by_predicted_label": {label: _top_items(counter, 5) for label, counter in seq_by_pred.items()},
    }


def write_reports(payload: Dict[str, object]) -> None:
    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    n = int(payload["sample_count"])
    lines: List[str] = []
    lines.append("# Stage 3.4 Output Leakage Audit\n\n")
    lines.append(f"Generated: {payload['created_utc']} (UTC)\n\n")
    lines.append(
        "Stage 3.4 intentionally reveals the public prediction `y_hat` and the top-3 semantic group IDs. "
        "It does not reveal raw input features or exact semantic-group SHAP magnitudes. This audit summarizes "
        "the information carried by those public explanation outputs on the Exact SHAP evaluation subset.\n\n"
    )
    lines.append(f"- Samples audited: `{n}`\n")
    lines.append(f"- Predicted-label entropy: `{payload['predicted_label_entropy_bits']:.4f}` bits\n")
    lines.append(f"- Exact top-3 sequence entropy: `{payload['exact_top3_sequence_entropy_bits']:.4f}` bits\n")
    lines.append(f"- Unique Exact SHAP top-3 sequences: `{payload['unique_exact_top3_sequences']}` out of 60 possible ordered sequences\n\n")

    lines.append("## Public Prediction Distribution\n\n")
    lines.append("| Predicted label | Count | Rate |\n|---:|---:|---:|\n")
    for label, count in sorted(payload["predicted_label_counts"].items()):
        lines.append(f"| {label} | {count} | {_pct(int(count), n)} |\n")

    lines.append("\n## Top-3 Group Membership\n\n")
    lines.append("| Group | Count in top-3 | Rate |\n|---|---:|---:|\n")
    for group in GROUPS:
        count = int(payload["top3_membership_counts"].get(group, 0))
        lines.append(f"| {group} | {count} | {_pct(count, n)} |\n")

    lines.append("\n## Most Frequent Ordered Top-3 Explanations\n\n")
    lines.append("| Rank | Ordered top-3 groups | Count | Rate |\n|---:|---|---:|---:|\n")
    for idx, item in enumerate(payload["top_exact_top3_sequences"], start=1):
        count = int(item["count"])
        lines.append(f"| {idx} | {item['value']} | {count} | {_pct(count, n)} |\n")

    lines.append("\n## Thesis Interpretation\n\n")
    lines.append(
        "The public explanation is deliberately low-dimensional: a binary prediction plus three semantic group IDs. "
        "This is useful for SOC auditability, but it is still output leakage. The correct privacy claim is therefore "
        "input-feature privacy with intentional disclosure of the certified decision and semantic explanation summary, "
        "not complete behavioral secrecy.\n"
    )
    OUT_MD.write_text("".join(lines), encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=str(CSV_PATH))
    args = ap.parse_args(argv)
    rows = _load_rows(Path(args.csv))
    payload = analyze(rows)
    write_reports(payload)
    print(f"Wrote: {OUT_JSON}")
    print(f"Wrote: {OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
