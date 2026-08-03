#!/usr/bin/env python
"""Post-hoc attack-type error analysis for the binary IDS models.

The `type` column is intentionally excluded from training because it is target
metadata/leakage-prone. This script uses it only after prediction to analyze
which attack families are missed by the binary models.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import platform
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Sequence

import numpy as np
import pandas as pd

from eval_decision_engineering import _confusion, _metrics_from_conf


ROOT = Path(__file__).resolve().parents[1]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _resolve_manifest_path(repo_root: Path, raw_path: str) -> Path:
    raw = raw_path.replace("\\", os.sep).replace("/", os.sep)
    path = Path(raw)
    if path.is_absolute():
        return path
    candidates = [
        (repo_root / raw).resolve(),
        (repo_root / "notebooks" / raw).resolve(),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def _load_type_metadata(repo_root: Path, *, chunksize: int) -> pd.DataFrame:
    manifest = _read_json(repo_root / "outputs" / "splits" / "data_manifest.json")
    sample_frac = float(manifest.get("sample_frac", 0.15))
    random_state = int(manifest.get("random_state", 42))
    frames: List[pd.DataFrame] = []
    for raw_file in manifest["files_used"]:
        path = _resolve_manifest_path(repo_root, str(raw_file))
        print(f"Loading metadata sample: {path.name}")
        chunks: List[pd.DataFrame] = []
        for chunk in pd.read_csv(path, usecols=["label", "type"], chunksize=int(chunksize), low_memory=False):
            chunks.append(chunk.sample(frac=sample_frac, random_state=random_state))
        if chunks:
            part = pd.concat(chunks, ignore_index=True)
            part["source_file"] = path.name
            frames.append(part)
    out = pd.concat(frames, ignore_index=True)
    expected = int(manifest.get("n_rows", len(out)))
    if abs(len(out) - expected) > 100:
        raise RuntimeError(f"Reconstructed metadata row count {len(out)} differs from manifest n_rows={expected}")
    return out


def _load_model(path: Path):
    import joblib

    return joblib.load(path)


def _predict_attack_probability(model, X: np.ndarray) -> np.ndarray:
    proba = model.predict_proba(X)
    if proba.ndim != 2 or proba.shape[1] < 2:
        raise ValueError(f"Unexpected predict_proba output shape: {getattr(proba, 'shape', None)}")
    return np.asarray(proba[:, 1], dtype=np.float64)


def _thresholds_for_model(decision: Dict[str, Any], model_name: str) -> Dict[str, float]:
    points = decision["models"][model_name]["operating_points"]
    return {
        "default_0.5": 0.5,
        "low_fpr": float(points["low_fpr"]["threshold"]),
        "balanced_mcc": float(points["balanced_mcc"]["threshold"]),
        "high_recall": float(points["high_recall"]["threshold"]),
    }


def _safe_div(num: float, den: float) -> float:
    return 0.0 if den == 0 else float(num) / float(den)


def _attack_type_rows(
    *,
    y_true: np.ndarray,
    y_pred: np.ndarray,
    attack_type: np.ndarray,
    source_file: np.ndarray,
    min_count: int,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    attack_mask = y_true == 1
    types = sorted({str(x) for x in attack_type[attack_mask]})
    for type_name in types:
        mask = attack_mask & (attack_type == type_name)
        n = int(np.sum(mask))
        if n < min_count:
            continue
        fn = int(np.sum(mask & (y_pred == 0)))
        tp = int(np.sum(mask & (y_pred == 1)))
        files = sorted({str(x) for x in source_file[mask]})
        rows.append(
            {
                "attack_type": type_name,
                "n": n,
                "tp": tp,
                "fn": fn,
                "attack_recall": _safe_div(tp, n),
                "fn_rate": _safe_div(fn, n),
                "source_files": ",".join(files),
            }
        )
    rows.sort(key=lambda r: (-float(r["fn_rate"]), -int(r["n"]), str(r["attack_type"])))
    return rows


def _source_file_rows(*, y_true: np.ndarray, y_pred: np.ndarray, source_file: np.ndarray) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for file_name in sorted({str(x) for x in source_file}):
        mask = source_file == file_name
        conf = _confusion(y_true[mask], y_pred[mask].astype(np.float64), 0.5)
        metrics = _metrics_from_conf(conf)
        rows.append(
            {
                "source_file": file_name,
                "n": int(np.sum(mask)),
                "attack_pct": float(np.mean(y_true[mask] == 1) * 100.0),
                "confusion": conf,
                "metrics": metrics,
            }
        )
    return rows


def _write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _render_md(payload: Dict[str, Any]) -> str:
    meta = payload["meta"]
    lines: List[str] = []
    lines.append("# Attack-Type Post-hoc Error Analysis\n")
    lines.append(f"Generated: {meta['generated_utc']} (UTC)\n\n")
    lines.append("## Purpose\n")
    lines.append(
        "`type` is not used for binary model training. This report uses `type` only after prediction to identify "
        "which attack families contribute most to false negatives under each operating point.\n\n"
    )
    lines.append("## Alignment checks\n")
    lines.append(f"- Test rows: `{meta['n_test']}`\n")
    lines.append(f"- Metadata/test label mismatches: `{meta['label_mismatch_count']}`\n")
    lines.append(f"- Minimum attack-type count reported: `{meta['min_count']}`\n\n")

    for model_name, model in payload["models"].items():
        lines.append(f"## {model_name}\n\n")
        lines.append("### Operating point summary\n")
        lines.append("| Point | Threshold | Attack Recall | Normal Recall (Spec) | FPR | MCC | Confusion tn/fp/fn/tp |\n")
        lines.append("|---|---:|---:|---:|---:|---:|---|\n")
        for point in ["default_0.5", "low_fpr", "balanced_mcc", "high_recall"]:
            block = model["operating_points"][point]
            metrics = block["metrics"]
            conf = block["confusion"]
            lines.append(
                f"| {point} | {block['threshold']:.6f} | {metrics['attack_recall']:.6f} | "
                f"{metrics['normal_recall_specificity']:.6f} | {metrics['fpr']:.6f} | {metrics['mcc']:.6f} | "
                f"{conf['tn']}/{conf['fp']}/{conf['fn']}/{conf['tp']} |\n"
            )
        lines.append("\n")

        lines.append("### Highest false-negative rates by attack type\n")
        lines.append("Rows are sorted by false-negative rate, then support size. Only true attack rows are included.\n\n")
        for point in ["default_0.5", "balanced_mcc", "low_fpr", "high_recall"]:
            rows = model["attack_type_errors"][point][:10]
            lines.append(f"#### {point}\n\n")
            lines.append("| Attack type | n | FN | TP | Attack recall | FN rate |\n")
            lines.append("|---|---:|---:|---:|---:|---:|\n")
            for row in rows:
                lines.append(
                    f"| {row['attack_type']} | {row['n']} | {row['fn']} | {row['tp']} | "
                    f"{row['attack_recall']:.6f} | {row['fn_rate']:.6f} |\n"
                )
            lines.append("\n")

        normal = model["normal_false_alarms"]
        lines.append("### Normal false alarms\n")
        lines.append(
            f"- Normal rows: `{normal['n_normal']}`, false positives at default 0.5: `{normal['fp_default_0.5']}`, "
            f"FPR: `{normal['fpr_default_0.5']:.6f}`.\n\n"
        )

    lines.append("## Interpretation\n")
    lines.append(
        "- This analysis strengthens the IDS evaluation because it shows which attack families are missed, rather than only reporting aggregate binary metrics.\n"
    )
    lines.append(
        "- Since `type` is excluded from training and used only post hoc, the report does not introduce target leakage into the binary model.\n"
    )
    return "".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=str(ROOT), help="Repository root.")
    parser.add_argument("--chunksize", type=int, default=50000, help="CSV chunk size for metadata reconstruction.")
    parser.add_argument("--min-count", type=int, default=100, help="Minimum true-attack rows per type to report.")
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    reports_dir = repo_root / "reports"
    out_dir = repo_root / "outputs" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    metadata = _load_type_metadata(repo_root, chunksize=int(args.chunksize))
    test_idx = np.load(repo_root / "outputs" / "splits" / "test_idx.npy")
    y_test = np.load(repo_root / "outputs" / "processed" / "y_test.npy").reshape(-1).astype(np.int8)
    X_test = np.load(repo_root / "outputs" / "processed" / "X_test.npy", mmap_mode="r")
    test_meta = metadata.iloc[test_idx].reset_index(drop=True)
    meta_y = test_meta["label"].astype(np.int8).to_numpy()
    mismatch_count = int(np.sum(meta_y != y_test))
    if mismatch_count:
        raise RuntimeError(f"Metadata/test label alignment failed: {mismatch_count} mismatches")

    attack_type = test_meta["type"].astype(str).to_numpy()
    source_file = test_meta["source_file"].astype(str).to_numpy()
    decision = _read_json(out_dir / "decision_engineering_baselines.json")

    model_specs = {
        "xgboost": repo_root / "outputs" / "models" / "xgboost_baseline.pkl",
        "logistic_regression": repo_root / "outputs" / "models" / "logreg_baseline.pkl",
    }
    all_csv_rows: List[Dict[str, Any]] = []
    models: Dict[str, Any] = {}
    for model_name, model_path in model_specs.items():
        if not model_path.exists():
            continue
        print(f"Predicting: {model_name}")
        model = _load_model(model_path)
        p_attack = _predict_attack_probability(model, X_test)
        thresholds = _thresholds_for_model(decision, model_name)

        operating_points: Dict[str, Any] = {}
        attack_type_errors: Dict[str, List[Dict[str, Any]]] = {}
        source_file_errors: Dict[str, List[Dict[str, Any]]] = {}
        for point, threshold in thresholds.items():
            y_pred = (p_attack >= float(threshold)).astype(np.int8)
            conf = _confusion(y_test, p_attack, float(threshold))
            operating_points[point] = {
                "threshold": float(threshold),
                "confusion": conf,
                "metrics": _metrics_from_conf(conf),
            }
            rows = _attack_type_rows(
                y_true=y_test,
                y_pred=y_pred,
                attack_type=attack_type,
                source_file=source_file,
                min_count=int(args.min_count),
            )
            attack_type_errors[point] = rows
            source_file_errors[point] = _source_file_rows(y_true=y_test, y_pred=y_pred, source_file=source_file)
            for row in rows:
                csv_row = {"model": model_name, "point": point, **row}
                all_csv_rows.append(csv_row)

        normal_mask = y_test == 0
        y_pred_default = (p_attack >= 0.5).astype(np.int8)
        fp_default = int(np.sum(normal_mask & (y_pred_default == 1)))
        n_normal = int(np.sum(normal_mask))

        models[model_name] = {
            "model_path": str(model_path.relative_to(repo_root)).replace("\\", "/"),
            "thresholds": thresholds,
            "operating_points": operating_points,
            "attack_type_errors": attack_type_errors,
            "source_file_errors": source_file_errors,
            "normal_false_alarms": {
                "n_normal": n_normal,
                "fp_default_0.5": fp_default,
                "fpr_default_0.5": _safe_div(fp_default, n_normal),
            },
        }

    try:
        import sklearn

        sklearn_version = getattr(sklearn, "__version__", None)
    except Exception:
        sklearn_version = None

    payload: Dict[str, Any] = {
        "meta": {
            "generated_utc": _utc_now_iso(),
            "n_test": int(len(y_test)),
            "label_mismatch_count": mismatch_count,
            "min_count": int(args.min_count),
            "environment": {
                "python": platform.python_version(),
                "numpy": getattr(np, "__version__", None),
                "pandas": getattr(pd, "__version__", None),
                "sklearn": sklearn_version,
            },
        },
        "models": models,
    }

    json_path = out_dir / "attack_type_error_analysis.json"
    md_path = reports_dir / "attack_type_error_analysis.md"
    csv_path = out_dir / "attack_type_error_analysis.csv"
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    md_path.write_text(_render_md(payload), encoding="utf-8")
    _write_csv(csv_path, all_csv_rows)

    print(f"Wrote: {json_path}")
    print(f"Wrote: {md_path}")
    print(f"Wrote: {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
