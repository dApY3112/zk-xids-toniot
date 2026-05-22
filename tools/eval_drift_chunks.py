#!/usr/bin/env python
"""Drift / robustness check by ordered chunks.

Motivation (thesis):
- IDS models face distribution shift (time drift, different capture periods, etc.).
- Even without explicit timestamps, we can approximate an ordered axis using the
  original sample indices from `outputs/splits/test_idx.npy`.
- We then evaluate metric stability across contiguous chunks.

This script:
- Loads frozen arrays `X_val/y_val`, `X_test/y_test` and `test_idx.npy`.
- Reorders test samples by ascending `test_idx` (proxy for original order).
- Splits into K contiguous chunks.
- For each chunk, reports key metrics at:
    * default threshold 0.5
    * tuned operating point (balanced MCC) chosen on validation

Outputs:
- JSON: outputs/reports/drift_chunks.json
- MD: reports/drift_chunks.md
- Figures: reports/figures/drift_chunks_<model>.png

Run (recommended):
  conda run -n py310 python tools/eval_drift_chunks.py
"""

from __future__ import annotations

import argparse
import json
import os
import platform
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _safe_div(num: float, den: float) -> float:
    return 0.0 if den == 0 else float(num) / float(den)


def _confusion(y_true: np.ndarray, y_prob_attack: np.ndarray, threshold: float) -> Tuple[int, int, int, int]:
    y_true = y_true.astype(np.int8)
    y_pred = (y_prob_attack >= threshold).astype(np.int8)
    tp = int(np.sum((y_true == 1) & (y_pred == 1)))
    tn = int(np.sum((y_true == 0) & (y_pred == 0)))
    fp = int(np.sum((y_true == 0) & (y_pred == 1)))
    fn = int(np.sum((y_true == 1) & (y_pred == 0)))
    return tn, fp, fn, tp


def _mcc(tn: int, fp: int, fn: int, tp: int) -> float:
    numer = (tp * tn) - (fp * fn)
    denom = float((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    if denom <= 0:
        return 0.0
    return float(numer) / float(np.sqrt(denom))


def _metrics(y_true: np.ndarray, y_prob_attack: np.ndarray, threshold: float) -> Dict[str, Any]:
    tn, fp, fn, tp = _confusion(y_true, y_prob_attack, threshold)
    total = tn + fp + fn + tp
    tpr = _safe_div(tp, tp + fn)  # attack recall
    tnr = _safe_div(tn, tn + fp)  # specificity
    fpr = _safe_div(fp, fp + tn)
    bacc = 0.5 * (tpr + tnr)
    mcc = _mcc(tn, fp, fn, tp)
    return {
        "threshold": float(threshold),
        "confusion": {"tn": tn, "fp": fp, "fn": fn, "tp": tp},
        "metrics": {
            "attack_recall": tpr,
            "normal_recall_specificity": tnr,
            "fpr": fpr,
            "balanced_accuracy": bacc,
            "mcc": mcc,
            "support": int(total),
            "attack_pct": 100.0 * _safe_div(tp + fn, total),
        },
    }


def _balanced_mcc_threshold(y_val: np.ndarray, p_val: np.ndarray) -> float:
    """Choose threshold on validation that maximizes MCC."""
    from sklearn.metrics import roc_curve

    fpr, tpr, thr = roc_curve(y_val.astype(np.int8), p_val.astype(np.float64), pos_label=1)
    _ = (fpr, tpr)  # not used directly, but keeps intent clear

    best_mcc = -1.0
    best_thr = 0.5
    for t in thr:
        tn, fp, fn, tp = _confusion(y_val, p_val, float(t))
        mcc = _mcc(tn, fp, fn, tp)
        if mcc > best_mcc:
            best_mcc = mcc
            best_thr = float(t)

    if not np.isfinite(best_thr):
        return 0.5
    return float(np.clip(best_thr, 0.0, 1.0))


@dataclass
class Paths:
    repo_root: str

    @property
    def processed_dir(self) -> str:
        return os.path.join(self.repo_root, "outputs", "processed")

    @property
    def splits_dir(self) -> str:
        return os.path.join(self.repo_root, "outputs", "splits")

    @property
    def models_dir(self) -> str:
        return os.path.join(self.repo_root, "outputs", "models")

    @property
    def outputs_reports_dir(self) -> str:
        return os.path.join(self.repo_root, "outputs", "reports")

    @property
    def reports_dir(self) -> str:
        return os.path.join(self.repo_root, "reports")

    @property
    def figures_dir(self) -> str:
        return os.path.join(self.reports_dir, "figures")

    @property
    def out_json(self) -> str:
        return os.path.join(self.outputs_reports_dir, "drift_chunks.json")

    @property
    def out_md(self) -> str:
        return os.path.join(self.reports_dir, "drift_chunks.md")


def _load_arrays(processed_dir: str) -> Dict[str, np.ndarray]:
    needed = ["X_val.npy", "y_val.npy", "X_test.npy", "y_test.npy"]
    out: Dict[str, np.ndarray] = {}
    for name in needed:
        path = os.path.join(processed_dir, name)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Missing required array: {path}")
        out[name] = np.load(path)
    out["y_val.npy"] = out["y_val.npy"].reshape(-1)
    out["y_test.npy"] = out["y_test.npy"].reshape(-1)
    return out


def _load_model(path: str):
    import joblib

    return joblib.load(path)


def _predict_proba_attack(model, X: np.ndarray) -> np.ndarray:
    proba = model.predict_proba(X)
    return proba[:, 1].astype(np.float64)


def _make_chunks(n: int, k: int) -> List[Tuple[int, int]]:
    k = max(1, int(k))
    edges = np.linspace(0, n, k + 1).astype(int)
    out: List[Tuple[int, int]] = []
    for i in range(k):
        a = int(edges[i])
        b = int(edges[i + 1])
        if b > a:
            out.append((a, b))
    return out


def _plot(model_name: str, chunks: List[Dict[str, Any]], out_path: str) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    xs = np.arange(1, len(chunks) + 1)

    def series(key: str, variant: str) -> np.ndarray:
        return np.array([c[variant]["metrics"][key] for c in chunks], dtype=np.float64)

    fpr_05 = series("fpr", "default_0.5")
    rec_05 = series("attack_recall", "default_0.5")
    mcc_05 = series("mcc", "default_0.5")

    fpr_t = series("fpr", "tuned_mcc")
    rec_t = series("attack_recall", "tuned_mcc")
    mcc_t = series("mcc", "tuned_mcc")

    attack_pct = np.array([c["attack_pct"] for c in chunks], dtype=np.float64)

    plt.figure(figsize=(8.2, 7.4))

    ax1 = plt.subplot(3, 1, 1)
    ax1.plot(xs, fpr_05, label="FPR @0.5", linewidth=2)
    ax1.plot(xs, fpr_t, label="FPR @tuned(MCC)", linewidth=2)
    ax1.set_ylabel("FPR")
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc="best")
    ax1.set_title(f"Drift / robustness by chunk — {model_name}")

    ax2 = plt.subplot(3, 1, 2, sharex=ax1)
    ax2.plot(xs, rec_05, label="Attack recall @0.5", linewidth=2)
    ax2.plot(xs, rec_t, label="Attack recall @tuned(MCC)", linewidth=2)
    ax2.set_ylabel("Attack recall")
    ax2.grid(True, alpha=0.3)
    ax2.legend(loc="best")

    ax3 = plt.subplot(3, 1, 3, sharex=ax1)
    ax3.plot(xs, mcc_05, label="MCC @0.5", linewidth=2)
    ax3.plot(xs, mcc_t, label="MCC @tuned(MCC)", linewidth=2)
    ax3.plot(xs, attack_pct / 100.0, label="Attack% (scaled)", linewidth=1, linestyle="--")
    ax3.set_xlabel("Chunk index (ordered by original sample index)")
    ax3.set_ylabel("MCC / scaled Attack%")
    ax3.grid(True, alpha=0.3)
    ax3.legend(loc="best")

    plt.tight_layout()
    plt.savefig(out_path, dpi=160)
    plt.close()


def _render_md(result: Dict[str, Any]) -> str:
    meta = result.get("meta", {})
    lines: List[str] = []
    lines.append("# Drift / Robustness Check (Chunked Test)\n\n")
    lines.append(f"Generated: {meta.get('generated_utc', '')} (UTC)\n\n")
    lines.append(f"Data mode: `{meta.get('data_mode', '')}`\n\n")

    lines.append("## What this measures\n\n")
    lines.append(
        "We reorder the test split by ascending `test_idx` (proxy for original sample order), split into contiguous chunks, "
        "and track metric stability across chunks. Large drops suggest potential drift / non-stationarity.\n\n"
    )

    lines.append("## Environment\n\n")
    env = meta.get("environment", {})
    lines.append(f"- Python: `{env.get('python', '')}`\n")
    lines.append(f"- NumPy: `{env.get('numpy', '')}`\n")
    lines.append(f"- scikit-learn: `{env.get('sklearn', '')}`\n")
    lines.append(f"- XGBoost: `{env.get('xgboost', '')}`\n\n")

    lines.append("## Figures\n\n")
    lines.append("Figures are under `reports/figures/`.\n\n")
    for model_name, m in result.get("models", {}).items():
        fig = m.get("figure", "")
        if fig:
            lines.append(f"- {model_name}: `reports/figures/{fig}`\n")
    lines.append("\n")

    lines.append("## Summary statistics (test chunks)\n\n")
    lines.append("Each metric is summarized across chunks (min/mean/max).\n\n")

    lines.append("| Model | Variant | FPR min/mean/max | Recall min/mean/max | MCC min/mean/max |\n")
    lines.append("|---|---|---|---|---|\n")
    for model_name, m in result.get("models", {}).items():
        stats = m.get("chunk_stats", {})
        for variant in ["default_0.5", "tuned_mcc"]:
            s = stats.get(variant, {})
            if not s:
                continue
            lines.append(
                f"| {model_name} | {variant} | {s['fpr']} | {s['attack_recall']} | {s['mcc']} |\n"
            )

    lines.append("\n")
    lines.append("## Notes\n\n")
    lines.append("- This is a lightweight drift proxy; it does not require timestamps.\n")
    lines.append("- If you later add time/file metadata, repeat the same evaluation grouped by file or time window.\n")
    return "".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repo-root",
        default=os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
        help="Repository root (default: parent of tools/)",
    )
    parser.add_argument("--chunks", type=int, default=20, help="Number of contiguous chunks.")
    args = parser.parse_args(argv)

    repo_root = os.path.abspath(args.repo_root)
    paths = Paths(repo_root=repo_root)
    os.makedirs(paths.outputs_reports_dir, exist_ok=True)
    os.makedirs(paths.figures_dir, exist_ok=True)

    arrays = _load_arrays(paths.processed_dir)
    X_val = arrays["X_val.npy"]
    y_val = arrays["y_val.npy"]
    X_test = arrays["X_test.npy"]
    y_test = arrays["y_test.npy"]

    test_idx_path = os.path.join(paths.splits_dir, "test_idx.npy")
    if not os.path.exists(test_idx_path):
        raise FileNotFoundError(f"Missing: {test_idx_path}")
    test_idx = np.load(test_idx_path).reshape(-1)
    if len(test_idx) != len(y_test):
        raise ValueError(f"test_idx length mismatch: {len(test_idx)} vs y_test {len(y_test)}")

    order = np.argsort(test_idx)
    X_test_ord = X_test[order]
    y_test_ord = y_test[order]

    # Environment versions
    sklearn_version = None
    xgboost_version = None
    try:
        import sklearn

        sklearn_version = getattr(sklearn, "__version__", None)
    except Exception:
        sklearn_version = None
    try:
        import xgboost

        xgboost_version = getattr(xgboost, "__version__", None)
    except Exception:
        xgboost_version = None

    data_mode = None
    split_meta_path = os.path.join(repo_root, "outputs", "splits", "split_meta.json")
    if os.path.exists(split_meta_path):
        with open(split_meta_path, "r", encoding="utf-8") as f:
            data_mode = json.load(f).get("mode")

    meta = {
        "generated_utc": _utc_now_iso(),
        "data_mode": data_mode,
        "chunks": int(args.chunks),
        "ordering": "test reordered by ascending outputs/splits/test_idx.npy",
        "environment": {
            "python": platform.python_version(),
            "numpy": getattr(np, "__version__", None),
            "sklearn": sklearn_version,
            "xgboost": xgboost_version,
        },
    }

    model_specs = {
        "xgboost": os.path.join(paths.models_dir, "xgboost_baseline.pkl"),
        "logistic_regression": os.path.join(paths.models_dir, "logreg_baseline.pkl"),
    }

    out_models: Dict[str, Any] = {}
    chunks = _make_chunks(len(y_test_ord), int(args.chunks))

    for model_name, model_path in model_specs.items():
        if not os.path.exists(model_path):
            continue

        model = _load_model(model_path)
        p_val = _predict_proba_attack(model, X_val)
        p_test = _predict_proba_attack(model, X_test_ord)

        thr_tuned = _balanced_mcc_threshold(y_val, p_val)

        per_chunk: List[Dict[str, Any]] = []
        for i, (a, b) in enumerate(chunks, start=1):
            y_c = y_test_ord[a:b]
            p_c = p_test[a:b]
            default = _metrics(y_c, p_c, 0.5)
            tuned = _metrics(y_c, p_c, thr_tuned)
            per_chunk.append(
                {
                    "chunk": i,
                    "start": int(a),
                    "end": int(b),
                    "support": int(b - a),
                    "attack_pct": float(np.mean(y_c) * 100.0),
                    "default_0.5": default,
                    "tuned_mcc": tuned,
                }
            )

        def summarize(variant: str, key: str) -> str:
            xs = np.array([c[variant]["metrics"][key] for c in per_chunk], dtype=np.float64)
            return f"{float(xs.min()):.6f}/{float(xs.mean()):.6f}/{float(xs.max()):.6f}"

        chunk_stats = {
            "default_0.5": {
                "fpr": summarize("default_0.5", "fpr"),
                "attack_recall": summarize("default_0.5", "attack_recall"),
                "mcc": summarize("default_0.5", "mcc"),
            },
            "tuned_mcc": {
                "fpr": summarize("tuned_mcc", "fpr"),
                "attack_recall": summarize("tuned_mcc", "attack_recall"),
                "mcc": summarize("tuned_mcc", "mcc"),
            },
        }

        fig_name = f"drift_chunks_{model_name}.png"
        fig_path = os.path.join(paths.figures_dir, fig_name)
        _plot(model_name, per_chunk, fig_path)

        out_models[model_name] = {
            "model_path": os.path.relpath(model_path, repo_root).replace("\\", "/"),
            "tuned_threshold_mcc": float(thr_tuned),
            "per_chunk": per_chunk,
            "chunk_stats": chunk_stats,
            "figure": fig_name,
        }

    result = {"meta": meta, "models": out_models}

    with open(paths.out_json, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    with open(paths.out_md, "w", encoding="utf-8") as f:
        f.write(_render_md(result))

    print(f"Wrote: {paths.out_json}")
    print(f"Wrote: {paths.out_md}")
    print(f"Figures: {paths.figures_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
