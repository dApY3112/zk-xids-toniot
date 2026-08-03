#!/usr/bin/env python
"""Analyze Stage 3.4 Exact SHAP top-3 ranking margins."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = ROOT / "outputs"
REPORTS = ROOT / "reports"
STAGE3 = ROOT / "stage3_zk"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _split_path(split: str, kind: str) -> Path:
    if kind == "X":
        return OUTPUTS / "processed" / f"X_{split}.npy"
    if kind == "y":
        return OUTPUTS / "processed" / f"y_{split}.npy"
    if kind == "idx":
        return OUTPUTS / "splits" / f"{split}_idx.npy"
    raise ValueError(kind)


def _chunks(n: int, chunk_size: int) -> Iterable[Tuple[int, int]]:
    for start in range(0, n, chunk_size):
        yield start, min(start + chunk_size, n)


def _ordered_group_ids(abs_phi: np.ndarray) -> np.ndarray:
    group_ids = np.broadcast_to(np.arange(1, abs_phi.shape[1] + 1), abs_phi.shape)
    return (np.lexsort((group_ids, -abs_phi), axis=1) + 1).astype(np.int16)


def _stats(values: np.ndarray) -> Dict[str, float]:
    if values.size == 0:
        return {k: 0.0 for k in ["min", "p1", "p5", "p10", "median", "mean", "p90", "p95", "p99", "max"]}
    return {
        "min": float(np.min(values)),
        "p1": float(np.percentile(values, 1)),
        "p5": float(np.percentile(values, 5)),
        "p10": float(np.percentile(values, 10)),
        "median": float(np.median(values)),
        "mean": float(np.mean(values)),
        "p90": float(np.percentile(values, 90)),
        "p95": float(np.percentile(values, 95)),
        "p99": float(np.percentile(values, 99)),
        "max": float(np.max(values)),
    }


def _fmt(x: float) -> str:
    if abs(x) >= 1e4 or (abs(x) > 0 and abs(x) < 1e-4):
        return f"{x:.6e}"
    return f"{x:.6f}"


def _example(
    *,
    split: str,
    row_in_split: int,
    dataset_index: int,
    y_true: int,
    margin_int: int,
    scale: float,
    ordered_ids: Sequence[int],
    phi: Sequence[int],
    groups: Sequence[str],
) -> Dict[str, Any]:
    top3 = [int(x) for x in ordered_ids[:3]]
    rank4 = int(ordered_ids[3])
    phi_by_rank = [int(phi[int(gid) - 1]) for gid in ordered_ids]
    names = [groups[int(gid) - 1] for gid in ordered_ids]
    return {
        "split": split,
        "row_in_split": int(row_in_split),
        "dataset_index": int(dataset_index),
        "y_true": int(y_true),
        "margin_int": int(margin_int),
        "margin_scaled": float(margin_int / scale),
        "top3_ids": ",".join(str(x) for x in top3),
        "rank4_id": rank4,
        "ordered_group_names": ";".join(names),
        "phi_int_by_rank": ",".join(str(x) for x in phi_by_rank),
    }


def evaluate_split(
    *,
    split: str,
    model_public: Dict[str, Any],
    group_map: Dict[str, Any],
    reference: Dict[str, Any],
    chunk_size: int,
    max_examples: int,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    X = np.load(_split_path(split, "X"), mmap_mode="r")
    y = np.load(_split_path(split, "y"), mmap_mode="r")
    idx = np.load(_split_path(split, "idx"), mmap_mode="r")

    sx = int(model_public["Sx"])
    sw = int(model_public["Sw"])
    scale = float(sx * sw)
    w_int = np.asarray(model_public["w_int"], dtype=np.int64)
    x_ref_int = np.asarray(reference["x_ref_int"], dtype=np.int64)
    group_ids = np.asarray(group_map["feature_index_to_group_id"], dtype=np.int16)
    groups = list(group_map["groups"])
    n_groups = int(group_map["n_groups"])

    margins: List[np.ndarray] = []
    rel_margins: List[np.ndarray] = []
    examples: List[Dict[str, Any]] = []

    for start, end in _chunks(int(X.shape[0]), chunk_size):
        Xc = np.asarray(X[start:end], dtype=np.float64)
        yc = np.asarray(y[start:end], dtype=np.int8)
        idxc = np.asarray(idx[start:end], dtype=np.int64)
        x_int = np.rint(Xc * sx).astype(np.int64)

        phi = np.zeros((end - start, n_groups), dtype=np.int64)
        for gid in range(1, n_groups + 1):
            mask = group_ids == gid
            phi[:, gid - 1] = (x_int[:, mask] - x_ref_int[mask]) @ w_int[mask]

        abs_phi = np.abs(phi)
        ordered_ids = _ordered_group_ids(abs_phi)
        ordered_abs = np.take_along_axis(abs_phi, ordered_ids.astype(np.int64) - 1, axis=1)
        margin = (ordered_abs[:, 2] - ordered_abs[:, 3]).astype(np.int64)
        denom = np.maximum(ordered_abs[:, 2].astype(np.float64), 1.0)
        rel = margin.astype(np.float64) / denom
        margins.append(margin.astype(np.float64) / scale)
        rel_margins.append(rel)

        local_k = min(max_examples, len(margin))
        if local_k:
            candidate_idx = np.argpartition(margin, local_k - 1)[:local_k]
            for local in candidate_idx.tolist():
                examples.append(
                    _example(
                        split=split,
                        row_in_split=start + local,
                        dataset_index=int(idxc[local]),
                        y_true=int(yc[local]),
                        margin_int=int(margin[local]),
                        scale=scale,
                        ordered_ids=ordered_ids[local],
                        phi=phi[local],
                        groups=groups,
                    )
                )

    margin_scaled = np.concatenate(margins) if margins else np.zeros((0,), dtype=np.float64)
    rel_margin = np.concatenate(rel_margins) if rel_margins else np.zeros((0,), dtype=np.float64)
    thresholds = [0.0, 0.001, 0.01, 0.1, 1.0]
    threshold_counts = {
        str(t): {
            "count": int(np.sum(margin_scaled <= t)),
            "rate": float(np.mean(margin_scaled <= t)) if margin_scaled.size else 0.0,
        }
        for t in thresholds
    }
    examples = sorted(examples, key=lambda row: (row["margin_int"], row["split"], row["row_in_split"]))[:max_examples]
    return (
        {
            "split": split,
            "n": int(X.shape[0]),
            "margin_scaled_stats": _stats(margin_scaled),
            "relative_margin_stats": _stats(rel_margin),
            "small_margin_thresholds_scaled": threshold_counts,
        },
        examples,
    )


def write_examples(path: Path, examples: Sequence[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "split",
        "row_in_split",
        "dataset_index",
        "y_true",
        "margin_int",
        "margin_scaled",
        "top3_ids",
        "rank4_id",
        "ordered_group_names",
        "phi_int_by_rank",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in examples:
            writer.writerow(row)


def write_md(path: Path, payload: Dict[str, Any], examples: Sequence[Dict[str, Any]]) -> None:
    lines: List[str] = []
    lines.append("# Exact SHAP Top-3 Ranking Margin Analysis\n\n")
    lines.append(f"Generated: {payload['created_utc']} (UTC)\n\n")
    lines.append("## Purpose\n\n")
    lines.append(
        "Stage 3.4 proves that the public top-3 semantic group IDs are a valid non-increasing ranking by "
        "absolute quantized Exact SHAP value. This report measures the empirical gap between rank 3 and rank 4. "
        "A small gap means the certified ranking is correct for the current input, but may be fragile under "
        "small input, reference, or quantization changes.\n\n"
    )

    lines.append("## Margin Definition\n\n")
    lines.append("```text\nmargin = abs(phi_rank3_int) - abs(phi_rank4_int)\nmargin_scaled = margin / (Sx * Sw)\nrelative_margin = margin / max(abs(phi_rank3_int), 1)\n```\n\n")

    lines.append("## Margin Distribution\n\n")
    lines.append("| Split | n | min | p1 | p5 | p10 | median | mean | p95 | max |\n")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n")
    for row in payload["splits"]:
        s = row["margin_scaled_stats"]
        lines.append(
            f"| {row['split']} | {row['n']} | {_fmt(s['min'])} | {_fmt(s['p1'])} | {_fmt(s['p5'])} "
            f"| {_fmt(s['p10'])} | {_fmt(s['median'])} | {_fmt(s['mean'])} | {_fmt(s['p95'])} | {_fmt(s['max'])} |\n"
        )

    lines.append("\n## Small-Margin Counts\n\n")
    lines.append("| Split | <=0 | <=0.001 | <=0.01 | <=0.1 | <=1.0 |\n")
    lines.append("|---|---:|---:|---:|---:|---:|\n")
    for row in payload["splits"]:
        t = row["small_margin_thresholds_scaled"]
        cells = []
        for key in ["0.0", "0.001", "0.01", "0.1", "1.0"]:
            cell = t[key]
            cells.append(f"{cell['count']} ({cell['rate'] * 100:.4f}%)")
        lines.append(f"| {row['split']} | " + " | ".join(cells) + " |\n")

    lines.append("\n## Smallest-Margin Examples\n\n")
    lines.append("Full examples are written to `outputs/reports/exact_shap_ranking_margin_examples.csv`.\n\n")
    lines.append("| Split | row | dataset_idx | y_true | margin_scaled | top3 | rank4 | ordered groups |\n")
    lines.append("|---|---:|---:|---:|---:|---|---:|---|\n")
    for row in examples[:12]:
        lines.append(
            f"| {row['split']} | {row['row_in_split']} | {row['dataset_index']} | {row['y_true']} "
            f"| {_fmt(row['margin_scaled'])} | {row['top3_ids']} | {row['rank4_id']} | {row['ordered_group_names']} |\n"
        )

    lines.append("\n## Thesis Interpretation\n\n")
    lines.append(
        "The current circuit correctly certifies a top-3 ranking for the supplied private input, but it does not "
        "certify robustness of that ranking. Report this margin analysis as empirical self-assessment: large margins "
        "support stable explanations, while near-zero margins identify cases where the third and fourth groups are "
        "nearly tied and the explanation should be interpreted cautiously.\n"
    )

    path.write_text("".join(lines), encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--splits", default="val,test", help="Comma-separated splits to evaluate.")
    parser.add_argument("--chunk-size", type=int, default=50000, help="Rows per chunk.")
    parser.add_argument("--max-examples", type=int, default=20, help="Number of smallest-margin examples to store.")
    args = parser.parse_args(argv)

    model_public = _read_json(STAGE3 / "artifacts" / "model_public.json")
    group_map = _read_json(STAGE3 / "artifacts" / "group_map.json")
    reference = _read_json(STAGE3 / "artifacts" / "exact_shap_reference.json")

    payload: Dict[str, Any] = {
        "created_utc": _utc_now_iso(),
        "Sx": int(model_public["Sx"]),
        "Sw": int(model_public["Sw"]),
        "splits": [],
    }
    all_examples: List[Dict[str, Any]] = []
    for split in [part.strip() for part in args.splits.split(",") if part.strip()]:
        metrics, examples = evaluate_split(
            split=split,
            model_public=model_public,
            group_map=group_map,
            reference=reference,
            chunk_size=int(args.chunk_size),
            max_examples=int(args.max_examples),
        )
        payload["splits"].append(metrics)
        all_examples.extend(examples)
    all_examples = sorted(all_examples, key=lambda row: (row["margin_int"], row["split"], row["row_in_split"]))[: int(args.max_examples)]

    out_json = OUTPUTS / "reports" / "exact_shap_ranking_margin.json"
    out_examples = OUTPUTS / "reports" / "exact_shap_ranking_margin_examples.csv"
    out_md = REPORTS / "exact_shap_ranking_margin.md"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    with out_json.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    write_examples(out_examples, all_examples)
    write_md(out_md, payload, all_examples)

    print(f"Wrote: {out_json}")
    print(f"Wrote: {out_examples}")
    print(f"Wrote: {out_md}")
    for row in payload["splits"]:
        s = row["margin_scaled_stats"]
        print(f"{row['split']}: median margin={s['median']:.6f}, p5={s['p5']:.6f}, min={s['min']:.6f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
