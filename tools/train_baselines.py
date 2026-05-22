#!/usr/bin/env python
"""Retrain baseline models and overwrite serialized artifacts.

Why:
- Pickled models can emit warnings if loaded under a different sklearn/xgboost
  version than the one that originally created them.
- For strict reproducibility (and cleaner reports), we regenerate the baseline
  model files under the *current* environment.

This script re-fits the same baseline models as in `notebooks/04_train_and_evaluate_baseline.ipynb`:
- XGBoost (hist) with fixed hyperparameters
- Logistic Regression with class_weight="balanced"

It trains on a stratified subset of the training split to keep runtime/memory
reasonable on Windows.

Usage (from repo root):
  python tools/train_baselines.py

Recommended (use your venv Python):
    ./.venv/Scripts/python.exe tools/train_baselines.py
"""

from __future__ import annotations

import argparse
import json
import os
import platform
from dataclasses import dataclass

import numpy as np


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
    def feature_order(self) -> str:
        return os.path.join(self.processed_dir, "feature_order.json")


def _load_arrays(processed_dir: str):
    X_train = np.load(os.path.join(processed_dir, "X_train.npy"))
    y_train = np.load(os.path.join(processed_dir, "y_train.npy")).reshape(-1)
    return X_train, y_train


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repo-root",
        default=os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
        help="Repository root (default: parent of tools/)",
    )
    parser.add_argument("--subset-n", type=int, default=400_000, help="Stratified subset size for training.")
    parser.add_argument("--random-state", type=int, default=42)
    args = parser.parse_args(argv)

    repo_root = os.path.abspath(args.repo_root)
    paths = Paths(repo_root=repo_root)
    os.makedirs(paths.models_dir, exist_ok=True)

    # Imports that may not exist unless ML deps are installed
    try:
        import joblib
        from sklearn.linear_model import LogisticRegression
        from sklearn.model_selection import StratifiedShuffleSplit
    except Exception as e:
        raise RuntimeError(
            "Missing ML dependencies. Ensure scikit-learn and joblib are installed in the active environment."
        ) from e

    try:
        from xgboost import XGBClassifier
    except Exception as e:
        raise RuntimeError("Missing XGBoost dependency in the active environment.") from e

    X_train, y_train = _load_arrays(paths.processed_dir)
    if X_train.shape[0] != y_train.shape[0]:
        raise ValueError(f"Shape mismatch: X_train has {X_train.shape[0]} rows, y_train has {y_train.shape[0]}")

    subset_n = int(min(args.subset_n, X_train.shape[0]))
    sss = StratifiedShuffleSplit(n_splits=1, train_size=subset_n, random_state=int(args.random_state))
    idx_subset, _ = next(sss.split(np.zeros(len(y_train)), y_train))

    X_sub = np.asarray(X_train[idx_subset], dtype=np.float32)
    y_sub = np.asarray(y_train[idx_subset], dtype=np.int64)

    print("Environment:")
    print("- Python:", platform.python_version())
    try:
        import sklearn

        print("- scikit-learn:", sklearn.__version__)
    except Exception:
        pass
    try:
        import xgboost

        print("- xgboost:", xgboost.__version__)
    except Exception:
        pass

    print("Training subset:", X_sub.shape, y_sub.shape)
    print("Attack% (subset):", float(np.mean(y_sub)) * 100.0)

    # XGBoost baseline (match notebook)
    xgb_model = XGBClassifier(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        tree_method="hist",
        eval_metric="logloss",
        n_jobs=-1,
        random_state=int(args.random_state),
    )
    xgb_model.fit(X_sub, y_sub)

    # Logistic Regression baseline (match notebook)
    logreg_model = LogisticRegression(
        max_iter=2000,
        class_weight="balanced",
        n_jobs=1,
        random_state=int(args.random_state),
    )
    logreg_model.fit(X_sub, y_sub)

    out_xgb = os.path.join(paths.models_dir, "xgboost_baseline.pkl")
    out_lr = os.path.join(paths.models_dir, "logreg_baseline.pkl")

    joblib.dump(xgb_model, out_xgb)
    joblib.dump(logreg_model, out_lr)

    print("Wrote:", out_xgb)
    print("Wrote:", out_lr)

    # Optional: write a small metadata file for traceability
    meta_path = os.path.join(paths.models_dir, "baseline_models_meta.json")
    meta = {
        "random_state": int(args.random_state),
        "subset_n": int(subset_n),
        "attack_pct_subset": float(np.mean(y_sub)) * 100.0,
    }
    if os.path.exists(paths.feature_order):
        with open(paths.feature_order, "r", encoding="utf-8") as f:
            meta["n_features"] = len(json.load(f))
    try:
        import sklearn

        meta["sklearn_version"] = sklearn.__version__
    except Exception:
        pass
    try:
        import xgboost

        meta["xgboost_version"] = xgboost.__version__
    except Exception:
        pass

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    print("Wrote:", meta_path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
