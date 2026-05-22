#!/usr/bin/env python
"""Semantic-group fairness ablation (sum vs mean normalization).

Stage 2 semantic grouping aggregates Top-k feature *indices* into 5 semantic groups.
However, groups have different numbers of features. A larger group has a higher
chance to appear in Top-k purely due to group size.

This script computes, for each model:
- Raw group presence: % of samples where the group appears at least once in Top-k.
- Size-normalized presence: raw_presence_pct / group_size.

Outputs:
- outputs/reports/semantic_group_ablation.json
- reports/semantic_group_ablation.md
- reports/figures/semantic_group_ablation_<model>.png
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Dict, List, Tuple

import numpy as np


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


@dataclass
class GroupStats:
    group: str
    group_id: int
    group_size: int
    present_count: int
    present_pct: float
    present_pct_per_feature: float


def _read_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _presence_by_group(topk_idx: np.ndarray, feature_index_to_group_id: List[int], groups: List[str]) -> List[GroupStats]:
    if topk_idx.ndim != 2:
        raise ValueError(f"Expected topk_idx to be 2D (n_samples, k). Got shape={topk_idx.shape}")

    n_samples, k = topk_idx.shape
    if n_samples <= 0 or k <= 0:
        raise ValueError(f"Invalid topk shape={topk_idx.shape}")

    # Validate indices (best-effort)
    n_features = len(feature_index_to_group_id)
    if int(topk_idx.min()) < 0 or int(topk_idx.max()) >= n_features:
        raise ValueError(
            f"Top-k feature indices out of range. min={int(topk_idx.min())}, max={int(topk_idx.max())}, n_features={n_features}"
        )

    # Group sizes
    gid_arr = np.array(feature_index_to_group_id, dtype=np.int32)
    group_ids_unique = sorted(set(int(x) for x in gid_arr.tolist()))

    # Some files use 1..n_groups ids; map group_id -> index in `groups` list (0-based)
    # We assume group_id values are consistent with group_map.json.
    gid_to_name = {i + 1: groups[i] for i in range(len(groups))}
    group_sizes: Dict[int, int] = {gid: int(np.sum(gid_arr == gid)) for gid in group_ids_unique}

    # Compute sample-level group presence
    topk_group_ids = gid_arr[topk_idx.astype(np.int32)]  # shape (n_samples, k)
    present_counts: Dict[int, int] = {}
    for gid in group_ids_unique:
        present_counts[gid] = int(np.sum(np.any(topk_group_ids == gid, axis=1)))

    stats: List[GroupStats] = []
    for gid in group_ids_unique:
        name = gid_to_name.get(gid, f"group_{gid}")
        size = int(group_sizes.get(gid, 0))
        cnt = int(present_counts.get(gid, 0))
        pct = float(cnt / n_samples * 100.0)
        pct_pf = float(pct / size) if size > 0 else 0.0
        stats.append(
            GroupStats(
                group=name,
                group_id=int(gid),
                group_size=size,
                present_count=cnt,
                present_pct=pct,
                present_pct_per_feature=pct_pf,
            )
        )
    return stats


def _rank_groups(stats: List[GroupStats], *, key: str) -> List[Tuple[str, float]]:
    if key == "sum":
        pairs = [(s.group, float(s.present_pct)) for s in stats]
    elif key == "mean":
        pairs = [(s.group, float(s.present_pct_per_feature)) for s in stats]
    else:
        raise ValueError("key must be one of: sum, mean")

    return sorted(pairs, key=lambda x: x[1], reverse=True)


def _plot(stats: List[GroupStats], title: str, out_path: str) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    groups = [s.group for s in stats]
    raw = [s.present_pct for s in stats]
    norm = [s.present_pct_per_feature for s in stats]

    fig, axes = plt.subplots(1, 2, figsize=(11, 4), constrained_layout=True)
    fig.suptitle(title)

    axes[0].bar(groups, raw)
    axes[0].set_title("Raw: % samples with group in Top-k")
    axes[0].set_ylabel("% of samples")
    axes[0].tick_params(axis="x", rotation=30)

    axes[1].bar(groups, norm)
    axes[1].set_title("Size-normalized: raw / group_size")
    axes[1].set_ylabel("(% samples) per feature")
    axes[1].tick_params(axis="x", rotation=30)

    _ensure_dir(os.path.dirname(out_path))
    fig.savefig(out_path, dpi=160)
    plt.close(fig)


def _write_markdown(
    *,
    out_md: str,
    created_utc: str,
    data_mode: str,
    results: Dict[str, Dict],
) -> None:
    lines: List[str] = []
    lines.append("# Semantic Group Ablation: Sum vs Mean (Size-Normalized)\n")
    lines.append(f"Generated: {created_utc} (UTC)\n")
    if data_mode:
        lines.append(f"Data mode: `{data_mode}`\n")

    lines.append("## What this measures\n")
    lines.append(
        "Stage 2 counts how often each **semantic group** appears in the per-sample Top-k explanation. "
        "Because groups contain different numbers of features, raw frequency can be biased toward larger groups.\n"
    )
    lines.append("We compare two scoring rules:\n")
    lines.append("- **Sum (raw):** % of samples where the group appears at least once in Top-k\n")
    lines.append("- **Mean (normalized):** (raw %) / (group_size)\n")

    for model_name, model_res in results.items():
        lines.append(f"## {model_name}\n")
        lines.append("### Group sizes and frequencies\n")
        lines.append("| Group | Size (#features) | Raw presence (% samples) | Normalized (raw/size) |\n")
        lines.append("|---|---:|---:|---:|\n")
        for row in model_res["rows"]:
            lines.append(
                f"| {row['group']} | {row['group_size']} | {row['present_pct']:.2f} | {row['present_pct_per_feature']:.4f} |\n"
            )

        lines.append("\n### Top-3 groups\n")
        top3_sum = model_res["rank_sum"][:3]
        top3_mean = model_res["rank_mean"][:3]
        lines.append("- Sum (raw): " + ", ".join([f"{g} ({v:.2f})" for g, v in top3_sum]) + "\n")
        lines.append("- Mean (normalized): " + ", ".join([f"{g} ({v:.4f})" for g, v in top3_mean]) + "\n")

        fig_path = model_res.get("figure", "")
        if fig_path:
            lines.append("\n### Figure\n")
            lines.append(f"- `{fig_path}`\n")

    _ensure_dir(os.path.dirname(out_md))
    with open(out_md, "w", encoding="utf-8") as f:
        f.writelines(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--group-map",
        default=os.path.join(REPO_ROOT, "stage3_zk", "artifacts", "group_map.json"),
        help="Path to group_map.json",
    )
    ap.add_argument(
        "--topk-logreg",
        default=os.path.join(REPO_ROOT, "outputs", "stage2", "topk_logreg.npy"),
        help="Path to topk_logreg.npy",
    )
    ap.add_argument(
        "--topk-xgb",
        default=os.path.join(REPO_ROOT, "outputs", "stage2", "topk_xgb.npy"),
        help="Path to topk_xgb.npy",
    )
    ap.add_argument(
        "--out-json",
        default=os.path.join(REPO_ROOT, "outputs", "reports", "semantic_group_ablation.json"),
        help="Output JSON path",
    )
    ap.add_argument(
        "--out-md",
        default=os.path.join(REPO_ROOT, "reports", "semantic_group_ablation.md"),
        help="Output Markdown report path",
    )
    args = ap.parse_args()

    group_map = _read_json(args.group_map)
    feature_index_to_group_id = group_map["feature_index_to_group_id"]
    groups = group_map["groups"]

    # The Stage 2 Top-k arrays are indices only (n_samples, k).
    topk_logreg = np.load(args.topk_logreg)
    topk_xgb = np.load(args.topk_xgb)

    created = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    data_mode = ""
    manifest_path = os.path.join(REPO_ROOT, "outputs", "splits", "data_manifest.json")
    if os.path.exists(manifest_path):
        try:
            data_mode = str(_read_json(manifest_path).get("mode", ""))
        except Exception:
            data_mode = ""

    results: Dict[str, Dict] = {}
    figures_dir = os.path.join(REPO_ROOT, "reports", "figures")
    _ensure_dir(figures_dir)

    for model_key, arr in [("logistic_regression", topk_logreg), ("xgboost", topk_xgb)]:
        stats = _presence_by_group(arr, feature_index_to_group_id, groups)
        # Keep a stable, readable group order: as defined in group_map.json
        group_order = {name: i for i, name in enumerate(groups)}
        stats_sorted = sorted(stats, key=lambda s: group_order.get(s.group, 10_000))

        fig_rel = os.path.join("reports", "figures", f"semantic_group_ablation_{model_key}.png")
        fig_abs = os.path.join(REPO_ROOT, fig_rel)
        _plot(stats_sorted, f"Semantic Group Ablation ({model_key})", fig_abs)

        results[model_key] = {
            "n_samples": int(arr.shape[0]),
            "k": int(arr.shape[1]),
            "rows": [asdict(s) for s in stats_sorted],
            "rank_sum": _rank_groups(stats_sorted, key="sum"),
            "rank_mean": _rank_groups(stats_sorted, key="mean"),
            "figure": fig_rel.replace("\\", "/"),
        }

    payload = {
        "created_utc": created,
        "data_mode": data_mode,
        "group_map": {
            "n_features": int(group_map.get("n_features", len(feature_index_to_group_id))),
            "n_groups": int(group_map.get("n_groups", len(groups))),
            "groups": list(groups),
        },
        "results": results,
    }

    _ensure_dir(os.path.dirname(args.out_json))
    with open(args.out_json, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    _write_markdown(
        out_md=args.out_md,
        created_utc=created,
        data_mode=data_mode,
        results={k: v for k, v in results.items()},
    )

    print(f"✅ Wrote: {args.out_json}")
    print(f"✅ Wrote: {args.out_md}")
    for model_key in results:
        print(f"✅ Figure: {results[model_key]['figure']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
