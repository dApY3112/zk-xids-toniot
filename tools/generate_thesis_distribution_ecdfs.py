#!/usr/bin/env python
"""Generate thesis ECDFs for Stage 3.4 margin and quantization analyses."""

from __future__ import annotations

import csv
import json
import os
import platform
import subprocess
import sys
import time
import tracemalloc
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

sys.dont_write_bytecode = True

import numpy as np

from analyze_exact_shap_ranking_margin import _chunks as shap_chunks
from analyze_exact_shap_ranking_margin import _ordered_group_ids
from eval_float_quantized_lr_agreement import _load_pickle
from eval_float_quantized_lr_agreement import _split_path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_EXTRA = ROOT / "outputs" / "thesis_extra"
FIG_DIR = ROOT / "reports" / "figures" / "thesis_extra"
REPORT_EXTRA = ROOT / "reports" / "thesis_extra"
REPORT_PATH = ROOT / "THESIS_ECDF_GENERATION_REPORT.md"
STAGE3 = ROOT / "stage3_zk"

os.environ.setdefault("MPLCONFIGDIR", str(OUTPUT_EXTRA / "mplconfig"))


@dataclass(frozen=True)
class Targets:
    shap_npz: Path = OUTPUT_EXTRA / "exact_shap_rank34_margins.npz"
    lr_npz: Path = OUTPUT_EXTRA / "float_quantized_lr_score_errors.npz"
    shap_summary_json: Path = REPORT_EXTRA / "exact_shap_rank34_margin_ecdf_summary.json"
    lr_summary_json: Path = REPORT_EXTRA / "float_quantized_lr_error_ecdf_summary.json"
    shap_percentiles_csv: Path = REPORT_EXTRA / "exact_shap_rank34_margin_percentiles.csv"
    lr_percentiles_csv: Path = REPORT_EXTRA / "float_quantized_lr_error_percentiles.csv"
    shap_png: Path = FIG_DIR / "exact_shap_rank34_margin_ecdf.png"
    shap_svg: Path = FIG_DIR / "exact_shap_rank34_margin_ecdf.svg"
    lr_png: Path = FIG_DIR / "float_quantized_lr_absolute_error_ecdf.png"
    lr_svg: Path = FIG_DIR / "float_quantized_lr_absolute_error_ecdf.svg"
    generation_report: Path = REPORT_PATH

    def all_files(self) -> List[Path]:
        return [
            self.shap_npz,
            self.lr_npz,
            self.shap_summary_json,
            self.lr_summary_json,
            self.shap_percentiles_csv,
            self.lr_percentiles_csv,
            self.shap_png,
            self.shap_svg,
            self.lr_png,
            self.lr_svg,
            self.generation_report,
        ]


class MemoryTracker:
    def __init__(self) -> None:
        self._psutil = None
        self._process = None
        self.peak_rss_mb: float | None = None
        try:
            import psutil

            self._psutil = psutil
            self._process = psutil.Process(os.getpid())
        except Exception:
            self._psutil = None
            self._process = None

    def sample(self) -> None:
        if self._process is None:
            return
        rss_mb = self._process.memory_info().rss / (1024.0 * 1024.0)
        if self.peak_rss_mb is None or rss_mb > self.peak_rss_mb:
            self.peak_rss_mb = float(rss_mb)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _write_json_no_overwrite(path: Path, payload: Any) -> None:
    _assert_new_file(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def _write_text_no_overwrite(path: Path, text: str) -> None:
    _assert_new_file(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _assert_new_file(path: Path) -> None:
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite existing file: {path.relative_to(ROOT)}")


def _preflight_no_overwrite(targets: Targets) -> None:
    existing = [p.relative_to(ROOT) for p in targets.all_files() if p.exists()]
    if existing:
        formatted = "\n".join(f"  - {p}" for p in existing)
        raise FileExistsError("Refusing to run because target files already exist:\n" + formatted)


def _percentile(values: np.ndarray, q: float) -> float:
    return float(np.percentile(values.astype(np.float64), q))


def _basic_distribution(values: np.ndarray) -> Dict[str, float | int]:
    arr = values.astype(np.float64)
    return {
        "sample_count": int(arr.size),
        "minimum": float(np.min(arr)),
        "p1": _percentile(arr, 1),
        "p5": _percentile(arr, 5),
        "p10": _percentile(arr, 10),
        "p25": _percentile(arr, 25),
        "median": float(np.median(arr)),
        "p75": _percentile(arr, 75),
        "p90": _percentile(arr, 90),
        "p95": _percentile(arr, 95),
        "p99": _percentile(arr, 99),
        "maximum": float(np.max(arr)),
        "mean": float(np.mean(arr)),
        "standard_deviation": float(np.std(arr)),
    }


def _rate_dict(values: np.ndarray, thresholds: Sequence[float]) -> Dict[str, Dict[str, float | int]]:
    out: Dict[str, Dict[str, float | int]] = {}
    total = int(values.size)
    for threshold in thresholds:
        mask = values <= threshold
        count = int(np.sum(mask))
        out[f"le_{threshold:g}"] = {
            "threshold": float(threshold),
            "count": count,
            "rate": float(count / total) if total else 0.0,
            "percent": float(count / total * 100.0) if total else 0.0,
        }
    return out


def _compact_stats(values: np.ndarray) -> Dict[str, float | int | None]:
    arr = values.astype(np.float64)
    if arr.size == 0:
        return {
            "sample_count": 0,
            "mean": None,
            "median": None,
            "p95": None,
            "maximum": None,
        }
    return {
        "sample_count": int(arr.size),
        "mean": float(np.mean(arr)),
        "median": float(np.median(arr)),
        "p95": _percentile(arr, 95),
        "maximum": float(np.max(arr)),
    }


def _load_model_public() -> Dict[str, Any]:
    return _read_json(STAGE3 / "artifacts" / "model_public.json")


def _load_group_map() -> Dict[str, Any]:
    return _read_json(STAGE3 / "artifacts" / "group_map.json")


def _load_reference() -> Dict[str, Any]:
    return _read_json(STAGE3 / "artifacts" / "exact_shap_reference.json")


def compute_shap_rank34(
    *,
    split: str,
    model_public: Dict[str, Any],
    group_map: Dict[str, Any],
    reference: Dict[str, Any],
    chunk_size: int,
    memory: MemoryTracker,
) -> Dict[str, np.ndarray]:
    X = np.load(_split_path(split, "X"), mmap_mode="r")

    sx = int(model_public["Sx"])
    sw = int(model_public["Sw"])
    scale = float(sx * sw)
    w_int = np.asarray(model_public["w_int"], dtype=np.int64)
    x_ref_int = np.asarray(reference["x_ref_int"], dtype=np.int64)
    group_ids = np.asarray(group_map["feature_index_to_group_id"], dtype=np.int16)
    n_groups = int(group_map["n_groups"])

    margin_int_parts: List[np.ndarray] = []
    margin_scaled_parts: List[np.ndarray] = []
    rank3_parts: List[np.ndarray] = []
    rank4_parts: List[np.ndarray] = []

    for start, end in shap_chunks(int(X.shape[0]), chunk_size):
        memory.sample()
        Xc = np.asarray(X[start:end], dtype=np.float64)
        x_int = np.rint(Xc * sx).astype(np.int64)

        phi = np.zeros((end - start, n_groups), dtype=np.int64)
        for gid in range(1, n_groups + 1):
            mask = group_ids == gid
            phi[:, gid - 1] = (x_int[:, mask] - x_ref_int[mask]) @ w_int[mask]

        abs_phi = np.abs(phi)
        ordered_ids = _ordered_group_ids(abs_phi)
        ordered_abs = np.take_along_axis(abs_phi, ordered_ids.astype(np.int64) - 1, axis=1)
        margin_int = (ordered_abs[:, 2] - ordered_abs[:, 3]).astype(np.int64)

        margin_int_parts.append(margin_int)
        margin_scaled_parts.append(margin_int.astype(np.float64) / scale)
        rank3_parts.append(ordered_ids[:, 2].astype(np.int16))
        rank4_parts.append(ordered_ids[:, 3].astype(np.int16))
        memory.sample()

    return {
        "margin_int": np.concatenate(margin_int_parts),
        "margin_scaled": np.concatenate(margin_scaled_parts),
        "rank3_group_id": np.concatenate(rank3_parts),
        "rank4_group_id": np.concatenate(rank4_parts),
    }


def compute_lr_errors(
    *,
    split: str,
    model: Any,
    model_public: Dict[str, Any],
    chunk_size: int,
    memory: MemoryTracker,
) -> Dict[str, np.ndarray]:
    X = np.load(_split_path(split, "X"), mmap_mode="r")
    y = np.load(_split_path(split, "y"), mmap_mode="r")

    w_float = np.asarray(model.coef_, dtype=np.float64).reshape(-1)
    b_float = float(np.asarray(model.intercept_, dtype=np.float64).reshape(-1)[0])
    w_int = np.asarray(model_public["w_int"], dtype=np.int64)
    b_int = int(model_public["b_int"])
    sx = int(model_public["Sx"])
    sw = int(model_public["Sw"])
    scale = float(sx * sw)

    if X.shape[0] != y.shape[0]:
        raise ValueError(f"Split {split} has mismatched X and y lengths: {X.shape[0]} vs {y.shape[0]}")
    if X.shape[1] != w_float.shape[0] or X.shape[1] != w_int.shape[0]:
        raise ValueError(f"Split {split} has feature/model mismatch: X={X.shape}, w_float={w_float.shape}, w_int={w_int.shape}")

    float_score_parts: List[np.ndarray] = []
    quant_score_scaled_parts: List[np.ndarray] = []
    signed_error_parts: List[np.ndarray] = []
    absolute_error_parts: List[np.ndarray] = []
    float_pred_parts: List[np.ndarray] = []
    quant_pred_parts: List[np.ndarray] = []
    mismatch_parts: List[np.ndarray] = []
    float_distance_parts: List[np.ndarray] = []
    quant_distance_parts: List[np.ndarray] = []

    for start, end in shap_chunks(int(X.shape[0]), chunk_size):
        memory.sample()
        Xc = np.asarray(X[start:end], dtype=np.float64)
        float_score = Xc @ w_float + b_float
        float_pred = (float_score >= 0.0).astype(np.int8)

        x_int = np.rint(Xc * sx).astype(np.int64)
        quant_score = x_int @ w_int + b_int
        quant_score_scaled = quant_score.astype(np.float64) / scale
        quant_pred = (quant_score >= 0).astype(np.int8)

        signed_error = quant_score_scaled - float_score
        absolute_error = np.abs(signed_error)
        mismatch = (float_pred != quant_pred)

        float_score_parts.append(float_score.astype(np.float64))
        quant_score_scaled_parts.append(quant_score_scaled.astype(np.float64))
        signed_error_parts.append(signed_error.astype(np.float64))
        absolute_error_parts.append(absolute_error.astype(np.float64))
        float_pred_parts.append(float_pred)
        quant_pred_parts.append(quant_pred)
        mismatch_parts.append(mismatch.astype(np.bool_))
        float_distance_parts.append(np.abs(float_score).astype(np.float64))
        quant_distance_parts.append(np.abs(quant_score_scaled).astype(np.float64))
        memory.sample()

    return {
        "float_score": np.concatenate(float_score_parts),
        "quant_score_scaled": np.concatenate(quant_score_scaled_parts),
        "signed_score_error": np.concatenate(signed_error_parts),
        "absolute_score_error": np.concatenate(absolute_error_parts),
        "float_prediction": np.concatenate(float_pred_parts),
        "quantized_prediction": np.concatenate(quant_pred_parts),
        "prediction_mismatch": np.concatenate(mismatch_parts),
        "float_distance_to_boundary": np.concatenate(float_distance_parts),
        "quantized_distance_to_boundary": np.concatenate(quant_distance_parts),
    }


def summarize_shap(split_arrays: Dict[str, Dict[str, np.ndarray]]) -> Dict[str, Any]:
    thresholds = [0.0001, 0.001, 0.005, 0.01, 0.05, 0.1]
    out: Dict[str, Any] = {
        "created_utc": _utc_now_iso(),
        "definition": "margin_scaled = (abs_phi_rank3_int - abs_phi_rank4_int) / (Sx * Sw)",
        "splits": {},
    }
    for split, arrays in split_arrays.items():
        margin = arrays["margin_scaled"]
        summary = _basic_distribution(margin)
        zero_count = int(np.sum(margin == 0.0))
        summary["rate_equal_to_zero"] = float(zero_count / margin.size) if margin.size else 0.0
        summary["percent_equal_to_zero"] = float(zero_count / margin.size * 100.0) if margin.size else 0.0
        summary["threshold_rates"] = _rate_dict(margin, thresholds)
        out["splits"][split] = summary
    return out


def summarize_lr(split_arrays: Dict[str, Dict[str, np.ndarray]]) -> Dict[str, Any]:
    thresholds = [0.001, 0.01, 0.05, 0.1, 0.5, 1.0]
    out: Dict[str, Any] = {
        "created_utc": _utc_now_iso(),
        "definition": "absolute_score_error = abs((score_int / (Sx * Sw)) - float_score)",
        "splits": {},
    }
    for split, arrays in split_arrays.items():
        abs_err = arrays["absolute_score_error"]
        signed_err = arrays["signed_score_error"]
        mismatch = arrays["prediction_mismatch"].astype(bool)
        mismatch_count = int(np.sum(mismatch))
        total = int(abs_err.size)
        out["splits"][split] = {
            "sample_count": total,
            "mean_absolute_error": float(np.mean(abs_err)),
            "median_absolute_error": float(np.median(abs_err)),
            "p90": _percentile(abs_err, 90),
            "p95": _percentile(abs_err, 95),
            "p99": _percentile(abs_err, 99),
            "p99_9": _percentile(abs_err, 99.9),
            "maximum_absolute_error": float(np.max(abs_err)),
            "mean_signed_error": float(np.mean(signed_err)),
            "standard_deviation": float(np.std(abs_err)),
            "prediction_mismatches": mismatch_count,
            "prediction_agreement": float(1.0 - mismatch_count / total) if total else 0.0,
            "prediction_agreement_percent": float((1.0 - mismatch_count / total) * 100.0) if total else 0.0,
            "mismatch_error_statistics": _compact_stats(abs_err[mismatch]),
            "non_mismatch_error_statistics": _compact_stats(abs_err[~mismatch]),
            "threshold_percentages": _rate_dict(abs_err, thresholds),
            "zero_error_count": int(np.sum(abs_err == 0.0)),
            "zero_error_rate": float(np.mean(abs_err == 0.0)) if total else 0.0,
        }
    return out


def _validate_scalar(
    checks: List[Dict[str, Any]],
    *,
    name: str,
    actual: float | int,
    expected: float | int,
    tolerance: float,
) -> None:
    deviation = float(actual) - float(expected)
    checks.append(
        {
            "name": name,
            "actual": float(actual),
            "expected": float(expected),
            "deviation": deviation,
            "absolute_deviation": abs(deviation),
            "tolerance": float(tolerance),
            "status": "PASS" if abs(deviation) <= tolerance else "FAIL",
        }
    )


def validate_summaries(shap_summary: Dict[str, Any], lr_summary: Dict[str, Any]) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []

    shap_targets = {
        "val": {
            "sample_count": (502628, 0),
            "minimum": (0.000001, 5e-7),
            "p5": (0.000411, 5e-7),
            "median": (0.044013, 5e-7),
            "le_0.001_percent": (11.172279, 1e-5),
            "le_0.01_percent": (26.80, 1e-2),
        },
        "test": {
            "sample_count": (502628, 0),
            "minimum": (0.000001, 5e-7),
            "p5": (0.000411, 5e-7),
            "median": (0.044013, 5e-7),
            "le_0.001_percent": (11.080163, 1e-5),
            "le_0.01_percent": (26.81, 1e-2),
        },
    }
    for split, targets in shap_targets.items():
        row = shap_summary["splits"][split]
        _validate_scalar(
            checks,
            name=f"shap.{split}.sample_count",
            actual=int(row["sample_count"]),
            expected=targets["sample_count"][0],
            tolerance=targets["sample_count"][1],
        )
        for key in ["minimum", "p5", "median"]:
            expected, tol = targets[key]
            _validate_scalar(checks, name=f"shap.{split}.{key}", actual=float(row[key]), expected=expected, tolerance=tol)
        _validate_scalar(
            checks,
            name=f"shap.{split}.margin_le_0.001_percent",
            actual=float(row["threshold_rates"]["le_0.001"]["percent"]),
            expected=targets["le_0.001_percent"][0],
            tolerance=targets["le_0.001_percent"][1],
        )
        _validate_scalar(
            checks,
            name=f"shap.{split}.margin_le_0.01_percent",
            actual=float(row["threshold_rates"]["le_0.01"]["percent"]),
            expected=targets["le_0.01_percent"][0],
            tolerance=targets["le_0.01_percent"][1],
        )

    lr_targets = {
        "val": {
            "sample_count": (502628, 0),
            "prediction_agreement_percent": (99.991246, 1e-5),
            "prediction_mismatches": (44, 0),
            "mean_absolute_error": (0.040946, 1e-6),
            "p95": (0.116889, 1e-6),
            "maximum_absolute_error": (161.208082, 1e-5),
        },
        "test": {
            "sample_count": (502628, 0),
            "prediction_agreement_percent": (99.994230, 1e-5),
            "prediction_mismatches": (29, 0),
            "mean_absolute_error": (0.041297, 1e-6),
            "p95": (0.116913, 1e-6),
            "maximum_absolute_error": (154.911022, 1e-5),
        },
    }
    for split, targets in lr_targets.items():
        row = lr_summary["splits"][split]
        for key, (expected, tol) in targets.items():
            actual = row[key]
            _validate_scalar(checks, name=f"lr.{split}.{key}", actual=actual, expected=expected, tolerance=tol)

    return {
        "status": "PASS" if all(check["status"] == "PASS" for check in checks) else "FAIL",
        "checks": checks,
    }


def write_npz_outputs(targets: Targets, shap_arrays: Dict[str, Dict[str, np.ndarray]], lr_arrays: Dict[str, Dict[str, np.ndarray]]) -> None:
    _assert_new_file(targets.shap_npz)
    targets.shap_npz.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        targets.shap_npz,
        val_margin_int=shap_arrays["val"]["margin_int"],
        val_margin_scaled=shap_arrays["val"]["margin_scaled"],
        test_margin_int=shap_arrays["test"]["margin_int"],
        test_margin_scaled=shap_arrays["test"]["margin_scaled"],
        val_rank3_group_id=shap_arrays["val"]["rank3_group_id"],
        val_rank4_group_id=shap_arrays["val"]["rank4_group_id"],
        test_rank3_group_id=shap_arrays["test"]["rank3_group_id"],
        test_rank4_group_id=shap_arrays["test"]["rank4_group_id"],
    )

    _assert_new_file(targets.lr_npz)
    targets.lr_npz.parent.mkdir(parents=True, exist_ok=True)
    payload: Dict[str, np.ndarray] = {}
    for split in ["val", "test"]:
        for key, value in lr_arrays[split].items():
            payload[f"{split}_{key}"] = value
    np.savez_compressed(targets.lr_npz, **payload)


def write_percentile_csvs(targets: Targets, shap_arrays: Dict[str, Dict[str, np.ndarray]], lr_arrays: Dict[str, Dict[str, np.ndarray]]) -> None:
    percentiles = [0, 1, 5, 10, 25, 50, 75, 90, 95, 99, 99.9, 100]

    _assert_new_file(targets.shap_percentiles_csv)
    targets.shap_percentiles_csv.parent.mkdir(parents=True, exist_ok=True)
    with targets.shap_percentiles_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["analysis", "split", "percentile", "value"])
        for split in ["val", "test"]:
            arr = shap_arrays[split]["margin_scaled"]
            for p in percentiles:
                writer.writerow(["exact_shap_rank34_margin_scaled", split, p, float(np.percentile(arr, p))])

    _assert_new_file(targets.lr_percentiles_csv)
    targets.lr_percentiles_csv.parent.mkdir(parents=True, exist_ok=True)
    with targets.lr_percentiles_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["analysis", "split", "percentile", "value"])
        for split in ["val", "test"]:
            arr = lr_arrays[split]["absolute_score_error"]
            for p in percentiles:
                writer.writerow(["float_quantized_lr_absolute_score_error", split, p, float(np.percentile(arr, p))])


def _ecdf(values: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    xs = np.sort(values.astype(np.float64))
    ys = np.arange(1, xs.size + 1, dtype=np.float64) / float(xs.size)
    return xs, ys


def _configure_axis_for_nonnegative(ax: Any, values: Sequence[np.ndarray]) -> str:
    combined = np.concatenate([v.astype(np.float64) for v in values])
    if np.any(combined == 0.0):
        positives = combined[combined > 0.0]
        linthresh = float(np.min(positives)) if positives.size else 1e-12
        ax.set_xscale("symlog", linthresh=linthresh)
        return f"Zero values are shown with a symmetric-log x-axis, linthresh={linthresh:.6e}."
    ax.set_xscale("log")
    return "No zero values were present; a logarithmic x-axis is used without epsilon replacement."


def _prepare_figure_target(path: Path, *, overwrite: bool) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite existing file: {path.relative_to(ROOT)}")
    path.parent.mkdir(parents=True, exist_ok=True)


def write_figures(
    targets: Targets,
    shap_arrays: Dict[str, Dict[str, np.ndarray]],
    lr_arrays: Dict[str, Dict[str, np.ndarray]],
    lr_summary: Dict[str, Any],
    *,
    overwrite: bool = False,
) -> Dict[str, str]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figure_notes: Dict[str, str] = {}

    _prepare_figure_target(targets.shap_png, overwrite=overwrite)
    _prepare_figure_target(targets.shap_svg, overwrite=overwrite)
    fig, ax = plt.subplots(figsize=(6.5, 4.0), facecolor="white")
    for split, color, linestyle in [("val", "#0072B2", "-"), ("test", "#D55E00", "--")]:
        xs, ys = _ecdf(shap_arrays[split]["margin_scaled"])
        ax.step(xs, ys, where="post", label=f"{split} split", color=color, linestyle=linestyle, linewidth=1.8)
    zero_note = _configure_axis_for_nonnegative(
        ax,
        [shap_arrays["val"]["margin_scaled"], shap_arrays["test"]["margin_scaled"]],
    )
    for threshold, style in [(0.001, ":"), (0.01, "-.")]:
        ax.axvline(threshold, color="#666666", linestyle=style, linewidth=1.1, label=f"{threshold:g} threshold")
    ax.set_xlabel("Absolute Exact SHAP margin between ranks 3 and 4")
    ax.set_ylabel("Empirical cumulative proportion")
    ax.grid(True, which="both", color="0.88", linewidth=0.6)
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(targets.shap_png, dpi=300, facecolor="white")
    fig.savefig(targets.shap_svg, facecolor="white")
    plt.close(fig)
    figure_notes["shap_margin_axis_note"] = zero_note

    _prepare_figure_target(targets.lr_png, overwrite=overwrite)
    _prepare_figure_target(targets.lr_svg, overwrite=overwrite)
    fig, ax = plt.subplots(figsize=(6.5, 4.0), facecolor="white")
    for split, color, linestyle in [("val", "#0072B2", "-"), ("test", "#D55E00", "--")]:
        xs, ys = _ecdf(lr_arrays[split]["absolute_score_error"])
        ax.step(xs, ys, where="post", label=f"{split} split", color=color, linestyle=linestyle, linewidth=1.8)
    zero_note = _configure_axis_for_nonnegative(
        ax,
        [lr_arrays["val"]["absolute_score_error"], lr_arrays["test"]["absolute_score_error"]],
    )
    p95_val = float(lr_summary["splits"]["val"]["p95"])
    p95_test = float(lr_summary["splits"]["test"]["p95"])
    ax.axvline(p95_val, color="#0072B2", linestyle=":", linewidth=1.1, label="val p95")
    ax.axvline(p95_test, color="#D55E00", linestyle="-.", linewidth=1.1, label="test p95")
    ax.set_xlabel("Absolute score error")
    ax.set_ylabel("Empirical cumulative proportion")
    ax.grid(True, which="both", color="0.88", linewidth=0.6)
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(targets.lr_png, dpi=300, facecolor="white")
    fig.savefig(targets.lr_svg, facecolor="white")
    plt.close(fig)
    figure_notes["lr_error_axis_note"] = zero_note

    return figure_notes


def _module_version(module_name: str) -> str:
    try:
        module = __import__(module_name)
        return str(getattr(module, "__version__", "unknown"))
    except Exception as exc:
        return f"unavailable ({exc})"


def _git_revision() -> str:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=30,
        )
        if proc.returncode == 0:
            return proc.stdout.strip()
    except Exception:
        pass
    return "unavailable"


def _relative_paths(paths: Sequence[Path]) -> List[str]:
    return [str(path.relative_to(ROOT)).replace("\\", "/") for path in paths]


def write_generation_report(
    *,
    targets: Targets,
    shap_summary: Dict[str, Any],
    lr_summary: Dict[str, Any],
    validation: Dict[str, Any],
    figure_notes: Dict[str, str],
    started_utc: str,
    finished_utc: str,
    elapsed_s: float,
    peak_rss_mb: float | None,
    tracemalloc_peak_mb: float,
    command: str,
) -> None:
    output_paths = _relative_paths(targets.all_files())
    files_inspected = [
        "tools/analyze_exact_shap_ranking_margin.py",
        "outputs/reports/exact_shap_ranking_margin.json",
        "outputs/reports/exact_shap_ranking_margin_examples.csv",
        "tools/eval_float_quantized_lr_agreement.py",
        "outputs/reports/float_vs_quantized_lr_agreement.json",
        "outputs/reports/float_vs_quantized_lr_examples.csv",
        "outputs/models/logreg_baseline.pkl",
        "outputs/processed/X_val.npy",
        "outputs/processed/X_test.npy",
        "outputs/processed/y_val.npy",
        "outputs/processed/y_test.npy",
        "stage3_zk/artifacts/model_public.json",
        "stage3_zk/artifacts/group_map.json",
        "stage3_zk/artifacts/exact_shap_reference.json",
    ]

    lines: List[str] = []
    lines.append("# Thesis ECDF Generation Report\n\n")
    lines.append(f"Started: {started_utc} (UTC)\n")
    lines.append(f"Finished: {finished_utc} (UTC)\n")
    lines.append(f"Elapsed time: {elapsed_s:.2f} seconds\n")
    if peak_rss_mb is not None:
        lines.append(f"Peak process RSS: {peak_rss_mb:.2f} MiB\n")
    else:
        lines.append("Peak process RSS: unavailable; `psutil` was not available.\n")
    lines.append(f"Peak traced Python allocation: {tracemalloc_peak_mb:.2f} MiB\n\n")

    lines.append("## Files Inspected\n\n")
    for path in files_inspected:
        lines.append(f"- `{path}`\n")

    lines.append("\n## Scripts And Functions Reused\n\n")
    lines.append("- `tools/analyze_exact_shap_ranking_margin.py`: reused `_chunks` and `_ordered_group_ids`.\n")
    lines.append("- `tools/eval_float_quantized_lr_agreement.py`: reused `_load_pickle` and `_split_path`.\n")
    lines.append("- The new script preserves the same quantized LR, Exact SHAP, rounding, scaling, and ranking conventions as the existing reports.\n\n")

    lines.append("## Mathematical Definitions\n\n")
    lines.append("- Exact SHAP group value: `phi_g_int = sum_{i in group g} w_int[i] * (x_int[i] - x_ref_int[i])`.\n")
    lines.append("- Rank-3/rank-4 margin: `margin_scaled = (abs_phi_rank3_int - abs_phi_rank4_int) / (Sx * Sw)`.\n")
    lines.append("- Float LR score: `float_score = X @ w_float + b_float`.\n")
    lines.append("- Quantized LR score: `quant_score_scaled = (x_int @ w_int + b_int) / (Sx * Sw)`.\n")
    lines.append("- Signed score error: `quant_score_scaled - float_score`.\n")
    lines.append("- Absolute score error: `abs(quant_score_scaled - float_score)`.\n")
    lines.append("- Prediction mismatch: `(float_score >= 0) != (quant_score_int >= 0)`.\n\n")

    lines.append("## Input Artifacts And Sample Counts\n\n")
    for split in ["val", "test"]:
        lines.append(f"- `{split}` Exact SHAP margins: {shap_summary['splits'][split]['sample_count']} samples.\n")
        lines.append(f"- `{split}` LR score errors: {lr_summary['splits'][split]['sample_count']} samples.\n")
    lines.append("\n")

    lines.append("## Runtime Environment\n\n")
    lines.append(f"- Python: `{platform.python_version()}`\n")
    lines.append(f"- Platform: `{platform.platform()}`\n")
    lines.append(f"- NumPy: `{np.__version__}`\n")
    lines.append(f"- Matplotlib: `{_module_version('matplotlib')}`\n")
    lines.append(f"- Joblib: `{_module_version('joblib')}`\n")
    lines.append(f"- scikit-learn: `{_module_version('sklearn')}`\n")
    lines.append(f"- Git revision: `{_git_revision()}`\n\n")

    lines.append("## Execution Commands\n\n")
    lines.append("```text\n")
    lines.append(command + "\n")
    lines.append("```\n\n")

    lines.append("## Validation Against Existing Thesis Values\n\n")
    lines.append(f"Overall validation status: `{validation['status']}`\n\n")
    lines.append("| Check | Actual | Expected | Deviation | Tolerance | Status |\n")
    lines.append("|---|---:|---:|---:|---:|---|\n")
    for check in validation["checks"]:
        lines.append(
            f"| `{check['name']}` | {check['actual']:.12g} | {check['expected']:.12g} | "
            f"{check['deviation']:.12g} | {check['tolerance']:.12g} | {check['status']} |\n"
        )

    lines.append("\n## Exact Deviations From Existing Reports\n\n")
    lines.append("All validation deviations are listed in the table above. All checks passed within the stated formatting tolerances.\n\n")

    lines.append("## Output File Paths\n\n")
    for path in output_paths:
        lines.append(f"- `{path}`\n")

    lines.append("\n## Figure Captions\n\n")
    val_le_0001 = shap_summary["splits"]["val"]["threshold_rates"]["le_0.001"]["percent"]
    test_le_0001 = shap_summary["splits"]["test"]["threshold_rates"]["le_0.001"]["percent"]
    val_le_001 = shap_summary["splits"]["val"]["threshold_rates"]["le_0.01"]["percent"]
    test_le_001 = shap_summary["splits"]["test"]["threshold_rates"]["le_0.01"]["percent"]
    lines.append(
        "Figure X. Empirical cumulative distribution of the Stage 3.4 quantized Exact SHAP margin between the third- and fourth-ranked semantic groups. "
        f"The validation and test splits each contain 502,628 samples. Margins at or below 0.001 occur in {val_le_0001:.4f}% of validation samples and {test_le_0001:.4f}% of test samples; "
        f"margins at or below 0.01 occur in {val_le_001:.4f}% and {test_le_001:.4f}% respectively. {figure_notes['shap_margin_axis_note']}\n\n"
    )
    lines.append(
        "Figure Y. Empirical cumulative distribution of the absolute score difference between the floating-point Logistic Regression model and the quantized Logistic Regression relation used by Stage 3.4. "
        f"The p95 absolute errors are {lr_summary['splits']['val']['p95']:.6f} on validation and {lr_summary['splits']['test']['p95']:.6f} on test, while rare large deviations remain visible in the log-scaled tail. "
        f"{figure_notes['lr_error_axis_note']}\n\n"
    )

    lines.append("## Recommended Placement\n\n")
    lines.append("- Exact SHAP margin ECDF: Section 7.4.3.\n")
    lines.append("- Quantization-error ECDF: Section 7.4.1 or Appendix.\n\n")

    lines.append("## Thesis-Safe Interpretations\n\n")
    lines.append(
        "Exact SHAP margin ECDF: small rank-3/rank-4 margins identify cases where the inclusion boundary for the public top-3 explanation is empirically fragile. "
        "This does not measure proof correctness, does not establish robustness to arbitrary input perturbations, and does not invalidate the certified ranking under the quantized Stage 3.4 relation.\n\n"
    )
    lines.append(
        "Float-to-quantized LR error ECDF: most score errors are small and binary prediction agreement remains above 99.99% on both splits, but rare larger score deviations exist. "
        "The Stage 3.4 proof certifies the quantized integer relation, not exact floating-point equivalence for every possible input.\n\n"
    )

    lines.append("## Limitations And Concerns\n\n")
    lines.append("- These analyses reuse saved validation and test arrays and do not retrain any model.\n")
    lines.append("- The Exact SHAP margin figure measures the separation between ranks 3 and 4, not adversarial robustness.\n")
    lines.append("- The LR error figure measures empirical agreement on the saved splits, not formal equivalence over all possible inputs.\n")
    lines.append("- XGBoost is not evaluated in ZK and no hidden-model, model-agnostic SHAP, full provenance, or production-readiness claim is introduced.\n\n")

    lines.append("## Confirmations\n\n")
    lines.append("- No Logistic Regression or XGBoost model was retrained.\n")
    lines.append("- No preprocessing, saved models, semantic groups, quantization parameters, Circom circuits, or existing reports were modified.\n")
    lines.append("- The script checks all target files before execution and refuses to overwrite existing files.\n")
    lines.append("- Full arrays are stored in compressed NPZ files; no one-row-per-sample CSV was exported.\n")

    _write_text_no_overwrite(targets.generation_report, "".join(lines))


def verify_outputs(targets: Targets, shap_arrays: Dict[str, Dict[str, np.ndarray]], lr_arrays: Dict[str, Dict[str, np.ndarray]]) -> None:
    for path in targets.all_files():
        if not path.exists():
            raise FileNotFoundError(f"Expected output was not generated: {path.relative_to(ROOT)}")
        if path.stat().st_size <= 0:
            raise RuntimeError(f"Generated output is empty: {path.relative_to(ROOT)}")

    for split in ["val", "test"]:
        if shap_arrays[split]["margin_scaled"].shape[0] != 502628:
            raise RuntimeError(f"{split} SHAP margin array length mismatch")
        if lr_arrays[split]["absolute_score_error"].shape[0] != 502628:
            raise RuntimeError(f"{split} LR error array length mismatch")


def refresh_figures_from_saved_outputs(targets: Targets) -> None:
    required = [targets.shap_npz, targets.lr_npz, targets.lr_summary_json]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing saved outputs needed for figure refresh:\n" + "\n".join(f"  - {p}" for p in missing))

    shap_npz = np.load(targets.shap_npz)
    lr_npz = np.load(targets.lr_npz)
    shap_arrays = {
        "val": {"margin_scaled": shap_npz["val_margin_scaled"]},
        "test": {"margin_scaled": shap_npz["test_margin_scaled"]},
    }
    lr_arrays = {
        "val": {"absolute_score_error": lr_npz["val_absolute_score_error"]},
        "test": {"absolute_score_error": lr_npz["test_absolute_score_error"]},
    }
    lr_summary = _read_json(targets.lr_summary_json)
    write_figures(targets, shap_arrays, lr_arrays, lr_summary, overwrite=True)


def parse_args(argv: Sequence[str] | None = None) -> Any:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chunk-size", type=int, default=50000)
    parser.add_argument(
        "--refresh-figures-only",
        action="store_true",
        help="Regenerate only the PNG/SVG figures from existing NPZ and summary outputs.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    targets = Targets()
    if bool(args.refresh_figures_only):
        refresh_figures_from_saved_outputs(targets)
        print("Refreshed thesis ECDF figures:")
        for path in [targets.shap_png, targets.shap_svg, targets.lr_png, targets.lr_svg]:
            print(f"  {path.relative_to(ROOT)}")
        return 0

    _preflight_no_overwrite(targets)

    started_utc = _utc_now_iso()
    started = time.perf_counter()
    tracemalloc.start()
    memory = MemoryTracker()

    model_public = _load_model_public()
    group_map = _load_group_map()
    reference = _load_reference()
    model = _load_pickle(ROOT / "outputs" / "models" / "logreg_baseline.pkl")

    shap_arrays: Dict[str, Dict[str, np.ndarray]] = {}
    lr_arrays: Dict[str, Dict[str, np.ndarray]] = {}
    for split in ["val", "test"]:
        print(f"Computing Exact SHAP rank-3/rank-4 margins for {split}...")
        shap_arrays[split] = compute_shap_rank34(
            split=split,
            model_public=model_public,
            group_map=group_map,
            reference=reference,
            chunk_size=int(args.chunk_size),
            memory=memory,
        )
        print(f"Computing float-vs-quantized LR score errors for {split}...")
        lr_arrays[split] = compute_lr_errors(
            split=split,
            model=model,
            model_public=model_public,
            chunk_size=int(args.chunk_size),
            memory=memory,
        )

    shap_summary = summarize_shap(shap_arrays)
    lr_summary = summarize_lr(lr_arrays)
    validation = validate_summaries(shap_summary, lr_summary)
    if validation["status"] != "PASS":
        failed = [check for check in validation["checks"] if check["status"] != "PASS"]
        for check in failed:
            print(f"VALIDATION FAIL: {check}")
        raise RuntimeError("Validation failed; refusing to write thesis-ready ECDF figures.")

    write_npz_outputs(targets, shap_arrays, lr_arrays)
    _write_json_no_overwrite(targets.shap_summary_json, shap_summary)
    _write_json_no_overwrite(targets.lr_summary_json, lr_summary)
    write_percentile_csvs(targets, shap_arrays, lr_arrays)
    figure_notes = write_figures(targets, shap_arrays, lr_arrays, lr_summary)

    _, peak = tracemalloc.get_traced_memory()
    tracemalloc_peak_mb = peak / (1024.0 * 1024.0)
    tracemalloc.stop()
    finished_utc = _utc_now_iso()
    elapsed_s = time.perf_counter() - started
    command = "python -B tools/generate_thesis_distribution_ecdfs.py"
    if int(args.chunk_size) != 50000:
        command += f" --chunk-size {int(args.chunk_size)}"
    write_generation_report(
        targets=targets,
        shap_summary=shap_summary,
        lr_summary=lr_summary,
        validation=validation,
        figure_notes=figure_notes,
        started_utc=started_utc,
        finished_utc=finished_utc,
        elapsed_s=elapsed_s,
        peak_rss_mb=memory.peak_rss_mb,
        tracemalloc_peak_mb=tracemalloc_peak_mb,
        command=command,
    )
    verify_outputs(targets, shap_arrays, lr_arrays)

    print("Generated thesis ECDF outputs:")
    for path in targets.all_files():
        print(f"  {path.relative_to(ROOT)}")
    print(f"Elapsed seconds: {elapsed_s:.2f}")
    if memory.peak_rss_mb is not None:
        print(f"Peak RSS MiB: {memory.peak_rss_mb:.2f}")
    print(f"Peak traced Python allocation MiB: {tracemalloc_peak_mb:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
