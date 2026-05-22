#!/usr/bin/env python
"""Cost-based threshold selection for imbalanced IDS.

We treat label=1 as Attack (positive) and label=0 as Normal (negative).

Given a false-positive cost C_FP (Normal wrongly flagged as Attack) and a
false-negative cost C_FN (Attack missed), the expected cost at threshold t is:

  cost(t) = C_FP * FP(t) + C_FN * FN(t)

This script:
1) Tunes threshold on validation set for a sweep of FN/FP cost ratios.
2) Evaluates the chosen thresholds on test.
3) Writes a thesis-friendly Markdown report + plots.

Outputs:
- outputs/reports/cost_based_thresholds.json
- reports/cost_based_thresholds.md
- reports/figures/cost_thresholds_<model>.png

Run (recommended):
  conda run -n py310 python tools/eval_cost_based_thresholds.py
"""

from __future__ import annotations

import argparse
import json
import math
import os
import platform
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Sequence, Tuple

import numpy as np


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _safe_div(num: float, den: float) -> float:
    return 0.0 if den == 0 else float(num) / float(den)


def _mcc(tn: int, fp: int, fn: int, tp: int) -> float:
    numer = (tp * tn) - (fp * fn)
    denom = float((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    if denom <= 0:
        return 0.0
    return float(numer) / float(math.sqrt(denom))


def _confusion(y_true: np.ndarray, y_prob_attack: np.ndarray, threshold: float) -> Tuple[int, int, int, int]:
    y_true = y_true.astype(np.int8)
    y_pred = (y_prob_attack >= threshold).astype(np.int8)
    tp = int(np.sum((y_true == 1) & (y_pred == 1)))
    tn = int(np.sum((y_true == 0) & (y_pred == 0)))
    fp = int(np.sum((y_true == 0) & (y_pred == 1)))
    fn = int(np.sum((y_true == 1) & (y_pred == 0)))
    return tn, fp, fn, tp


def _metrics_from_conf(tn: int, fp: int, fn: int, tp: int) -> Dict[str, float]:
    total = tn + fp + fn + tp
    tpr = _safe_div(tp, tp + fn)  # attack recall
    tnr = _safe_div(tn, tn + fp)  # specificity
    fpr = _safe_div(fp, fp + tn)
    fnr = _safe_div(fn, fn + tp)
    precision = _safe_div(tp, tp + fp)
    acc = _safe_div(tp + tn, total)
    bacc = 0.5 * (tpr + tnr)
    return {
        "accuracy": float(acc),
        "balanced_accuracy": float(bacc),
        "attack_recall": float(tpr),
        "normal_recall_specificity": float(tnr),
        "precision": float(precision),
        "fpr": float(fpr),
        "fnr": float(fnr),
        "mcc": float(_mcc(tn, fp, fn, tp)),
    }


def _tune_threshold_min_cost(
    y_true: np.ndarray,
    y_prob_attack: np.ndarray,
    *,
    cost_fp: float,
    cost_fn: float,
) -> Dict[str, Any]:
    """Find threshold minimizing cost on provided split.

    Efficient sweep over unique score values in O(n log n).
    """
    y_true = y_true.astype(np.int8)
    y_prob_attack = y_prob_attack.astype(np.float64)

    order = np.argsort(-y_prob_attack)
    y_sorted = y_true[order]
    s_sorted = y_prob_attack[order]

    pos = (y_sorted == 1)
    tp_cum = np.cumsum(pos)
    fp_cum = np.cumsum(~pos)
    P = int(tp_cum[-1])
    N = int(fp_cum[-1])
    if P == 0 or N == 0:
        return {
            "note": "Tuning skipped: only one class present.",
            "threshold": 0.5,
            "val_cost": float("nan"),
        }

    change_idx = np.r_[np.where(np.diff(s_sorted) != 0)[0], len(s_sorted) - 1]

    tp = tp_cum[change_idx].astype(np.int64)
    fp = fp_cum[change_idx].astype(np.int64)
    fn = (P - tp).astype(np.int64)
    tn = (N - fp).astype(np.int64)

    cost = cost_fp * fp.astype(np.float64) + cost_fn * fn.astype(np.float64)
    best = int(np.argmin(cost))
    thr = float(s_sorted[int(change_idx[best])])
    if not np.isfinite(thr):
        thr = 0.5
    thr = float(np.clip(thr, 0.0, 1.0))

    # cost per sample (normalized) is easier to compare across datasets
    val_cost = float(cost[best])
    val_cost_per_sample = float(val_cost / float(P + N))
    return {
        "threshold": thr,
        "val_cost": val_cost,
        "val_cost_per_sample": val_cost_per_sample,
    }


def _parse_ratios(s: str) -> List[float]:
    out: List[float] = []
    for part in (s or "").split(","):
        p = part.strip()
        if not p:
            continue
        out.append(float(p))
    if not out:
        raise ValueError("No ratios parsed")
    return out


@dataclass
class Paths:
    repo_root: str

    @property
    def processed_dir(self) -> str:
        return os.path.join(self.repo_root, "outputs", "processed")

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
        return os.path.join(self.outputs_reports_dir, "cost_based_thresholds.json")

    @property
    def out_md(self) -> str:
        return os.path.join(self.reports_dir, "cost_based_thresholds.md")


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _read_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_arrays(processed_dir: str) -> Dict[str, np.ndarray]:
    needed = ["X_val.npy", "y_val.npy", "X_test.npy", "y_test.npy"]
    out: Dict[str, np.ndarray] = {}
    for name in needed:
        path = os.path.join(processed_dir, name)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Missing required array: {path}")
        # mmap helps keep memory stable; slices still work.
        mmap = "r" if name.startswith("X_") else None
        out[name] = np.load(path, mmap_mode=mmap)
    out["y_val.npy"] = out["y_val.npy"].reshape(-1)
    out["y_test.npy"] = out["y_test.npy"].reshape(-1)
    return out


def _load_model(path: str):
    import joblib

    return joblib.load(path)


def _predict_proba_attack(model, X: np.ndarray) -> np.ndarray:
    proba = model.predict_proba(X)
    if proba.ndim != 2 or proba.shape[1] < 2:
        raise ValueError(f"Unexpected predict_proba shape: {getattr(proba, 'shape', None)}")
    return proba[:, 1].astype(np.float64)


def _predict_proba_attack_batched(model, X: np.ndarray, *, batch: int, label: str) -> np.ndarray:
    n = int(X.shape[0])
    if n == 0:
        return np.zeros((0,), dtype=np.float64)
    if batch <= 0 or batch >= n:
        print(f"Predicting probabilities for {label} in one batch (n={n})…")
        return _predict_proba_attack(model, X)

    out = np.empty((n,), dtype=np.float64)
    print(f"Predicting probabilities for {label} in batches (n={n}, batch={batch})…")
    for i in range(0, n, batch):
        j = min(i + batch, n)
        out[i:j] = _predict_proba_attack(model, X[i:j])
        if (i == 0) or (j == n) or ((i // batch) % 5 == 0):
            print(f"  {label}: {j}/{n}")
    return out


def _plot(model_name: str, ratios: List[float], rows: List[Dict[str, Any]], out_path: str) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    x = np.array(ratios, dtype=np.float64)
    xlog = np.log10(x)
    thr = np.array([r["threshold"] for r in rows], dtype=np.float64)
    fpr = np.array([r["test_metrics"]["fpr"] for r in rows], dtype=np.float64)
    rec = np.array([r["test_metrics"]["attack_recall"] for r in rows], dtype=np.float64)
    cost = np.array([r["test_cost_per_sample"] for r in rows], dtype=np.float64)

    fig, axes = plt.subplots(3, 1, figsize=(9.5, 10), constrained_layout=True)
    fig.suptitle(f"Cost-based threshold selection ({model_name})")

    axes[0].plot(xlog, thr, marker="o")
    axes[0].set_ylabel("Threshold")
    axes[0].set_xlabel("log10(FN/FP cost ratio)")
    axes[0].grid(True, alpha=0.3)

    axes[1].plot(xlog, fpr, marker="o", label="FPR")
    axes[1].plot(xlog, rec, marker="o", label="Attack Recall")
    axes[1].set_ylabel("Rate")
    axes[1].set_xlabel("log10(FN/FP cost ratio)")
    axes[1].legend(loc="best")
    axes[1].grid(True, alpha=0.3)

    axes[2].plot(xlog, cost, marker="o")
    axes[2].set_ylabel("Cost per sample")
    axes[2].set_xlabel("log10(FN/FP cost ratio)")
    axes[2].grid(True, alpha=0.3)

    _ensure_dir(os.path.dirname(out_path))
    fig.savefig(out_path, dpi=160)
    plt.close(fig)


def _write_markdown(out_md: str, payload: dict) -> None:
    lines: List[str] = []
    lines.append("# Cost-based Threshold Selection\n")
    lines.append(f"Generated: {payload['meta']['generated_utc']} (UTC)\n\n")

    lines.append("## What this does\n")
    lines.append(
        "We choose decision thresholds by minimizing an explicit cost function on the validation set: "
        "`cost = C_FP * FP + C_FN * FN`, where FN/FP ratio is swept.\n\n"
    )
    lines.append("- Label 1 = Attack (positive), label 0 = Normal (negative)\n")
    lines.append("- FP = Normal flagged as Attack (false alarm)\n")
    lines.append("- FN = Attack missed (false negative)\n\n")

    ratios = payload["meta"]["fn_fp_ratios"]
    lines.append("## Ratios swept\n")
    lines.append("- FN/FP ratios: " + ", ".join([str(r) for r in ratios]) + "\n\n")

    for model_name, model_res in payload["models"].items():
        lines.append(f"## {model_name}\n")
        fig = model_res.get("figure")
        if fig:
            lines.append(f"- Figure: `{fig}`\n\n")

        lines.append("Thresholds are tuned on validation; metrics/cost are reported on test.\n\n")
        lines.append("| FN/FP | thr(val) | test FPR | test Recall | test MCC | test cost/sample |\n")
        lines.append("|---:|---:|---:|---:|---:|---:|\n")
        for row in model_res["rows"]:
            r = float(row["fn_fp_ratio"])
            thr = float(row["threshold"])
            m = row["test_metrics"]
            lines.append(
                f"| {r:g} | {thr:.6f} | {m['fpr']:.6f} | {m['attack_recall']:.6f} | {m['mcc']:.6f} | {row['test_cost_per_sample']:.6f} |\n"
            )
        lines.append("\n")

    _ensure_dir(os.path.dirname(out_md))
    with open(out_md, "w", encoding="utf-8") as f:
        f.writelines(lines)


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--ratios",
        default="0.25,0.5,1,2,5,10,20,50,100",
        help="Comma-separated FN/FP cost ratios to sweep (C_FP=1, C_FN=ratio).",
    )
    ap.add_argument(
        "--batch",
        type=int,
        default=200000,
        help="Batch size for predict_proba to keep runtime responsive on large arrays.",
    )
    args = ap.parse_args(argv)

    paths = Paths(repo_root=os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    arrays = _load_arrays(paths.processed_dir)
    y_val = arrays["y_val.npy"]
    y_test = arrays["y_test.npy"]

    # Models
    model_paths = {
        "logistic_regression": os.path.join(paths.models_dir, "logreg_baseline.pkl"),
        "xgboost": os.path.join(paths.models_dir, "xgboost_baseline.pkl"),
    }
    for p in model_paths.values():
        if not os.path.exists(p):
            raise FileNotFoundError(f"Missing model: {p}")

    # Predictions
    X_val = arrays["X_val.npy"]
    X_test = arrays["X_test.npy"]

    ratios = _parse_ratios(args.ratios)

    manifest_path = os.path.join(paths.repo_root, "outputs", "splits", "data_manifest.json")
    data_mode = ""
    if os.path.exists(manifest_path):
        try:
            data_mode = str(_read_json(manifest_path).get("mode", ""))
        except Exception:
            data_mode = ""

    payload: Dict[str, Any] = {
        "meta": {
            "generated_utc": _utc_now_iso(),
            "data_mode": data_mode,
            "label_definition": {"0": "Normal", "1": "Attack"},
            "cost_definition": {"cost_fp": 1.0, "cost_fn": "ratio"},
            "fn_fp_ratios": ratios,
            "environment": {
                "python": platform.python_version(),
                "numpy": np.__version__,
            },
        },
        "models": {},
    }

    _ensure_dir(paths.figures_dir)

    for model_name, model_path in model_paths.items():
        model = _load_model(model_path)
        p_val = _predict_proba_attack_batched(model, X_val, batch=int(args.batch), label=f"{model_name} val")
        p_test = _predict_proba_attack_batched(model, X_test, batch=int(args.batch), label=f"{model_name} test")

        rows: List[Dict[str, Any]] = []
        for ratio in ratios:
            tuned = _tune_threshold_min_cost(y_val, p_val, cost_fp=1.0, cost_fn=float(ratio))
            thr = float(tuned["threshold"])

            tn, fp, fn, tp = _confusion(y_test, p_test, thr)
            m = _metrics_from_conf(tn, fp, fn, tp)
            test_cost = float(1.0 * fp + float(ratio) * fn)
            test_cost_per_sample = float(test_cost / float(len(y_test)))

            rows.append(
                {
                    "fn_fp_ratio": float(ratio),
                    "threshold": thr,
                    "val_cost": tuned.get("val_cost"),
                    "val_cost_per_sample": tuned.get("val_cost_per_sample"),
                    "test_confusion": {"tn": tn, "fp": fp, "fn": fn, "tp": tp},
                    "test_metrics": m,
                    "test_cost": test_cost,
                    "test_cost_per_sample": test_cost_per_sample,
                }
            )

        fig_rel = os.path.join("reports", "figures", f"cost_thresholds_{model_name}.png").replace("\\", "/")
        fig_abs = os.path.join(paths.repo_root, fig_rel)
        _plot(model_name, ratios, rows, fig_abs)

        payload["models"][model_name] = {
            "model_path": os.path.relpath(model_path, paths.repo_root).replace("\\", "/"),
            "rows": rows,
            "figure": fig_rel,
        }

    _ensure_dir(os.path.dirname(paths.out_json))
    with open(paths.out_json, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    _write_markdown(paths.out_md, payload)

    print(f"✅ Wrote: {paths.out_json}")
    print(f"✅ Wrote: {paths.out_md}")
    for model_name in payload["models"]:
        print(f"✅ Figure: {payload['models'][model_name]['figure']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
