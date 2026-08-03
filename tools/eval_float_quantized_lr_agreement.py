#!/usr/bin/env python
"""Compare float Logistic Regression with the quantized LR used by ZK circuits."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import warnings
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = REPO_ROOT / "outputs"
REPORTS = REPO_ROOT / "reports"
STAGE3 = REPO_ROOT / "stage3_zk"


@dataclass(frozen=True)
class Paths:
    model: Path = OUTPUTS / "models" / "logreg_baseline.pkl"
    model_public: Path = STAGE3 / "artifacts" / "model_public.json"
    group_map: Path = STAGE3 / "artifacts" / "group_map.json"
    reference: Path = STAGE3 / "artifacts" / "exact_shap_reference.json"
    out_json: Path = OUTPUTS / "reports" / "float_vs_quantized_lr_agreement.json"
    out_md: Path = REPORTS / "float_vs_quantized_lr_agreement.md"
    out_examples: Path = OUTPUTS / "reports" / "float_vs_quantized_lr_examples.csv"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _load_pickle(path: Path) -> Any:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            import joblib

            return joblib.load(path)
        except ImportError:
            import pickle

            with path.open("rb") as f:
                return pickle.load(f)


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


def _top3_ids(phi: np.ndarray) -> np.ndarray:
    """Return 1-based top-3 ids by descending abs(phi), tie-broken by smaller id."""
    abs_phi = np.abs(phi)
    group_ids = np.broadcast_to(np.arange(1, phi.shape[1] + 1), phi.shape)
    order = np.lexsort((group_ids, -abs_phi), axis=1)
    return (order[:, :3] + 1).astype(np.int16)


def _jaccard_from_overlap(overlap: np.ndarray) -> np.ndarray:
    return overlap.astype(np.float64) / (6.0 - overlap.astype(np.float64))


def _percent(count: int, total: int) -> float:
    return float(count / total * 100.0) if total else 0.0


def _summary(values: List[np.ndarray]) -> Dict[str, float]:
    if not values:
        return {"mean": 0.0, "p95": 0.0, "max": 0.0}
    arr = np.concatenate(values).astype(np.float64)
    return {
        "mean": float(np.mean(arr)),
        "p95": float(np.percentile(arr, 95)),
        "max": float(np.max(arr)),
    }


def _fmt_float(x: float) -> str:
    if math.isnan(x):
        return "nan"
    if abs(x) >= 1e4 or (abs(x) > 0 and abs(x) < 1e-4):
        return f"{x:.6e}"
    return f"{x:.6f}"


def _row_example(
    *,
    split: str,
    kind: str,
    row_in_split: int,
    dataset_index: int,
    y_true: int,
    float_score: float,
    quant_score_scaled: float,
    float_pred: int,
    quant_pred: int,
    float_top3: Sequence[int],
    quant_top3: Sequence[int],
) -> Dict[str, Any]:
    return {
        "split": split,
        "kind": kind,
        "row_in_split": int(row_in_split),
        "dataset_index": int(dataset_index),
        "y_true": int(y_true),
        "float_score": float(float_score),
        "quant_score_scaled": float(quant_score_scaled),
        "score_abs_error": float(abs(quant_score_scaled - float_score)),
        "float_pred": int(float_pred),
        "quant_pred": int(quant_pred),
        "float_top3": ",".join(str(int(x)) for x in float_top3),
        "quant_top3": ",".join(str(int(x)) for x in quant_top3),
    }


def evaluate_split(
    *,
    split: str,
    model: Any,
    model_public: Dict[str, Any],
    group_map: Dict[str, Any],
    reference: Dict[str, Any],
    chunk_size: int,
    max_examples: int,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    X = np.load(_split_path(split, "X"), mmap_mode="r")
    y = np.load(_split_path(split, "y"), mmap_mode="r")
    idx = np.load(_split_path(split, "idx"), mmap_mode="r")

    w_float = np.asarray(model.coef_, dtype=np.float64).reshape(-1)
    b_float = float(np.asarray(model.intercept_, dtype=np.float64).reshape(-1)[0])
    w_int = np.asarray(model_public["w_int"], dtype=np.int64)
    b_int = int(model_public["b_int"])
    sx = int(model_public["Sx"])
    sw = int(model_public["Sw"])
    scale = float(sx * sw)
    x_ref_float = np.asarray(reference["x_ref"], dtype=np.float64)
    x_ref_int = np.asarray(reference["x_ref_int"], dtype=np.int64)
    group_ids = np.asarray(group_map["feature_index_to_group_id"], dtype=np.int16)
    n_groups = int(group_map["n_groups"])

    if X.shape[1] != w_int.shape[0] or X.shape[1] != w_float.shape[0]:
        raise ValueError(f"Dimension mismatch for {split}: X={X.shape}, w_float={w_float.shape}, w_int={w_int.shape}")

    total = int(X.shape[0])
    pred_mismatch = 0
    ordered_top3_match = 0
    overlap_sum = 0.0
    jaccard_sum = 0.0
    float_attack = 0
    quant_attack = 0
    abs_score_errors: List[np.ndarray] = []
    examples: List[Dict[str, Any]] = []

    for start, end in _chunks(total, chunk_size):
        Xc = np.asarray(X[start:end], dtype=np.float64)
        yc = np.asarray(y[start:end], dtype=np.int8)
        idxc = np.asarray(idx[start:end], dtype=np.int64)

        float_score = Xc @ w_float + b_float
        float_pred = (float_score >= 0.0).astype(np.int8)

        x_int = np.rint(Xc * sx).astype(np.int64)
        quant_score = x_int @ w_int + b_int
        quant_score_scaled = quant_score.astype(np.float64) / scale
        quant_pred = (quant_score >= 0).astype(np.int8)

        abs_err = np.abs(quant_score_scaled - float_score)
        abs_score_errors.append(abs_err)

        mismatch_mask = float_pred != quant_pred
        pred_mismatch += int(np.sum(mismatch_mask))
        float_attack += int(np.sum(float_pred))
        quant_attack += int(np.sum(quant_pred))

        float_phi = np.zeros((end - start, n_groups), dtype=np.float64)
        quant_phi = np.zeros((end - start, n_groups), dtype=np.int64)
        for gid in range(1, n_groups + 1):
            mask = group_ids == gid
            float_phi[:, gid - 1] = (Xc[:, mask] - x_ref_float[mask]) @ w_float[mask]
            quant_phi[:, gid - 1] = (x_int[:, mask] - x_ref_int[mask]) @ w_int[mask]

        float_top3 = _top3_ids(float_phi)
        quant_top3 = _top3_ids(quant_phi.astype(np.float64))
        top3_same = np.all(float_top3 == quant_top3, axis=1)
        ordered_top3_match += int(np.sum(top3_same))

        overlap = (float_top3[:, :, None] == quant_top3[:, None, :]).any(axis=2).sum(axis=1)
        overlap_sum += float(np.sum(overlap))
        jaccard_sum += float(np.sum(_jaccard_from_overlap(overlap)))

        if len(examples) < max_examples and np.any(mismatch_mask):
            for local in np.where(mismatch_mask)[0].tolist():
                if len(examples) >= max_examples:
                    break
                examples.append(
                    _row_example(
                        split=split,
                        kind="prediction_mismatch",
                        row_in_split=start + local,
                        dataset_index=int(idxc[local]),
                        y_true=int(yc[local]),
                        float_score=float(float_score[local]),
                        quant_score_scaled=float(quant_score_scaled[local]),
                        float_pred=int(float_pred[local]),
                        quant_pred=int(quant_pred[local]),
                        float_top3=float_top3[local],
                        quant_top3=quant_top3[local],
                    )
                )

        if len(examples) < max_examples:
            top3_mismatch_mask = ~top3_same
            if np.any(top3_mismatch_mask):
                for local in np.where(top3_mismatch_mask)[0].tolist():
                    if len(examples) >= max_examples:
                        break
                    examples.append(
                        _row_example(
                            split=split,
                            kind="top3_order_mismatch",
                            row_in_split=start + local,
                            dataset_index=int(idxc[local]),
                            y_true=int(yc[local]),
                            float_score=float(float_score[local]),
                            quant_score_scaled=float(quant_score_scaled[local]),
                            float_pred=int(float_pred[local]),
                            quant_pred=int(quant_pred[local]),
                            float_top3=float_top3[local],
                            quant_top3=quant_top3[local],
                        )
                    )

    err_summary = _summary(abs_score_errors)
    metrics = {
        "split": split,
        "n": total,
        "prediction_agreement_rate": float(1.0 - pred_mismatch / total) if total else 0.0,
        "prediction_mismatch_count": pred_mismatch,
        "prediction_mismatch_rate": float(pred_mismatch / total) if total else 0.0,
        "float_attack_rate": float(float_attack / total) if total else 0.0,
        "quantized_attack_rate": float(quant_attack / total) if total else 0.0,
        "score_abs_error": err_summary,
        "top3_ordered_match_rate": float(ordered_top3_match / total) if total else 0.0,
        "top3_ordered_mismatch_count": int(total - ordered_top3_match),
        "mean_top3_overlap_count": float(overlap_sum / total) if total else 0.0,
        "mean_top3_jaccard": float(jaccard_sum / total) if total else 0.0,
    }
    return metrics, examples


def write_examples(path: Path, examples: Sequence[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "split",
        "kind",
        "row_in_split",
        "dataset_index",
        "y_true",
        "float_score",
        "quant_score_scaled",
        "score_abs_error",
        "float_pred",
        "quant_pred",
        "float_top3",
        "quant_top3",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in examples:
            writer.writerow(row)


def write_md(path: Path, payload: Dict[str, Any], examples: Sequence[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: List[str] = []
    lines.append("# Float LR vs Quantized LR Agreement\n\n")
    lines.append(f"Generated: {payload['created_utc']} (UTC)\n\n")
    lines.append("## Purpose\n\n")
    lines.append(
        "This report checks whether the integer Logistic Regression relation used by the ZK circuits faithfully "
        "matches the floating-point scikit-learn Logistic Regression model on the validation and test splits. "
        "The comparison uses the same public quantization artifacts as Stage 3: `Sx = 65536`, `Sw = 4096`, "
        "`w_int = round(w * Sw)`, `x_int = round(x * Sx)`, and `b_int = round(b * Sx * Sw)`.\n\n"
    )
    lines.append("## Prediction Agreement\n\n")
    lines.append("| Split | n | Agreement | Mismatches | Mismatch rate | Float attack rate | Quantized attack rate |\n")
    lines.append("|---|---:|---:|---:|---:|---:|---:|\n")
    for row in payload["splits"]:
        lines.append(
            f"| {row['split']} | {row['n']} | {_percent(row['n'] - row['prediction_mismatch_count'], row['n']):.6f}% "
            f"| {row['prediction_mismatch_count']} | {_percent(row['prediction_mismatch_count'], row['n']):.6f}% "
            f"| {row['float_attack_rate'] * 100:.6f}% | {row['quantized_attack_rate'] * 100:.6f}% |\n"
        )
    lines.append("\n## Score Approximation Error\n\n")
    lines.append("The quantized integer score is rescaled by `Sx * Sw` before comparison with the float LR logit.\n\n")
    lines.append("| Split | mean abs error | p95 abs error | max abs error |\n")
    lines.append("|---|---:|---:|---:|\n")
    for row in payload["splits"]:
        err = row["score_abs_error"]
        lines.append(f"| {row['split']} | {_fmt_float(err['mean'])} | {_fmt_float(err['p95'])} | {_fmt_float(err['max'])} |\n")
    lines.append("\n## Exact SHAP Top-3 Agreement\n\n")
    lines.append(
        "Float Exact SHAP uses `phi_g = sum_{i in G_g} w_i * (x_i - x_ref_i)`. "
        "Quantized Exact SHAP uses the Stage 3.4 integer relation "
        "`phi_g_int = sum_{i in G_g} w_int[i] * (x_int[i] - x_ref_int[i])`.\n\n"
    )
    lines.append("| Split | Ordered top-3 match | Ordered mismatches | Mean overlap / 3 | Mean Jaccard |\n")
    lines.append("|---|---:|---:|---:|---:|\n")
    for row in payload["splits"]:
        lines.append(
            f"| {row['split']} | {row['top3_ordered_match_rate'] * 100:.6f}% "
            f"| {row['top3_ordered_mismatch_count']} | {row['mean_top3_overlap_count']:.6f} "
            f"| {row['mean_top3_jaccard']:.6f} |\n"
        )

    lines.append("\n## Examples\n\n")
    if examples:
        lines.append(
            "Representative mismatch examples are written to "
            "`outputs/reports/float_vs_quantized_lr_examples.csv`. The table below shows the first few.\n\n"
        )
        lines.append("| Split | Kind | row | dataset_idx | y_true | float_score | quant_score | float_pred | quant_pred | float_top3 | quant_top3 |\n")
        lines.append("|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|\n")
        for row in examples[:10]:
            lines.append(
                f"| {row['split']} | {row['kind']} | {row['row_in_split']} | {row['dataset_index']} | {row['y_true']} "
                f"| {_fmt_float(row['float_score'])} | {_fmt_float(row['quant_score_scaled'])} "
                f"| {row['float_pred']} | {row['quant_pred']} | {row['float_top3']} | {row['quant_top3']} |\n"
            )
    else:
        lines.append("No prediction or ordered top-3 mismatches were found in the evaluated splits.\n")

    lines.append("\n## Thesis Interpretation\n\n")
    total_mismatches = sum(int(row["prediction_mismatch_count"]) for row in payload["splits"])
    if total_mismatches == 0:
        lines.append(
            "No float-vs-quantized prediction mismatches were observed on the evaluated validation/test splits. "
            "This supports the claim that the ZK circuit proves the intended Logistic Regression decision rule "
            "rather than a materially different quantized surrogate, under the current artifacts.\n\n"
        )
    else:
        lines.append(
            "The evaluated splits contain float-vs-quantized prediction mismatches. These cases should be treated "
            "as quantization boundary effects: the ZK proof remains correct for the integer circuit relation, but "
            "the thesis should report that the quantized relation can differ from the floating-point sklearn model "
            "near the decision boundary.\n\n"
        )
    lines.append(
        "This is an empirical agreement check, not a cryptographic proof of equivalence for all possible inputs. "
        "The formal ZK claim remains the integer relation encoded in the circuit and bound by the public artifacts.\n"
    )

    path.write_text("".join(lines), encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--splits", default="val,test", help="Comma-separated splits to evaluate.")
    parser.add_argument("--chunk-size", type=int, default=50000, help="Rows per chunk.")
    parser.add_argument("--max-examples", type=int, default=20, help="Maximum mismatch examples to store.")
    args = parser.parse_args(argv)

    paths = Paths()
    model = _load_pickle(paths.model)
    model_public = _read_json(paths.model_public)
    group_map = _read_json(paths.group_map)
    reference = _read_json(paths.reference)

    split_names = [part.strip() for part in args.splits.split(",") if part.strip()]
    payload: Dict[str, Any] = {
        "created_utc": _utc_now_iso(),
        "model": str(paths.model.relative_to(REPO_ROOT)),
        "model_public": str(paths.model_public.relative_to(REPO_ROOT)),
        "reference": str(paths.reference.relative_to(REPO_ROOT)),
        "Sx": int(model_public["Sx"]),
        "Sw": int(model_public["Sw"]),
        "splits": [],
    }
    all_examples: List[Dict[str, Any]] = []

    for split in split_names:
        metrics, examples = evaluate_split(
            split=split,
            model=model,
            model_public=model_public,
            group_map=group_map,
            reference=reference,
            chunk_size=int(args.chunk_size),
            max_examples=max(0, int(args.max_examples) - len(all_examples)),
        )
        payload["splits"].append(metrics)
        all_examples.extend(examples)

    paths.out_json.parent.mkdir(parents=True, exist_ok=True)
    with paths.out_json.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    write_examples(paths.out_examples, all_examples)
    write_md(paths.out_md, payload, all_examples)

    print(f"Wrote: {paths.out_json}")
    print(f"Wrote: {paths.out_examples}")
    print(f"Wrote: {paths.out_md}")
    for row in payload["splits"]:
        print(
            f"{row['split']}: pred agreement={row['prediction_agreement_rate'] * 100:.6f}%, "
            f"top3 ordered match={row['top3_ordered_match_rate'] * 100:.6f}%"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
