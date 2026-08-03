#!/usr/bin/env python
"""Select diverse Stage 3.4 test vectors from the processed test split.

The initial Stage 3 vectors cover TP/TN/FN. This script adds vectors that are
useful for thesis self-assessment and ZK robustness evidence:

- false positive normal sample
- high-confidence attack
- high-confidence normal
- borderline score near zero
- near-tie Exact SHAP top-3 margin
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

import numpy as np


SCRIPT_DIR = Path(__file__).resolve().parent
STAGE3 = SCRIPT_DIR.parents[1]
REPO_ROOT = STAGE3.parent
ARTIFACTS = STAGE3 / "artifacts"
TEST_VECTORS = STAGE3 / "test_vectors"
REPORTS = STAGE3 / "reports"
OUTPUTS = REPO_ROOT / "outputs"


@dataclass
class Candidate:
    sample_no: int
    label: str
    row_in_split: int
    dataset_index: int
    y_true: int
    score_int: int
    y_hat: int
    margin_int: int
    top3_ids: List[int]
    other2_ids: List[int]
    phi: List[int]
    x_int: List[int]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _read_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def _chunks(total: int, size: int) -> Iterable[tuple[int, int]]:
    for start in range(0, total, size):
        yield start, min(start + size, total)


def _compute_phi(x_int: np.ndarray, w_int: np.ndarray, x_ref_int: np.ndarray, group_ids: np.ndarray, n_groups: int) -> List[int]:
    phi = [0] * n_groups
    diff = x_int.astype(np.int64) - x_ref_int.astype(np.int64)
    contrib = diff * w_int.astype(np.int64)
    for idx, value in enumerate(contrib):
        phi[int(group_ids[idx]) - 1] += int(value)
    return phi


def _rank_groups(phi: Sequence[int]) -> tuple[List[int], List[int], int]:
    ranked = sorted([(i + 1, abs(int(v)), int(v)) for i, v in enumerate(phi)], key=lambda item: (-item[1], item[0]))
    top3 = [gid for gid, _abs_v, _v in ranked[:3]]
    other2 = [gid for gid, _abs_v, _v in ranked[3:5]]
    margin = int(ranked[2][1] - ranked[3][1])
    return top3, other2, margin


def _candidate_for_row(
    *,
    sample_no: int,
    label: str,
    row: int,
    X_test: np.ndarray,
    y_test: np.ndarray,
    test_idx: np.ndarray,
    w_int: np.ndarray,
    b_int: int,
    sx: int,
    x_ref_int: np.ndarray,
    group_ids: np.ndarray,
    n_groups: int,
) -> Candidate:
    x_float = np.asarray(X_test[int(row)], dtype=np.float64)
    x_int = np.rint(x_float * int(sx)).astype(np.int64)
    score = int(np.dot(x_int, w_int.astype(np.int64)) + int(b_int))
    y_hat = 1 if score >= 0 else 0
    phi = _compute_phi(x_int, w_int, x_ref_int, group_ids, n_groups)
    top3, other2, margin = _rank_groups(phi)
    return Candidate(
        sample_no=sample_no,
        label=label,
        row_in_split=int(row),
        dataset_index=int(test_idx[int(row)]),
        y_true=int(y_test[int(row)]),
        score_int=score,
        y_hat=y_hat,
        margin_int=margin,
        top3_ids=top3,
        other2_ids=other2,
        phi=phi,
        x_int=[int(v) for v in x_int.tolist()],
    )


def _update_best(best: Dict[str, int | None], key: str, row: int, scores: np.ndarray, y: np.ndarray) -> None:
    current = best.get(key)
    score = int(scores[row])
    if key == "fp":
        if y[row] == 0 and score >= 0 and (current is None or score > int(scores[int(current)])):
            best[key] = int(row)
    elif key == "high_attack":
        if y[row] == 1 and score >= 0 and (current is None or score > int(scores[int(current)])):
            best[key] = int(row)
    elif key == "high_normal":
        if y[row] == 0 and score < 0 and (current is None or score < int(scores[int(current)])):
            best[key] = int(row)
    elif key == "borderline":
        if current is None or abs(score) < abs(int(scores[int(current)])):
            best[key] = int(row)


def _scan_rows(*, chunk_size: int, w_int: np.ndarray, b_int: int, sx: int, score_bound: int) -> Dict[str, int]:
    X_test = np.load(OUTPUTS / "processed" / "X_test.npy", mmap_mode="r")
    y_test = np.load(OUTPUTS / "processed" / "y_test.npy", mmap_mode="r").reshape(-1).astype(np.int8)
    best: Dict[str, int | None] = {"fp": None, "high_attack": None, "high_normal": None, "borderline": None}
    best_scores: Dict[str, int | None] = {"fp": None, "high_attack": None, "high_normal": None, "borderline": None}

    for start, end in _chunks(int(X_test.shape[0]), int(chunk_size)):
        Xc = np.asarray(X_test[start:end], dtype=np.float64)
        x_int = np.rint(Xc * int(sx)).astype(np.int64)
        scores = x_int @ w_int.astype(np.int64) + int(b_int)
        y = np.asarray(y_test[start:end], dtype=np.int8)

        in_bound = np.abs(scores) <= int(score_bound)
        masks = {
            "fp": (y == 0) & (scores >= 0) & in_bound,
            "high_attack": (y == 1) & (scores >= 0) & in_bound,
            "high_normal": (y == 0) & (scores < 0) & in_bound,
            "borderline": in_bound,
        }
        if np.any(masks["fp"]):
            local = np.where(masks["fp"])[0]
            idx = int(local[np.argmax(scores[local])])
            score = int(scores[idx])
            if best_scores["fp"] is None or score > int(best_scores["fp"]):
                best["fp"] = start + idx
                best_scores["fp"] = score
        if np.any(masks["high_attack"]):
            local = np.where(masks["high_attack"])[0]
            idx = int(local[np.argmax(scores[local])])
            score = int(scores[idx])
            if best_scores["high_attack"] is None or score > int(best_scores["high_attack"]):
                best["high_attack"] = start + idx
                best_scores["high_attack"] = score
        if np.any(masks["high_normal"]):
            local = np.where(masks["high_normal"])[0]
            idx = int(local[np.argmin(scores[local])])
            score = int(scores[idx])
            if best_scores["high_normal"] is None or score < int(best_scores["high_normal"]):
                best["high_normal"] = start + idx
                best_scores["high_normal"] = score
        if np.any(masks["borderline"]):
            local = np.where(masks["borderline"])[0]
            idx = int(local[np.argmin(np.abs(scores[local]))])
            score = int(scores[idx])
            if best_scores["borderline"] is None or abs(score) < abs(int(best_scores["borderline"])):
                best["borderline"] = start + idx
                best_scores["borderline"] = score

    out: Dict[str, int] = {}
    for key, value in best.items():
        if value is None:
            raise RuntimeError(f"No candidate found for {key}")
        out[key] = int(value)
    return out


def _small_margin_row() -> int:
    path = OUTPUTS / "reports" / "exact_shap_ranking_margin_examples.csv"
    if path.exists():
        import csv

        with path.open("r", newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row.get("split") == "test":
                    return int(row["row_in_split"])
    raise FileNotFoundError(f"Missing small-margin examples: {path}")


def _payload(candidate: Candidate, group_names: Sequence[str]) -> Dict[str, object]:
    ranked = sorted(
        [(i + 1, group_names[i], int(candidate.phi[i]), abs(int(candidate.phi[i]))) for i in range(len(candidate.phi))],
        key=lambda item: (-item[3], item[0]),
    )
    return {
        "sample_id": int(candidate.row_in_split),
        "stage34_sample_no": int(candidate.sample_no),
        "label": candidate.label,
        "y_true": int(candidate.y_true),
        "y_pred": int(candidate.y_hat),
        "dataset_index": int(candidate.dataset_index),
        "row_in_test_split": int(candidate.row_in_split),
        "x_int": candidate.x_int,
        "score_int": int(candidate.score_int),
        "score_abs_int": int(abs(candidate.score_int)),
        "y_hat": int(candidate.y_hat),
        "exact_shap_phi_int": {str(i + 1): int(v) for i, v in enumerate(candidate.phi)},
        "exact_shap_top3_groups": candidate.top3_ids,
        "other2_groups": candidate.other2_ids,
        "rank3_rank4_margin_int": int(candidate.margin_int),
        "ranked_groups": [
            {"group_id": gid, "group": name, "phi_int": phi, "abs_phi_int": abs_phi}
            for gid, name, phi, abs_phi in ranked
        ],
        "feature_order_matches": "feature_order.json",
    }


def _write_report(candidates: Sequence[Candidate], group_names: Sequence[str], *, score_bound: int) -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    json_path = REPORTS / "STAGE34_DIVERSE_TEST_VECTORS.json"
    md_path = REPORTS / "STAGE34_DIVERSE_TEST_VECTORS.md"
    payload = {
        "created_utc": _utc_now_iso(),
        "purpose": "Diverse Stage 3.4 test vectors beyond TP/TN/FN.",
        "score_bound_int": int(score_bound),
        "samples": [
            {
                "sample_no": c.sample_no,
                "label": c.label,
                "row_in_test_split": c.row_in_split,
                "dataset_index": c.dataset_index,
                "y_true": c.y_true,
                "y_hat": c.y_hat,
                "score_int": c.score_int,
                "score_abs_int": abs(c.score_int),
                "top3_ids": c.top3_ids,
                "other2_ids": c.other2_ids,
                "rank3_rank4_margin_int": c.margin_int,
                "top3_groups": [group_names[gid - 1] for gid in c.top3_ids],
            }
            for c in candidates
        ],
    }
    _write_json(json_path, payload)

    lines: List[str] = []
    lines.append("# Stage 3.4 Diverse Test Vectors\n\n")
    lines.append(f"Generated: {payload['created_utc']} (UTC)\n\n")
    lines.append(
        "These vectors extend the original TP/TN/FN proof cases with edge cases for IDS behavior and explanation stability. "
        "They are selected from the processed test split and use the same public quantized Logistic Regression artifact as Stage 3.4.\n\n"
    )
    lines.append(f"Circuit score bound used during selection: `abs(score_int) <= {int(score_bound)}`.\n\n")
    lines.append("| Stage 3.4 sample | Label | Test row | Dataset index | y_true | y_hat | score_int | abs(score) | top-3 groups | rank3-rank4 margin |\n")
    lines.append("|---:|---|---:|---:|---:|---:|---:|---:|---|---:|\n")
    for sample in payload["samples"]:
        lines.append(
            f"| {sample['sample_no']} | {sample['label']} | {sample['row_in_test_split']} | {sample['dataset_index']} | "
            f"{sample['y_true']} | {sample['y_hat']} | {sample['score_int']} | {sample['score_abs_int']} | "
            f"{', '.join(sample['top3_groups'])} | {sample['rank3_rank4_margin_int']} |\n"
        )
    lines.append("\n## Interpretation\n\n")
    lines.append("- `FP_normal` tests that the proof verifies the model's actual attack prediction even when the ground truth is Normal.\n")
    lines.append("- `HighConf_attack` and `HighConf_normal` exercise large positive and negative score margins.\n")
    lines.append("- `Borderline_score` exercises a prediction close to the LR decision boundary.\n")
    lines.append("- `SmallTop3Margin` exercises a near-tie between the third and fourth Exact SHAP semantic groups.\n")
    lines.append("- These vectors are correctness/stress evidence for the proof relation; they are not additional training data.\n")
    md_path.write_text("".join(lines), encoding="utf-8")
    print(f"Wrote: {json_path}")
    print(f"Wrote: {md_path}")


def main() -> int:
    model = _read_json(ARTIFACTS / "model_public.json")
    group_map = _read_json(ARTIFACTS / "group_map.json")
    reference = _read_json(ARTIFACTS / "exact_shap_reference.json")
    w_int = np.asarray(model["w_int"], dtype=np.int64)
    b_int = int(model["b_int"])
    sx = int(model["Sx"])
    group_ids = np.asarray(group_map["feature_index_to_group_id"], dtype=np.int16)
    group_names = list(group_map["groups"])
    x_ref_int = np.asarray(reference["x_ref_int"], dtype=np.int64)
    n_groups = int(group_map["n_groups"])

    X_test = np.load(OUTPUTS / "processed" / "X_test.npy", mmap_mode="r")
    y_test = np.load(OUTPUTS / "processed" / "y_test.npy", mmap_mode="r").reshape(-1).astype(np.int8)
    test_idx = np.load(OUTPUTS / "splits" / "test_idx.npy", mmap_mode="r")

    score_bound = 2**36
    rows = _scan_rows(chunk_size=50000, w_int=w_int, b_int=b_int, sx=sx, score_bound=score_bound)
    rows["small_margin"] = _small_margin_row()

    specs = [
        (4, "FP_normal", rows["fp"]),
        (5, "HighConf_attack", rows["high_attack"]),
        (6, "HighConf_normal", rows["high_normal"]),
        (7, "Borderline_score", rows["borderline"]),
        (8, "SmallTop3Margin", rows["small_margin"]),
    ]

    seen: set[int] = set()
    candidates: List[Candidate] = []
    for sample_no, label, row in specs:
        if int(row) in seen:
            raise RuntimeError(f"Duplicate selected row {row}; adjust selection logic")
        seen.add(int(row))
        candidate = _candidate_for_row(
            sample_no=sample_no,
            label=label,
            row=int(row),
            X_test=X_test,
            y_test=y_test,
            test_idx=test_idx,
            w_int=w_int,
            b_int=b_int,
            sx=sx,
            x_ref_int=x_ref_int,
            group_ids=group_ids,
            n_groups=n_groups,
        )
        candidates.append(candidate)
        out_path = TEST_VECTORS / f"test_sample_{sample_no}.json"
        _write_json(out_path, _payload(candidate, group_names))
        print(f"Wrote: {out_path}")

    _write_report(candidates, group_names, score_bound=score_bound)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
