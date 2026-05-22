#!/usr/bin/env python
"""Baseline metrics evaluator (imbalance-aware).

This script evaluates the saved Stage 2 baseline models (LogReg, XGBoost) using
the frozen Stage 1/2 artifacts under outputs/.

Key goals:
- Report metrics that stay meaningful under severe class imbalance.
- Explicitly measure Normal-side performance (specificity / FPR) since in this
  dataset Normal is the *minority* class.
- Provide an objective threshold tuning method on the validation set.

Outputs:
- JSON artifact under outputs/reports/ (machine-readable)
- Markdown summary under reports/ (thesis-friendly)

Usage (from repo root):
  python tools/baseline_metrics.py

Optional:
  python tools/baseline_metrics.py --criterion mcc
  python tools/baseline_metrics.py --tune-on val
"""

from __future__ import annotations

import argparse
import json
import math
import os
import platform
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Tuple

import numpy as np


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _safe_div(num: float, den: float) -> float:
    if den == 0:
        return 0.0
    return float(num) / float(den)


def _mcc(tn: int, fp: int, fn: int, tp: int) -> float:
    numer = (tp * tn) - (fp * fn)
    denom = math.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    return 0.0 if denom == 0 else float(numer) / float(denom)


def _confusion_from_threshold(y_true: np.ndarray, y_prob_attack: np.ndarray, threshold: float) -> Tuple[int, int, int, int]:
    y_pred = (y_prob_attack >= threshold).astype(np.int8)
    y_true = y_true.astype(np.int8)

    tp = int(np.sum((y_true == 1) & (y_pred == 1)))
    tn = int(np.sum((y_true == 0) & (y_pred == 0)))
    fp = int(np.sum((y_true == 0) & (y_pred == 1)))
    fn = int(np.sum((y_true == 1) & (y_pred == 0)))
    return tn, fp, fn, tp


def _roc_auc_binary(y_true: np.ndarray, y_score: np.ndarray) -> float:
    # Small local ROC AUC implementation avoids depending on sklearn here.
    # If only one class present, return 0.0.
    y_true = y_true.astype(np.int8)
    pos = (y_true == 1)
    neg = ~pos
    n_pos = int(np.sum(pos))
    n_neg = int(np.sum(neg))
    if n_pos == 0 or n_neg == 0:
        return 0.0

    order = np.argsort(y_score)
    y_sorted = y_true[order]
    # Rank-based AUC (equivalent to Mann–Whitney U)
    ranks = np.arange(1, len(y_sorted) + 1, dtype=np.float64)
    sum_ranks_pos = float(np.sum(ranks[y_sorted == 1]))
    auc = (sum_ranks_pos - (n_pos * (n_pos + 1) / 2.0)) / (n_pos * n_neg)
    return float(auc)


def _average_precision(y_true: np.ndarray, y_score: np.ndarray) -> float:
    # Average Precision (area under PR curve) without sklearn.
    y_true = y_true.astype(np.int8)
    n_pos = int(np.sum(y_true == 1))
    if n_pos == 0:
        return 0.0

    order = np.argsort(-y_score)
    y_sorted = y_true[order]

    tp_cum = np.cumsum(y_sorted == 1)
    fp_cum = np.cumsum(y_sorted == 0)

    precision = tp_cum / np.maximum(tp_cum + fp_cum, 1)
    recall = tp_cum / n_pos

    # Interpolated AP: sum over recall increments of precision at that point.
    # Equivalent to sklearn's average_precision_score for binary.
    recall_diff = np.diff(np.r_[0.0, recall])
    ap = float(np.sum(precision * recall_diff))
    return ap


def _metrics_at_threshold(y_true: np.ndarray, y_prob_attack: np.ndarray, *, threshold: float) -> Dict[str, Any]:
    tn, fp, fn, tp = _confusion_from_threshold(y_true, y_prob_attack, threshold)

    total = tn + fp + fn + tp
    n_attack = tp + fn
    n_normal = tn + fp

    recall_attack = _safe_div(tp, tp + fn)  # TPR
    specificity = _safe_div(tn, tn + fp)  # TNR (Normal recall)
    precision_attack = _safe_div(tp, tp + fp)
    precision_normal = _safe_div(tn, tn + fn)  # NPV in Attack-positive framing

    f1_attack = 0.0
    if (precision_attack + recall_attack) > 0:
        f1_attack = 2.0 * precision_attack * recall_attack / (precision_attack + recall_attack)

    recall_normal = specificity
    f1_normal = 0.0
    if (precision_normal + recall_normal) > 0:
        f1_normal = 2.0 * precision_normal * recall_normal / (precision_normal + recall_normal)

    acc = _safe_div(tp + tn, total)
    fpr = _safe_div(fp, fp + tn)
    fnr = _safe_div(fn, fn + tp)
    bacc = 0.5 * (recall_attack + specificity)
    mcc = _mcc(tn, fp, fn, tp)

    # Score-based metrics for both label choices
    roc_auc_attack = _roc_auc_binary(y_true, y_prob_attack)
    pr_auc_attack = _average_precision(y_true, y_prob_attack)

    y_true_normal = (y_true == 0).astype(np.int8)
    y_prob_normal = 1.0 - y_prob_attack
    roc_auc_normal = _roc_auc_binary(y_true_normal, y_prob_normal)
    pr_auc_normal = _average_precision(y_true_normal, y_prob_normal)

    return {
        "threshold": float(threshold),
        "confusion": {"tn": tn, "fp": fp, "fn": fn, "tp": tp},
        "counts": {
            "n_total": int(total),
            "n_attack": int(n_attack),
            "n_normal": int(n_normal),
            "attack_pct": 100.0 * _safe_div(n_attack, total),
            "normal_pct": 100.0 * _safe_div(n_normal, total),
        },
        "metrics": {
            "accuracy": acc,
            "balanced_accuracy": bacc,
            "mcc": mcc,
            "attack_precision": precision_attack,
            "attack_recall": recall_attack,
            "attack_f1": f1_attack,
            "normal_precision": precision_normal,
            "normal_recall_specificity": specificity,
            "normal_f1": f1_normal,
            "fpr": fpr,
            "fnr": fnr,
            "roc_auc_attack": roc_auc_attack,
            "pr_auc_attack": pr_auc_attack,
            "roc_auc_normal": roc_auc_normal,
            "pr_auc_normal": pr_auc_normal,
        },
    }


def _tune_thresholds(y_true: np.ndarray, y_prob_attack: np.ndarray) -> Dict[str, Any]:
    """Find best thresholds over unique probability values.

    Uses an exact sweep in O(n log n) by sorting predictions.
    """
    y_true = y_true.astype(np.int8)
    y_prob_attack = y_prob_attack.astype(np.float64)

    order = np.argsort(-y_prob_attack)
    y_sorted = y_true[order]
    s_sorted = y_prob_attack[order]

    pos_mask = (y_sorted == 1)
    tp_cum = np.cumsum(pos_mask)
    fp_cum = np.cumsum(~pos_mask)

    P = int(tp_cum[-1])
    N = int(fp_cum[-1])
    if P == 0 or N == 0:
        return {
            "note": "Tuning skipped: only one class present.",
            "best_mcc": {"threshold": 0.5, "mcc": 0.0, "balanced_accuracy": 0.0},
            "best_bacc": {"threshold": 0.5, "mcc": 0.0, "balanced_accuracy": 0.0},
        }

    # Evaluate at indices where threshold changes (unique score values)
    change_idx = np.r_[np.where(np.diff(s_sorted) != 0)[0], len(s_sorted) - 1]

    tp = tp_cum[change_idx].astype(np.int64)
    fp = fp_cum[change_idx].astype(np.int64)
    fn = (P - tp).astype(np.int64)
    tn = (N - fp).astype(np.int64)

    # Use float math for the denominator to avoid int overflow on large counts.
    numer = (tp * tn - fp * fn).astype(np.float64)
    a = (tp + fp).astype(np.float64)
    b = (tp + fn).astype(np.float64)
    c = (tn + fp).astype(np.float64)
    d = (tn + fn).astype(np.float64)
    denom = np.sqrt(a * b * c * d)
    mcc = np.zeros_like(denom, dtype=np.float64)
    np.divide(numer, denom, out=mcc, where=(denom != 0))
    mcc = np.nan_to_num(mcc, nan=0.0, posinf=0.0, neginf=0.0)

    tpr = tp.astype(np.float64) / P
    tnr = tn.astype(np.float64) / N
    bacc = 0.5 * (tpr + tnr)

    best_mcc_idx = int(np.argmax(mcc))
    best_bacc_idx = int(np.argmax(bacc))

    thr_mcc = float(s_sorted[int(change_idx[best_mcc_idx])])
    thr_bacc = float(s_sorted[int(change_idx[best_bacc_idx])])

    return {
        "best_mcc": {
            "threshold": thr_mcc,
            "mcc": float(mcc[best_mcc_idx]),
            "balanced_accuracy": float(bacc[best_mcc_idx]),
        },
        "best_bacc": {
            "threshold": thr_bacc,
            "mcc": float(mcc[best_bacc_idx]),
            "balanced_accuracy": float(bacc[best_bacc_idx]),
        },
    }


@dataclass
class Paths:
    repo_root: str

    @property
    def outputs(self) -> str:
        return os.path.join(self.repo_root, "outputs")

    @property
    def reports_out_dir(self) -> str:
        return os.path.join(self.outputs, "reports")

    @property
    def processed_dir(self) -> str:
        return os.path.join(self.outputs, "processed")

    @property
    def models_dir(self) -> str:
        return os.path.join(self.outputs, "models")

    @property
    def split_meta(self) -> str:
        return os.path.join(self.outputs, "splits", "split_meta.json")

    @property
    def out_json(self) -> str:
        return os.path.join(self.reports_out_dir, "baseline_metrics_extended.json")

    @property
    def out_md(self) -> str:
        return os.path.join(self.repo_root, "reports", "baseline_extended_metrics.md")


def _load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_arrays(processed_dir: str) -> Dict[str, np.ndarray]:
    needed = [
        "X_train.npy",
        "X_val.npy",
        "X_test.npy",
        "y_train.npy",
        "y_val.npy",
        "y_test.npy",
    ]
    out: Dict[str, np.ndarray] = {}
    for name in needed:
        path = os.path.join(processed_dir, name)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Missing required array: {path}")
        out[name] = np.load(path)
    return out


def _load_model(model_path: str):
    try:
        import joblib
    except Exception as e:  # pragma: no cover
        raise RuntimeError("joblib is required to load saved models") from e
    return joblib.load(model_path)


def _predict_proba_attack(model, X: np.ndarray) -> np.ndarray:
    if not hasattr(model, "predict_proba"):
        raise TypeError(f"Model {type(model).__name__} does not support predict_proba")
    proba = model.predict_proba(X)
    if proba.ndim != 2 or proba.shape[1] < 2:
        raise ValueError(f"Unexpected predict_proba shape: {getattr(proba, 'shape', None)}")
    return proba[:, 1].astype(np.float64)


def _render_md(summary: Dict[str, Any]) -> str:
    meta = summary.get("meta", {})
    models = summary.get("models", {})
    env = meta.get("environment", {})

    lines = []
    lines.append("# Baseline Metrics (Imbalance-Aware)\n")
    lines.append(f"Generated: {meta.get('generated_utc', '')} (UTC)\n")
    if meta.get("data_mode"):
        lines.append(f"Data mode: `{meta['data_mode']}`\n")

    lines.append("## Environment\n")
    lines.append(f"- Python: `{env.get('python', '')}`\n")
    lines.append(f"- NumPy: `{env.get('numpy', '')}`\n")
    lines.append(f"- scikit-learn: `{env.get('sklearn', '')}`\n")
    lines.append(f"- XGBoost: `{env.get('xgboost', '')}`\n")

    lines.append("## Why this file exists\n")
    lines.append(
        "The TON_IoT processed network dataset is severely imbalanced: Attack is the majority class and Normal is the minority class. "
        "Therefore, accuracy (and Attack-positive PR-AUC) can look overly optimistic. "
        "This report adds Normal-side metrics (specificity/FPR) and threshold tuning on the validation set.\n"
    )

    lines.append("## Key metrics (test set)\n")
    lines.append("Labels: `0 = Normal`, `1 = Attack`\n")
    lines.append("\n")

    header = "| Model | Threshold | Balanced Acc | MCC | Attack Recall | Normal Recall (Specificity) | FPR | PR-AUC (Attack) | PR-AUC (Normal) |"
    sep = "|---|---:|---:|---:|---:|---:|---:|---:|---:|"
    lines.append(header)
    lines.append(sep)

    def row(model_name: str, which: str, label: str) -> str:
        entry = models.get(model_name, {})
        block = entry.get(which, {})
        m = block.get("metrics", {})
        thr = block.get("threshold", 0.5)
        return (
            f"| {model_name} ({label}) | {thr:.6f} | {m.get('balanced_accuracy', 0.0):.6f} | {m.get('mcc', 0.0):.6f} | "
            f"{m.get('attack_recall', 0.0):.6f} | {m.get('normal_recall_specificity', 0.0):.6f} | {m.get('fpr', 0.0):.6f} | "
            f"{m.get('pr_auc_attack', 0.0):.6f} | {m.get('pr_auc_normal', 0.0):.6f} |"
        )

    for model_name in ["xgboost", "logistic_regression"]:
        if model_name in models:
            lines.append(row(model_name, "default_0.5", "default@0.5"))
            if "tuned_mcc" in models.get(model_name, {}):
                lines.append(row(model_name, "tuned_mcc", "tuned@MCC"))
            if "tuned_bacc" in models.get(model_name, {}):
                lines.append(row(model_name, "tuned_bacc", "tuned@BAcc"))

    lines.append("\n")
    lines.append("## Notes\n")
    lines.append("- `tuned@MCC` and `tuned@BAcc` select thresholds on the validation set that maximize MCC or Balanced Accuracy, respectively.\n")
    lines.append("- Use `Normal Recall (Specificity)` + `FPR` to reason about false alarms, because Normal is the minority class here.\n")
    lines.append(
        "- If you see warnings about unpickling model objects from a different library version, regenerate `outputs/models/*.pkl` by re-running "
        "`notebooks/04_train_and_evaluate_baseline.ipynb` under the pinned environment (recommended for strict reproducibility).\n"
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repo-root",
        default=os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
        help="Repository root (default: parent of tools/)",
    )
    parser.add_argument(
        "--criterion",
        default="mcc",
        choices=["mcc", "bacc"],
        help="Which tuning criterion to use (reported in JSON, tuning always computes both).",
    )
    parser.add_argument(
        "--tune-on",
        default="val",
        choices=["val", "test"],
        help="Which split to tune threshold on (default: val).",
    )

    args = parser.parse_args(argv)

    paths = Paths(repo_root=os.path.abspath(args.repo_root))
    os.makedirs(paths.reports_out_dir, exist_ok=True)

    arrays = _load_arrays(paths.processed_dir)
    X_val = arrays["X_val.npy"]
    y_val = arrays["y_val.npy"].reshape(-1)
    X_test = arrays["X_test.npy"]
    y_test = arrays["y_test.npy"].reshape(-1)

    tune_X = X_val if args.tune_on == "val" else X_test
    tune_y = y_val if args.tune_on == "val" else y_test

    split_meta = _load_json(paths.split_meta) if os.path.exists(paths.split_meta) else {}

    # Best-effort environment versions (useful for thesis reproducibility notes)
    sklearn_version = None
    xgboost_version = None
    try:  # pragma: no cover
        import sklearn

        sklearn_version = getattr(sklearn, "__version__", None)
    except Exception:
        sklearn_version = None
    try:  # pragma: no cover
        import xgboost

        xgboost_version = getattr(xgboost, "__version__", None)
    except Exception:
        xgboost_version = None

    meta = {
        "generated_utc": _utc_now_iso(),
        "data_mode": split_meta.get("mode"),
        "random_state": split_meta.get("random_state"),
        "tune_on": str(args.tune_on),
        "tuning_criterion": str(args.criterion),
        "label_definition": {"0": "Normal", "1": "Attack"},
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

    models_out: Dict[str, Any] = {}
    for name, model_path in model_specs.items():
        if not os.path.exists(model_path):
            continue

        model = _load_model(model_path)
        y_prob_tune = _predict_proba_attack(model, tune_X)
        tuning = _tune_thresholds(tune_y, y_prob_tune)

        thr_mcc = float(tuning.get("best_mcc", {}).get("threshold", 0.5))
        thr_bacc = float(tuning.get("best_bacc", {}).get("threshold", 0.5))

        tuned_selected = tuning["best_mcc"] if args.criterion == "mcc" else tuning["best_bacc"]
        thr_selected = float(tuned_selected.get("threshold", 0.5))

        y_prob_test = _predict_proba_attack(model, X_test)
        models_out[name] = {
            "model_path": os.path.relpath(model_path, paths.repo_root).replace("\\", "/"),
            "tuning": tuning,
            "default_0.5": _metrics_at_threshold(y_test, y_prob_test, threshold=0.5),
            "tuned_mcc": _metrics_at_threshold(y_test, y_prob_test, threshold=thr_mcc),
            "tuned_bacc": _metrics_at_threshold(y_test, y_prob_test, threshold=thr_bacc),
            "tuned_val": _metrics_at_threshold(y_test, y_prob_test, threshold=thr_selected),
        }

    out = {"meta": meta, "models": models_out}

    with open(paths.out_json, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)

    md = _render_md(out)
    with open(paths.out_md, "w", encoding="utf-8") as f:
        f.write(md)

    print(f"Wrote: {paths.out_json}")
    print(f"Wrote: {paths.out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
