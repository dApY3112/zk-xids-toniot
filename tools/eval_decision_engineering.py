#!/usr/bin/env python
"""Decision-engineering evaluation for imbalanced IDS classification.

Adds thesis-grade evaluation beyond single-threshold metrics:

1) Operating-point evaluation
   - ROC curve (FPR vs TPR)
   - PR curve (Precision vs Recall), Attack is positive (label=1)
   - FPR vs Attack Recall curve (SOC-friendly)
   - Select and report 3 operating points (chosen on validation):
       * low-FPR
       * balanced (max MCC)
       * high-recall
     Each point is reported on test with confusion matrix + key metrics.

2) Calibration
   - Reliability diagram + Expected Calibration Error (ECE)
   - Brier score
   - Compare before/after calibration (sigmoid/Platt and isotonic) fitted on validation.

Outputs:
  - reports/decision_engineering_baselines.md
  - reports/figures/decision_engineering_*.png
  - outputs/reports/decision_engineering_baselines.json

Run (recommended, from repo root):
  conda run -n py310 python tools/eval_decision_engineering.py
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


def _confusion(y_true: np.ndarray, y_prob_attack: np.ndarray, threshold: float) -> Dict[str, int]:
    y_true = y_true.astype(np.int8)
    y_pred = (y_prob_attack >= threshold).astype(np.int8)
    tp = int(np.sum((y_true == 1) & (y_pred == 1)))
    tn = int(np.sum((y_true == 0) & (y_pred == 0)))
    fp = int(np.sum((y_true == 0) & (y_pred == 1)))
    fn = int(np.sum((y_true == 1) & (y_pred == 0)))
    return {"tn": tn, "fp": fp, "fn": fn, "tp": tp}


def _mcc(tn: int, fp: int, fn: int, tp: int) -> float:
    numer = (tp * tn) - (fp * fn)
    denom = float((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    if denom <= 0:
        return 0.0
    return float(numer) / float(np.sqrt(denom))


def _metrics_from_conf(conf: Dict[str, int]) -> Dict[str, float]:
    tn, fp, fn, tp = conf["tn"], conf["fp"], conf["fn"], conf["tp"]
    total = tn + fp + fn + tp

    tpr = _safe_div(tp, tp + fn)  # attack recall
    tnr = _safe_div(tn, tn + fp)  # specificity (normal recall)
    fpr = _safe_div(fp, fp + tn)
    fnr = _safe_div(fn, fn + tp)
    precision = _safe_div(tp, tp + fp)

    bacc = 0.5 * (tpr + tnr)
    acc = _safe_div(tp + tn, total)
    mcc = _mcc(tn, fp, fn, tp)

    return {
        "accuracy": acc,
        "balanced_accuracy": bacc,
        "attack_recall": tpr,
        "normal_recall_specificity": tnr,
        "precision": precision,
        "fpr": fpr,
        "fnr": fnr,
        "mcc": mcc,
    }


def _ece(y_true: np.ndarray, y_prob: np.ndarray, *, n_bins: int = 15) -> Dict[str, Any]:
    """Expected Calibration Error with uniform bins on [0, 1]."""
    y_true = y_true.astype(np.int8)
    y_prob = np.clip(y_prob.astype(np.float64), 0.0, 1.0)

    bins = np.linspace(0.0, 1.0, n_bins + 1)
    idx = np.digitize(y_prob, bins) - 1
    idx = np.clip(idx, 0, n_bins - 1)

    ece = 0.0
    bin_stats: List[Dict[str, Any]] = []
    n = len(y_true)
    for b in range(n_bins):
        mask = (idx == b)
        count = int(np.sum(mask))
        if count == 0:
            bin_stats.append({"bin": b, "count": 0})
            continue
        conf = float(np.mean(y_prob[mask]))
        acc = float(np.mean(y_true[mask]))
        weight = count / n
        ece += weight * abs(acc - conf)
        bin_stats.append({"bin": b, "count": count, "mean_conf": conf, "empirical_acc": acc})
    return {"ece": float(ece), "n_bins": int(n_bins), "bins": bin_stats}


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
    def reports_dir(self) -> str:
        return os.path.join(self.repo_root, "reports")

    @property
    def figures_dir(self) -> str:
        return os.path.join(self.reports_dir, "figures")

    @property
    def outputs_reports_dir(self) -> str:
        return os.path.join(self.repo_root, "outputs", "reports")

    @property
    def out_md(self) -> str:
        return os.path.join(self.reports_dir, "decision_engineering_baselines.md")

    @property
    def out_json(self) -> str:
        return os.path.join(self.outputs_reports_dir, "decision_engineering_baselines.json")


def _load_arrays(processed_dir: str) -> Dict[str, np.ndarray]:
    needed = [
        "X_val.npy",
        "y_val.npy",
        "X_test.npy",
        "y_test.npy",
    ]
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
    if proba.ndim != 2 or proba.shape[1] < 2:
        raise ValueError(f"Unexpected predict_proba shape: {getattr(proba, 'shape', None)}")
    return proba[:, 1].astype(np.float64)


def _choose_operating_points(
    y_val: np.ndarray,
    p_val: np.ndarray,
    *,
    low_fpr_target: float,
    high_recall_target: float,
) -> Dict[str, float]:
    """Choose thresholds on validation set.

    We choose thresholds that best match practical constraints:
    - low_fpr: threshold with FPR <= target, maximizing attack recall among those;
              if none satisfy, choose threshold with minimal FPR.
    - balanced: threshold maximizing MCC
    - high_recall: threshold with recall >= target, minimizing FPR; if none satisfy,
                   choose threshold maximizing recall.
    """
    from sklearn.metrics import roc_curve

    fpr, tpr, thr = roc_curve(y_val.astype(np.int8), p_val.astype(np.float64), pos_label=1)
    # sklearn returns thr length = len(fpr) = len(tpr)

    # balanced: maximize MCC by sweeping thresholds present in roc
    best_mcc = -1.0
    best_thr_mcc = 0.5
    for t in thr:
        conf = _confusion(y_val, p_val, float(t))
        mcc = _metrics_from_conf(conf)["mcc"]
        if mcc > best_mcc:
            best_mcc = mcc
            best_thr_mcc = float(t)

    # low FPR
    mask_low = fpr <= low_fpr_target
    if np.any(mask_low):
        # maximize recall within constraint
        idx = int(np.argmax(np.where(mask_low, tpr, -1.0)))
        thr_low = float(thr[idx])
    else:
        idx = int(np.argmin(fpr))
        thr_low = float(thr[idx])

    # high recall
    mask_hi = tpr >= high_recall_target
    if np.any(mask_hi):
        # minimize FPR while meeting recall
        idx = int(np.argmin(np.where(mask_hi, fpr, np.inf)))
        thr_hi = float(thr[idx])
    else:
        idx = int(np.argmax(tpr))
        thr_hi = float(thr[idx])

    # Ensure thresholds are within [0,1] when possible (some models return +/- inf)
    def clamp(t: float) -> float:
        if not np.isfinite(t):
            return 0.5
        return float(np.clip(t, 0.0, 1.0))

    return {
        "low_fpr": clamp(thr_low),
        "balanced_mcc": clamp(best_thr_mcc),
        "high_recall": clamp(thr_hi),
    }


def _fit_calibrators(y_val: np.ndarray, p_val: np.ndarray):
    """Fit sigmoid (Platt) and isotonic calibrators on validation."""
    from sklearn.isotonic import IsotonicRegression
    from sklearn.linear_model import LogisticRegression

    y_val = y_val.astype(np.int8)
    p_val = np.clip(p_val.astype(np.float64), 1e-6, 1.0 - 1e-6)

    # Sigmoid/Platt scaling: logistic regression on logit(p)
    logit = np.log(p_val / (1.0 - p_val)).reshape(-1, 1)
    platt = LogisticRegression(solver="lbfgs", max_iter=2000)
    platt.fit(logit, y_val)

    # Isotonic regression on raw probability
    iso = IsotonicRegression(out_of_bounds="clip")
    iso.fit(p_val, y_val)

    def platt_apply(p: np.ndarray) -> np.ndarray:
        p = np.clip(p.astype(np.float64), 1e-6, 1.0 - 1e-6)
        logit_p = np.log(p / (1.0 - p)).reshape(-1, 1)
        return platt.predict_proba(logit_p)[:, 1].astype(np.float64)

    def iso_apply(p: np.ndarray) -> np.ndarray:
        p = np.clip(p.astype(np.float64), 0.0, 1.0)
        return iso.predict(p).astype(np.float64)

    return {"platt": platt_apply, "isotonic": iso_apply}


def _plot_curves(y_true: np.ndarray, p: np.ndarray, *, out_prefix: str) -> Dict[str, Any]:
    from sklearn.metrics import auc, precision_recall_curve, roc_curve

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    y_true = y_true.astype(np.int8)
    p = p.astype(np.float64)

    fpr, tpr, _ = roc_curve(y_true, p, pos_label=1)
    roc_auc = float(auc(fpr, tpr))

    prec, rec, _ = precision_recall_curve(y_true, p, pos_label=1)
    pr_auc = float(auc(rec, prec))

    # ROC
    plt.figure(figsize=(5.2, 4.2))
    plt.plot(fpr, tpr, linewidth=2)
    plt.plot([0, 1], [0, 1], linestyle="--", linewidth=1)
    plt.xlabel("False Positive Rate (Normal -> Attack)")
    plt.ylabel("True Positive Rate / Attack Recall")
    plt.title(f"ROC (AUC={roc_auc:.4f})")
    plt.grid(True, alpha=0.3)
    roc_path = out_prefix + "_roc.png"
    plt.tight_layout()
    plt.savefig(roc_path, dpi=160)
    plt.close()

    # PR
    plt.figure(figsize=(5.2, 4.2))
    plt.plot(rec, prec, linewidth=2)
    plt.xlabel("Recall (Attack)")
    plt.ylabel("Precision (Attack)")
    plt.title(f"PR (AUC={pr_auc:.4f})")
    plt.grid(True, alpha=0.3)
    pr_path = out_prefix + "_pr.png"
    plt.tight_layout()
    plt.savefig(pr_path, dpi=160)
    plt.close()

    # FPR vs Recall (SOC-friendly)
    plt.figure(figsize=(5.2, 4.2))
    # Sort by recall increasing for a nice curve
    order = np.argsort(tpr)
    plt.plot(fpr[order], tpr[order], linewidth=2)
    plt.xlabel("False Positive Rate (Normal -> Attack)")
    plt.ylabel("Attack Recall")
    plt.title("FPR vs Attack Recall")
    plt.grid(True, alpha=0.3)
    fr_path = out_prefix + "_fpr_vs_recall.png"
    plt.tight_layout()
    plt.savefig(fr_path, dpi=160)
    plt.close()

    return {
        "roc_auc": roc_auc,
        "pr_auc": pr_auc,
        "figures": {
            "roc": os.path.basename(roc_path),
            "pr": os.path.basename(pr_path),
            "fpr_vs_recall": os.path.basename(fr_path),
        },
    }


def _plot_reliability(y_true: np.ndarray, p: np.ndarray, *, title: str, out_path: str, n_bins: int = 15) -> Dict[str, Any]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    y_true = y_true.astype(np.int8)
    p = np.clip(p.astype(np.float64), 0.0, 1.0)

    bins = np.linspace(0.0, 1.0, n_bins + 1)
    idx = np.digitize(p, bins) - 1
    idx = np.clip(idx, 0, n_bins - 1)

    xs = []
    ys = []
    counts = []
    for b in range(n_bins):
        mask = (idx == b)
        c = int(np.sum(mask))
        if c == 0:
            continue
        xs.append(float(np.mean(p[mask])))
        ys.append(float(np.mean(y_true[mask])))
        counts.append(c)

    plt.figure(figsize=(5.2, 4.2))
    plt.plot([0, 1], [0, 1], linestyle="--", linewidth=1)
    plt.scatter(xs, ys, s=18)
    plt.plot(xs, ys, linewidth=1)
    plt.xlabel("Mean predicted probability (Attack)")
    plt.ylabel("Empirical attack frequency")
    plt.title(title)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_path, dpi=160)
    plt.close()

    ece_info = _ece(y_true, p, n_bins=n_bins)
    return {"ece": ece_info["ece"], "n_bins": n_bins, "points": len(xs), "counts_nonempty_bins": len(counts)}


def _render_md(result: Dict[str, Any]) -> str:
    meta = result.get("meta", {})
    lines: List[str] = []
    lines.append("# Decision Engineering Evaluation (Baselines)\n")
    lines.append(f"Generated: {meta.get('generated_utc', '')} (UTC)\n")
    lines.append(f"Data mode: `{meta.get('data_mode', '')}`\n")
    env = meta.get("environment", {})
    lines.append("## Environment\n")
    lines.append(f"- Python: `{env.get('python', '')}`\n")
    lines.append(f"- NumPy: `{env.get('numpy', '')}`\n")
    lines.append(f"- scikit-learn: `{env.get('sklearn', '')}`\n")
    lines.append(f"- XGBoost: `{env.get('xgboost', '')}`\n")

    lines.append("## Figures\n")
    lines.append("All figures are under `reports/figures/`.\n")

    models = result.get("models", {})
    for model_name, m in models.items():
        lines.append(f"### {model_name}\n")
        figs = m.get("figures", {})
        if figs:
            lines.append(f"- ROC: `reports/figures/{figs.get('roc', '')}`\n")
            lines.append(f"- PR: `reports/figures/{figs.get('pr', '')}`\n")
            lines.append(f"- FPR vs Recall: `reports/figures/{figs.get('fpr_vs_recall', '')}`\n")
        cfigs = m.get("calibration_figures", {})
        if cfigs:
            lines.append(f"- Reliability (raw): `reports/figures/{cfigs.get('raw', '')}`\n")
            lines.append(f"- Reliability (Platt): `reports/figures/{cfigs.get('platt', '')}`\n")
            lines.append(f"- Reliability (Isotonic): `reports/figures/{cfigs.get('isotonic', '')}`\n")

        lines.append("\n")
        lines.append("#### Operating points (thresholds chosen on validation, evaluated on test)\n")
        lines.append("Labels: `0=Normal`, `1=Attack`\n")
        lines.append("\n")
        lines.append("| Point | Threshold | Attack Recall | Normal Recall (Spec) | FPR | MCC | Confusion (tn/fp/fn/tp) |\n")
        lines.append("|---|---:|---:|---:|---:|---:|---|\n")
        for key in ["low_fpr", "balanced_mcc", "high_recall"]:
            block = m.get("operating_points", {}).get(key, {})
            thr = float(block.get("threshold", 0.5))
            metrics = block.get("test", {}).get("metrics", {})
            conf = block.get("test", {}).get("confusion", {})
            lines.append(
                f"| {key} | {thr:.6f} | {metrics.get('attack_recall', 0.0):.6f} | {metrics.get('normal_recall_specificity', 0.0):.6f} | "
                f"{metrics.get('fpr', 0.0):.6f} | {metrics.get('mcc', 0.0):.6f} | "
                f"{conf.get('tn', 0)}/{conf.get('fp', 0)}/{conf.get('fn', 0)}/{conf.get('tp', 0)} |\n"
            )

        lines.append("\n")
        lines.append("#### Calibration (test set)\n")
        cal = m.get("calibration", {})
        if cal:
            lines.append("| Variant | Brier | ECE |\n")
            lines.append("|---|---:|---:|\n")
            for variant in ["raw", "platt", "isotonic"]:
                v = cal.get(variant, {})
                lines.append(f"| {variant} | {v.get('brier', 0.0):.6f} | {v.get('ece', 0.0):.6f} |\n")
        lines.append("\n")

    lines.append("## Interpretation guide\n")
    lines.append(
        "- In this dataset, Normal is the minority class. So `FPR` and `Normal Recall (Specificity)` are critical for operational IDS value.\n"
    )
    lines.append(
        "- Operating points make the imbalance problem explicit: you pick a threshold by cost constraints (false alarms vs missed attacks), not by default 0.5.\n"
    )
    lines.append(
        "- Calibration complements classification quality: even with strong ROC/PR, probability estimates can be miscalibrated. ECE/Brier quantify this.\n"
    )
    return "".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repo-root",
        default=os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
        help="Repository root (default: parent of tools/)",
    )
    parser.add_argument("--low-fpr", type=float, default=0.01, help="Low-FPR operating point target (validation).")
    parser.add_argument("--high-recall", type=float, default=0.995, help="High-recall operating point target (validation).")
    parser.add_argument("--ece-bins", type=int, default=15, help="Bins for ECE / reliability diagram.")
    args = parser.parse_args(argv)

    repo_root = os.path.abspath(args.repo_root)
    paths = Paths(repo_root=repo_root)
    os.makedirs(paths.figures_dir, exist_ok=True)
    os.makedirs(paths.outputs_reports_dir, exist_ok=True)

    arrays = _load_arrays(paths.processed_dir)
    X_val = arrays["X_val.npy"]
    y_val = arrays["y_val.npy"]
    X_test = arrays["X_test.npy"]
    y_test = arrays["y_test.npy"]

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

    # Try to read split meta if present
    split_meta_path = os.path.join(repo_root, "outputs", "splits", "split_meta.json")
    data_mode = None
    if os.path.exists(split_meta_path):
        with open(split_meta_path, "r", encoding="utf-8") as f:
            data_mode = json.load(f).get("mode")

    meta = {
        "generated_utc": _utc_now_iso(),
        "data_mode": data_mode,
        "label_definition": {"0": "Normal", "1": "Attack"},
        "operating_point_targets": {"low_fpr": float(args.low_fpr), "high_recall": float(args.high_recall)},
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
    from sklearn.metrics import brier_score_loss

    for model_name, model_path in model_specs.items():
        if not os.path.exists(model_path):
            continue

        model = _load_model(model_path)
        p_val = _predict_proba_attack(model, X_val)
        p_test = _predict_proba_attack(model, X_test)

        # Operating points
        thrs = _choose_operating_points(
            y_val,
            p_val,
            low_fpr_target=float(args.low_fpr),
            high_recall_target=float(args.high_recall),
        )

        op: Dict[str, Any] = {}
        for key, thr in thrs.items():
            conf_test = _confusion(y_test, p_test, float(thr))
            op[key] = {
                "threshold": float(thr),
                "test": {
                    "confusion": conf_test,
                    "metrics": _metrics_from_conf(conf_test),
                },
            }

        # Curves
        fig_prefix = os.path.join(paths.figures_dir, f"decision_engineering_{model_name}")
        curve_info = _plot_curves(y_test, p_test, out_prefix=fig_prefix)

        # Calibration
        calibrators = _fit_calibrators(y_val, p_val)
        p_platt = calibrators["platt"](p_test)
        p_iso = calibrators["isotonic"](p_test)

        brier_raw = float(brier_score_loss(y_test.astype(np.int8), np.clip(p_test, 0.0, 1.0)))
        brier_platt = float(brier_score_loss(y_test.astype(np.int8), np.clip(p_platt, 0.0, 1.0)))
        brier_iso = float(brier_score_loss(y_test.astype(np.int8), np.clip(p_iso, 0.0, 1.0)))

        rel_raw_path = os.path.join(paths.figures_dir, f"decision_engineering_{model_name}_reliability_raw.png")
        rel_platt_path = os.path.join(paths.figures_dir, f"decision_engineering_{model_name}_reliability_platt.png")
        rel_iso_path = os.path.join(paths.figures_dir, f"decision_engineering_{model_name}_reliability_isotonic.png")

        rel_raw = _plot_reliability(y_test, p_test, title=f"Reliability (raw) — {model_name}", out_path=rel_raw_path, n_bins=int(args.ece_bins))
        rel_platt = _plot_reliability(y_test, p_platt, title=f"Reliability (Platt) — {model_name}", out_path=rel_platt_path, n_bins=int(args.ece_bins))
        rel_iso = _plot_reliability(y_test, p_iso, title=f"Reliability (Isotonic) — {model_name}", out_path=rel_iso_path, n_bins=int(args.ece_bins))

        out_models[model_name] = {
            "model_path": os.path.relpath(model_path, repo_root).replace("\\", "/"),
            "curves": {"roc_auc": curve_info["roc_auc"], "pr_auc": curve_info["pr_auc"]},
            "figures": curve_info["figures"],
            "operating_points": op,
            "calibration": {
                "raw": {"brier": brier_raw, "ece": float(rel_raw["ece"])},
                "platt": {"brier": brier_platt, "ece": float(rel_platt["ece"])},
                "isotonic": {"brier": brier_iso, "ece": float(rel_iso["ece"])},
            },
            "calibration_figures": {
                "raw": os.path.basename(rel_raw_path),
                "platt": os.path.basename(rel_platt_path),
                "isotonic": os.path.basename(rel_iso_path),
            },
        }

    result = {"meta": meta, "models": out_models}

    with open(paths.out_json, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    md = _render_md(result)
    with open(paths.out_md, "w", encoding="utf-8") as f:
        f.write(md)

    print(f"Wrote: {paths.out_json}")
    print(f"Wrote: {paths.out_md}")
    print(f"Figures: {paths.figures_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
