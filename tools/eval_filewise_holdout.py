#!/usr/bin/env python
"""File-wise holdout robustness check for the TON_IoT IDS case study.

The main thesis split is a stratified random train/validation/test split over a
sampled union of 23 processed CSV files. This script adds a stricter
supplementary check: train on earlier-numbered files and evaluate on a held-out
block of later-numbered files. It is intended as robustness evidence, not as a
replacement for the main benchmark.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

import numpy as np
import pandas as pd

from eval_decision_engineering import _choose_operating_points, _confusion, _metrics_from_conf


NUMERIC_FEATURES = [
    "duration",
    "src_bytes",
    "dst_bytes",
    "src_pkts",
    "dst_pkts",
    "src_ip_bytes",
    "dst_ip_bytes",
    "missed_bytes",
    "src_port",
    "dst_port",
    "http_request_body_len",
    "http_response_body_len",
]

CATEGORICAL_FEATURES = [
    "proto",
    "service",
    "conn_state",
    "http_method",
    "http_version",
    "http_status_code",
    "ssl_version",
    "ssl_cipher",
    "weird_name",
]

BOOLEAN_FEATURES = [
    "dns_AA",
    "dns_RD",
    "dns_RA",
    "ssl_resumed",
    "ssl_established",
]

DROP_COLUMNS = [
    "src_ip",
    "dst_ip",
    "type",
    "ts",
    "http_uri",
    "http_referrer",
    "http_user_agent",
    "ssl_subject",
    "ssl_issuer",
    "weird_addl",
    "weird_notice",
    "dns_query",
]


@dataclass
class Paths:
    repo_root: Path

    @property
    def data_dir(self) -> Path:
        return self.repo_root / "data" / "processed" / "Processed_Network_dataset"

    @property
    def reports_dir(self) -> Path:
        return self.repo_root / "reports"

    @property
    def outputs_reports_dir(self) -> Path:
        return self.repo_root / "outputs" / "reports"

    @property
    def out_md(self) -> Path:
        return self.reports_dir / "filewise_holdout.md"

    @property
    def out_json(self) -> Path:
        return self.outputs_reports_dir / "filewise_holdout.json"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _natural_file_key(path: Path) -> Tuple[int, str]:
    match = re.search(r"Network_dataset_(\d+)\.csv$", path.name)
    return (int(match.group(1)) if match else 10**9, path.name)


def _find_files(data_dir: Path) -> List[Path]:
    files = sorted(data_dir.glob("Network_dataset_*.csv"), key=_natural_file_key)
    if not files:
        raise FileNotFoundError(f"No processed network files found under {data_dir}")
    return files


def _read_sampled_file(path: Path, *, sample_frac: float, random_state: int) -> pd.DataFrame:
    df = pd.read_csv(path, low_memory=False)
    if not (0.0 < sample_frac <= 1.0):
        raise ValueError("--sample-frac must be in (0, 1]")
    sampled = df.sample(frac=float(sample_frac), random_state=int(random_state)).copy()
    sampled["__source_file"] = path.name
    return sampled


def _load_sampled_files(files: Sequence[Path], *, sample_frac: float, random_state: int) -> pd.DataFrame:
    parts: List[pd.DataFrame] = []
    for path in files:
        print(f"Loading sampled file: {path.name}")
        parts.append(_read_sampled_file(path, sample_frac=sample_frac, random_state=random_state))
    return pd.concat(parts, ignore_index=True)


def _prepare_xy(df: pd.DataFrame) -> Tuple[pd.DataFrame, np.ndarray]:
    if "label" not in df.columns:
        raise ValueError("Missing required label column")
    y = df["label"].astype(np.int8).to_numpy()
    X = df.drop(columns=["label", "__source_file"], errors="ignore")
    X = X.drop(columns=[c for c in DROP_COLUMNS if c in X.columns], errors="ignore")

    for col in NUMERIC_FEATURES:
        if col in X.columns:
            X[col] = pd.to_numeric(X[col], errors="coerce")

    for col in CATEGORICAL_FEATURES:
        if col in X.columns:
            X[col] = X[col].astype(str).replace("-", "NONE")

    true_values = {"t", "true", "1", "yes"}
    for col in BOOLEAN_FEATURES:
        if col not in X.columns:
            continue
        series = X[col]
        if pd.api.types.is_numeric_dtype(series):
            X[col] = series.fillna(0).astype(np.int8)
            continue
        normalized = series.astype(str).replace("-", "NONE").str.lower()
        X[col] = normalized.apply(lambda value: 1 if value in true_values else 0).astype(np.int8)

    missing = [c for c in NUMERIC_FEATURES + CATEGORICAL_FEATURES + BOOLEAN_FEATURES if c not in X.columns]
    if missing:
        raise ValueError(f"Missing expected feature columns: {missing}")
    return X, y


def _stratified_cap(
    X: pd.DataFrame,
    y: np.ndarray,
    *,
    max_rows: int,
    random_state: int,
) -> Tuple[pd.DataFrame, np.ndarray]:
    if max_rows <= 0 or len(y) <= max_rows:
        return X, y
    from sklearn.model_selection import StratifiedShuffleSplit

    sss = StratifiedShuffleSplit(n_splits=1, train_size=int(max_rows), random_state=int(random_state))
    idx, _ = next(sss.split(np.zeros(len(y)), y))
    idx = np.asarray(idx, dtype=np.int64)
    return X.iloc[idx].reset_index(drop=True), y[idx]


def _train_val_split(
    X: pd.DataFrame,
    y: np.ndarray,
    *,
    val_frac: float,
    random_state: int,
) -> Tuple[pd.DataFrame, pd.DataFrame, np.ndarray, np.ndarray]:
    from sklearn.model_selection import train_test_split

    X_train, X_val, y_train, y_val = train_test_split(
        X,
        y,
        test_size=float(val_frac),
        stratify=y,
        random_state=int(random_state),
    )
    return X_train.reset_index(drop=True), X_val.reset_index(drop=True), y_train, y_val


def _build_pipeline(random_state: int):
    from sklearn.compose import ColumnTransformer
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder, StandardScaler

    numeric_pipe = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    categorical_pipe = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]
    )
    boolean_pipe = Pipeline(steps=[("imputer", SimpleImputer(strategy="most_frequent"))])

    preprocess = ColumnTransformer(
        transformers=[
            ("num", numeric_pipe, NUMERIC_FEATURES),
            ("cat", categorical_pipe, CATEGORICAL_FEATURES),
            ("bool", boolean_pipe, BOOLEAN_FEATURES),
        ],
        remainder="drop",
        verbose_feature_names_out=False,
    )

    return Pipeline(
        steps=[
            ("preprocess", preprocess),
            (
                "model",
                LogisticRegression(
                    max_iter=2000,
                    class_weight="balanced",
                    n_jobs=1,
                    random_state=int(random_state),
                ),
            ),
        ]
    )


def _predict_attack_probability(model, X: pd.DataFrame) -> np.ndarray:
    proba = model.predict_proba(X)
    if proba.ndim != 2 or proba.shape[1] < 2:
        raise ValueError(f"Unexpected predict_proba output shape: {getattr(proba, 'shape', None)}")
    return np.asarray(proba[:, 1], dtype=np.float64)


def _evaluate_points(y_true: np.ndarray, p_attack: np.ndarray, thresholds: Dict[str, float]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for name, threshold in thresholds.items():
        conf = _confusion(y_true, p_attack, float(threshold))
        out[name] = {
            "threshold": float(threshold),
            "confusion": conf,
            "metrics": _metrics_from_conf(conf),
        }
    return out


def _label_summary(y: np.ndarray) -> Dict[str, Any]:
    total = int(len(y))
    attack = int(np.sum(y == 1))
    normal = int(np.sum(y == 0))
    return {
        "n": total,
        "normal": normal,
        "attack": attack,
        "attack_pct": float(attack / total * 100.0) if total else 0.0,
    }


def _render_md(payload: Dict[str, Any]) -> str:
    meta = payload["meta"]
    holdout = payload["holdout"]
    thresholds = payload["thresholds"]
    points = payload["operating_points"]
    summaries = payload["data_summary"]

    lines: List[str] = []
    lines.append("# File-wise Holdout Robustness Check\n")
    lines.append(f"Generated: {meta['generated_utc']} (UTC)\n")
    lines.append("\n")
    lines.append("## Purpose\n")
    lines.append(
        "The main thesis benchmark uses a stratified random split over the sampled union of 23 TON_IoT processed CSV files. "
        "This supplementary robustness check trains a Logistic Regression model on earlier-numbered files and evaluates it "
        "on a held-out block of later-numbered files. It is a file-wise holdout experiment, not a timestamp-ordered temporal deployment simulation.\n"
    )
    lines.append("\n")
    lines.append("## File split\n")
    lines.append(f"- Training/validation files: `{', '.join(holdout['train_files'])}`\n")
    lines.append(f"- Held-out files: `{', '.join(holdout['holdout_files'])}`\n")
    lines.append(f"- Per-file sample fraction: `{meta['sample_frac']}`\n")
    lines.append(f"- Training cap before validation split: `{meta['max_train_rows']}` rows\n")
    lines.append("\n")
    lines.append("## Data summary\n")
    lines.append("| Split | n | Normal | Attack | Attack % |\n")
    lines.append("|---|---:|---:|---:|---:|\n")
    for key in ["train_model", "validation", "holdout"]:
        row = summaries[key]
        lines.append(
            f"| {key} | {row['n']} | {row['normal']} | {row['attack']} | {row['attack_pct']:.4f}% |\n"
        )
    lines.append("\n")
    lines.append("## Operating points\n")
    lines.append("Thresholds are selected on the validation part of the training-file sample and evaluated on the held-out files.\n")
    lines.append("\n")
    lines.append("| Point | Threshold | Attack Recall | Normal Recall (Spec) | FPR | MCC | Confusion (tn/fp/fn/tp) |\n")
    lines.append("|---|---:|---:|---:|---:|---:|---|\n")
    for name in ["default_0.5", "low_fpr", "balanced_mcc", "high_recall"]:
        block = points[name]
        metrics = block["metrics"]
        conf = block["confusion"]
        lines.append(
            f"| {name} | {block['threshold']:.6f} | {metrics['attack_recall']:.6f} | "
            f"{metrics['normal_recall_specificity']:.6f} | {metrics['fpr']:.6f} | {metrics['mcc']:.6f} | "
            f"{conf['tn']}/{conf['fp']}/{conf['fn']}/{conf['tp']} |\n"
        )
    lines.append("\n")
    lines.append("## Interpretation\n")
    lines.append(
        "- This experiment directly addresses the limitation that the main split is random and can mix records from every processed CSV file across train, validation, and test.\n"
    )
    lines.append(
        "- Because file numbering is only a proxy for source-file grouping, the result should be cited as file-wise robustness rather than true chronological validation.\n"
    )
    lines.append(
        "- Large degradation relative to the main random split would indicate non-stationarity across files; stable performance would strengthen the generalization claim.\n"
    )
    lines.append("\n")
    lines.append("## Environment\n")
    env = meta["environment"]
    lines.append(f"- Python: `{env.get('python')}`\n")
    lines.append(f"- NumPy: `{env.get('numpy')}`\n")
    lines.append(f"- pandas: `{env.get('pandas')}`\n")
    lines.append(f"- scikit-learn: `{env.get('sklearn')}`\n")
    lines.append("\n")
    lines.append("## Reproduce\n")
    lines.append(
        "`python tools/reproduce.py file-holdout --sample-frac "
        f"{meta['sample_frac']} --holdout-count {holdout['holdout_count']} --max-train-rows {meta['max_train_rows']}`\n"
    )
    lines.append(f"\nValidation thresholds: `{json.dumps(thresholds, sort_keys=True)}`\n")
    return "".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repo-root",
        default=os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
        help="Repository root (default: parent of tools/)",
    )
    parser.add_argument("--sample-frac", type=float, default=0.05, help="Per-file sampling fraction.")
    parser.add_argument("--holdout-count", type=int, default=4, help="Number of later-numbered files to hold out.")
    parser.add_argument("--max-train-rows", type=int, default=400_000, help="Cap sampled train/val rows before splitting.")
    parser.add_argument("--max-holdout-rows", type=int, default=250_000, help="Cap held-out rows for evaluation.")
    parser.add_argument("--val-frac", type=float, default=0.25, help="Validation fraction within training files.")
    parser.add_argument("--low-fpr", type=float, default=0.01, help="Validation low-FPR target.")
    parser.add_argument("--high-recall", type=float, default=0.995, help="Validation high-recall target.")
    parser.add_argument("--random-state", type=int, default=42)
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    paths = Paths(repo_root=repo_root)
    paths.reports_dir.mkdir(parents=True, exist_ok=True)
    paths.outputs_reports_dir.mkdir(parents=True, exist_ok=True)

    files = _find_files(paths.data_dir)
    holdout_count = int(args.holdout_count)
    if holdout_count <= 0 or holdout_count >= len(files):
        raise ValueError("--holdout-count must be between 1 and len(files)-1")
    train_files = files[:-holdout_count]
    holdout_files = files[-holdout_count:]

    raw_train = _load_sampled_files(train_files, sample_frac=float(args.sample_frac), random_state=int(args.random_state))
    raw_holdout = _load_sampled_files(
        holdout_files,
        sample_frac=float(args.sample_frac),
        random_state=int(args.random_state),
    )

    X_train_all, y_train_all = _prepare_xy(raw_train)
    X_holdout, y_holdout = _prepare_xy(raw_holdout)

    X_train_all, y_train_all = _stratified_cap(
        X_train_all,
        y_train_all,
        max_rows=int(args.max_train_rows),
        random_state=int(args.random_state),
    )
    X_holdout, y_holdout = _stratified_cap(
        X_holdout,
        y_holdout,
        max_rows=int(args.max_holdout_rows),
        random_state=int(args.random_state),
    )
    X_train, X_val, y_train, y_val = _train_val_split(
        X_train_all,
        y_train_all,
        val_frac=float(args.val_frac),
        random_state=int(args.random_state),
    )

    model = _build_pipeline(random_state=int(args.random_state))
    print(f"Fitting file-wise Logistic Regression on {len(y_train)} rows...")
    model.fit(X_train, y_train)

    p_val = _predict_attack_probability(model, X_val)
    p_holdout = _predict_attack_probability(model, X_holdout)
    chosen = _choose_operating_points(
        y_val,
        p_val,
        low_fpr_target=float(args.low_fpr),
        high_recall_target=float(args.high_recall),
    )
    thresholds = {"default_0.5": 0.5, **chosen}
    operating_points = _evaluate_points(y_holdout, p_holdout, thresholds)

    try:
        import sklearn

        sklearn_version = getattr(sklearn, "__version__", None)
    except Exception:
        sklearn_version = None

    payload: Dict[str, Any] = {
        "meta": {
            "generated_utc": _utc_now_iso(),
            "sample_frac": float(args.sample_frac),
            "max_train_rows": int(args.max_train_rows),
            "max_holdout_rows": int(args.max_holdout_rows),
            "val_frac": float(args.val_frac),
            "random_state": int(args.random_state),
            "environment": {
                "python": platform.python_version(),
                "numpy": getattr(np, "__version__", None),
                "pandas": getattr(pd, "__version__", None),
                "sklearn": sklearn_version,
            },
        },
        "holdout": {
            "holdout_count": holdout_count,
            "train_files": [p.name for p in train_files],
            "holdout_files": [p.name for p in holdout_files],
        },
        "data_summary": {
            "train_model": _label_summary(y_train),
            "validation": _label_summary(y_val),
            "holdout": _label_summary(y_holdout),
        },
        "thresholds": thresholds,
        "operating_points": operating_points,
    }

    with paths.out_json.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    paths.out_md.write_text(_render_md(payload), encoding="utf-8")

    print(f"Wrote: {paths.out_json}")
    print(f"Wrote: {paths.out_md}")
    for name, block in operating_points.items():
        metrics = block["metrics"]
        print(
            f"{name}: attack_recall={metrics['attack_recall']:.6f}, "
            f"normal_recall={metrics['normal_recall_specificity']:.6f}, "
            f"fpr={metrics['fpr']:.6f}, mcc={metrics['mcc']:.6f}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
