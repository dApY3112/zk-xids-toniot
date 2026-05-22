#!/usr/bin/env python
"""Reference-vector sensitivity analysis for semantic-group Exact SHAP."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import numpy as np

from eval_exact_shap_semantic_groups import (
    REPO_ROOT,
    _exact_group_shap_from_deltas,
    _group_masks,
    _jaccard,
    _load_feature_names,
    _load_group_map,
    _load_lr_model,
    _score_deltas_by_group,
    _select_stage2_subset,
    _topk_groups,
)


OUT_CSV = REPO_ROOT / "outputs" / "explainability" / "exact_shap_reference_sensitivity.csv"
OUT_JSON = REPO_ROOT / "reports" / "exact_shap_reference_sensitivity.json"
OUT_MD = REPO_ROOT / "reports" / "exact_shap_reference_sensitivity.md"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _chunked_mean(X: np.ndarray, mask: np.ndarray | None = None, *, chunk_size: int = 100_000) -> np.ndarray:
    total = np.zeros(X.shape[1], dtype=np.float64)
    count = 0
    n = X.shape[0]
    for start in range(0, n, chunk_size):
        end = min(start + chunk_size, n)
        chunk = np.asarray(X[start:end], dtype=np.float64)
        if mask is not None:
            local = mask[start:end]
            if not np.any(local):
                continue
            chunk = chunk[local]
        total += np.sum(chunk, axis=0)
        count += chunk.shape[0]
    if count == 0:
        raise ValueError("Cannot compute mean over empty reference subset")
    return total / float(count)


def _freq(top_rows: Sequence[Sequence[str]]) -> Dict[str, int]:
    c = Counter()
    for row in top_rows:
        c.update(row)
    return dict(c)


def _reference_eval(
    *,
    name: str,
    x_ref: np.ndarray,
    X: np.ndarray,
    w: np.ndarray,
    base_score: float,
    masks: Sequence[np.ndarray],
    groups: Sequence[str],
) -> Dict[str, object]:
    closed = _score_deltas_by_group(X, w, x_ref, masks)
    phi = _exact_group_shap_from_deltas(closed, base_score)
    ids_rows: List[List[int]] = []
    name_rows: List[List[str]] = []
    for i in range(phi.shape[0]):
        ids, names = _topk_groups(phi[i], groups, k=3, use_abs=True)
        ids_rows.append(ids)
        name_rows.append(names)
    return {
        "name": name,
        "phi": phi,
        "top_ids": ids_rows,
        "top_names": name_rows,
        "frequency": _freq(name_rows),
    }


def _compare(base: Dict[str, object], other: Dict[str, object]) -> Dict[str, object]:
    overlaps: List[int] = []
    jaccards: List[float] = []
    changed = 0
    for a, b in zip(base["top_ids"], other["top_ids"]):
        sa = set(int(x) for x in a)
        sb = set(int(x) for x in b)
        overlaps.append(len(sa & sb))
        jaccards.append(_jaccard(sa, sb))
        if list(a) != list(b):
            changed += 1
    return {
        "reference": other["name"],
        "mean_overlap_count": float(np.mean(overlaps)),
        "mean_jaccard": float(np.mean(jaccards)),
        "ordered_top3_changed_count": int(changed),
        "ordered_top3_changed_rate": float(changed / len(overlaps)) if overlaps else 0.0,
    }


def write_reports(payload: Dict[str, object]) -> None:
    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    rows = payload["comparisons"]
    with OUT_CSV.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["reference", "mean_overlap_count", "mean_jaccard", "ordered_top3_changed_count", "ordered_top3_changed_rate"],
        )
        writer.writeheader()
        writer.writerows(rows)

    lines: List[str] = []
    lines.append("# Exact SHAP Reference Sensitivity\n\n")
    lines.append(f"Generated: {payload['created_utc']} (UTC)\n\n")
    lines.append(
        "This offline analysis tests how semantic-group Exact SHAP top-3 explanations change when the reference vector changes. "
        "The implemented Stage 3.4 circuit still verifies the training-mean reference only; alternative references are sensitivity "
        "checks, not additional ZK claims.\n\n"
    )
    lines.append(f"- Samples: `{payload['sample_count']}`\n")
    lines.append("- Baseline reference: `training_mean`\n")
    lines.append("- Alternative references: `zero_vector`, `normal_train_mean`\n\n")
    lines.append("## Top-3 Stability vs Training Mean\n\n")
    lines.append("| Reference | Mean overlap / 3 | Mean Jaccard | Ordered top-3 changed | Changed rate |\n")
    lines.append("|---|---:|---:|---:|---:|\n")
    for row in rows:
        lines.append(
            f"| {row['reference']} | {row['mean_overlap_count']:.4f} | {row['mean_jaccard']:.4f} | "
            f"{row['ordered_top3_changed_count']} | {100.0 * row['ordered_top3_changed_rate']:.2f}% |\n"
        )

    lines.append("\n## Group Frequency by Reference\n\n")
    lines.append("| Reference | Protocol | Application | ConnectionState | Ports | TrafficVolume |\n")
    lines.append("|---|---:|---:|---:|---:|---:|\n")
    for ref_name, freq in payload["frequencies"].items():
        lines.append(
            f"| {ref_name} | {freq.get('Protocol', 0)} | {freq.get('Application', 0)} | "
            f"{freq.get('ConnectionState', 0)} | {freq.get('Ports', 0)} | {freq.get('TrafficVolume', 0)} |\n"
        )

    lines.append("\n## Thesis Interpretation\n\n")
    lines.append(
        "Exact SHAP explanations depend on the reference vector used to replace masked groups. The training-set mean remains "
        "the implemented and verified reference because it is deterministic, public, and exported into the Stage 3.4 circuit. "
        "Sensitivity results should be used for critical self-assessment rather than as additional verified relations.\n"
    )
    OUT_MD.write_text("".join(lines), encoding="utf-8")


def build_arg_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=str(REPO_ROOT / "outputs" / "models" / "logreg_baseline.pkl"))
    ap.add_argument("--x-train", default=str(REPO_ROOT / "outputs" / "processed" / "X_train.npy"))
    ap.add_argument("--y-train", default=str(REPO_ROOT / "outputs" / "processed" / "y_train.npy"))
    ap.add_argument("--x-test", default=str(REPO_ROOT / "outputs" / "processed" / "X_test.npy"))
    ap.add_argument("--y-test", default=str(REPO_ROOT / "outputs" / "processed" / "y_test.npy"))
    ap.add_argument("--test-idx", default=str(REPO_ROOT / "outputs" / "splits" / "test_idx.npy"))
    ap.add_argument("--feature-names", default=str(REPO_ROOT / "outputs" / "processed" / "feature_order.json"))
    ap.add_argument("--group-map", default=str(REPO_ROOT / "stage3_zk" / "artifacts" / "group_map.json"))
    ap.add_argument("--random-state", type=int, default=42)
    ap.add_argument("--stage2-tp", type=int, default=1000)
    ap.add_argument("--stage2-fn", type=int, default=100)
    ap.add_argument("--fallback-n", type=int, default=500)
    return ap


def main(argv: Sequence[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    feature_names = _load_feature_names(Path(args.feature_names))
    groups, group_ids = _load_group_map(Path(args.group_map), len(feature_names))
    masks = _group_masks(group_ids, len(groups))
    model = _load_lr_model(Path(args.model))
    w = np.asarray(model.coef_[0], dtype=np.float64)
    b = float(model.intercept_[0])
    X_train = np.load(args.x_train, mmap_mode="r")
    y_train = np.load(args.y_train, mmap_mode="r")
    X_test = np.load(args.x_test, mmap_mode="r")
    y_test = np.load(args.y_test, mmap_mode="r")
    test_idx = np.load(args.test_idx, mmap_mode="r") if Path(args.test_idx).exists() else None

    print("Computing training-set mean reference...")
    training_mean = _chunked_mean(X_train)

    print("Selecting deterministic Stage 2-style subset...")
    selected, _tag = _select_stage2_subset(
        X_test=X_test,
        y_test=y_test,
        model=model,
        random_state=int(args.random_state),
        stage2_tp=int(args.stage2_tp),
        stage2_fn=int(args.stage2_fn),
        fallback_n=int(args.fallback_n),
    )
    X = np.asarray(X_test[selected], dtype=np.float64)
    base_score = float(np.dot(training_mean, w) + b)

    print("Computing reference vectors...")
    refs = {
        "training_mean": training_mean,
        "zero_vector": np.zeros(X.shape[1], dtype=np.float64),
        "normal_train_mean": _chunked_mean(X_train, np.asarray(y_train) == 0),
    }

    print("Evaluating top-3 sensitivity...")
    evaluations = {
        name: _reference_eval(name=name, x_ref=ref, X=X, w=w, base_score=base_score, masks=masks, groups=groups)
        for name, ref in refs.items()
    }
    base = evaluations["training_mean"]
    comparisons = [_compare(base, evaluations[name]) for name in ["zero_vector", "normal_train_mean"]]
    payload = {
        "created_utc": _utc_now_iso(),
        "sample_count": int(X.shape[0]),
        "subset_source": "reconstructed_stage2_lr_tp1000_fn100_seed42",
        "references": list(refs.keys()),
        "comparisons": comparisons,
        "frequencies": {name: ev["frequency"] for name, ev in evaluations.items()},
    }
    write_reports(payload)
    print(f"Wrote: {OUT_JSON}")
    print(f"Wrote: {OUT_MD}")
    print(f"Wrote: {OUT_CSV}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
