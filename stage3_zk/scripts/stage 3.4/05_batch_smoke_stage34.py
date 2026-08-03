#!/usr/bin/env python
"""Stage 3.4 deterministic batch smoke test.

This supplemental harness selects a label-balanced deterministic batch from the
processed test split, runs the current Stage 3.4 witness/prove/verify path, and
writes a compact report. It is functional evidence only; it does not replace the
authoritative eight-vector Stage 3.4 proof report.
"""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
import time
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
BUILD_DIR = STAGE3 / "circuits" / "exact_shap_top3" / "build"
BATCH_DIR = STAGE3 / "outputs" / "batch_smoke"

SNARKJS = STAGE3 / "node_modules" / "snarkjs" / "cli.js"
WASM = BUILD_DIR / "exact_shap_top3_js" / "exact_shap_top3.wasm"
WITNESS_GEN = BUILD_DIR / "exact_shap_top3_js" / "generate_witness.js"
ZKEY_FINAL = BUILD_DIR / "exact_shap_top3_final.zkey"
VKEY = BUILD_DIR / "verification_key.json"

B_SCORE = 2**36
B_PHI = 2**47


@dataclass
class BatchCase:
    batch_id: int
    row_in_test_split: int
    dataset_index: int
    y_true: int
    y_hat: int
    top3_ids: List[int]
    other2_ids: List[int]
    top3_groups: List[str]
    x_shifted: List[int]
    w_shifted: List[int]
    b_shifted: int


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _read_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def _require(paths: Sequence[Path]) -> None:
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing required Stage 3.4 batch smoke artifacts:\n" + "\n".join(missing))


def _chunks(total: int, chunk_size: int) -> Iterable[tuple[int, int]]:
    for start in range(0, total, chunk_size):
        yield start, min(start + chunk_size, total)


def _timed(cmd: Sequence[str], *, timeout: int) -> Dict[str, object]:
    started = time.perf_counter()
    proc = subprocess.run(cmd, cwd=str(STAGE3), capture_output=True, text=True, timeout=timeout)
    return {
        "cmd": list(cmd),
        "returncode": int(proc.returncode),
        "duration_ms": int(round((time.perf_counter() - started) * 1000)),
        "stdout_tail": (proc.stdout or "")[-500:],
        "stderr_tail": (proc.stderr or "")[-500:],
    }


def _load_curated_rows() -> set[int]:
    rows: set[int] = set()
    for path in TEST_VECTORS.glob("test_sample_*.json"):
        try:
            payload = _read_json(path)
        except json.JSONDecodeError:
            continue
        row = payload.get("row_in_test_split")
        if row is not None:
            rows.add(int(row))
    return rows


def _curated_vector_file_count() -> int:
    return sum(1 for _ in TEST_VECTORS.glob("test_sample_*.json"))


def _select_rows(
    *,
    n_samples: int,
    seed: int,
    chunk_size: int,
    sx: int,
    w_int: np.ndarray,
    b_int: int,
    max_abs_x: int,
    exclude_rows: set[int],
) -> List[int]:
    X_test = np.load(OUTPUTS / "processed" / "X_test.npy", mmap_mode="r")
    y_test = np.load(OUTPUTS / "processed" / "y_test.npy", mmap_mode="r").reshape(-1).astype(np.int8)

    normal_rows: List[int] = []
    attack_rows: List[int] = []
    exclude = np.asarray(sorted(exclude_rows), dtype=np.int64)

    for start, end in _chunks(int(X_test.shape[0]), chunk_size):
        rows = np.arange(start, end, dtype=np.int64)
        Xc = np.asarray(X_test[start:end], dtype=np.float64)
        x_int = np.rint(Xc * int(sx)).astype(np.int64)
        valid_x = np.all((x_int >= -int(max_abs_x)) & (x_int <= int(max_abs_x)), axis=1)
        scores = x_int @ w_int.astype(np.int64) + int(b_int)
        valid_score = (scores >= -B_SCORE) & (scores < B_SCORE)
        valid = valid_x & valid_score
        if exclude.size:
            valid &= ~np.isin(rows, exclude)
        y = np.asarray(y_test[start:end], dtype=np.int8)
        normal_rows.extend(int(v) for v in rows[valid & (y == 0)].tolist())
        attack_rows.extend(int(v) for v in rows[valid & (y == 1)].tolist())

    n_normal = n_samples // 2
    n_attack = n_samples - n_normal
    if len(normal_rows) < n_normal or len(attack_rows) < n_attack:
        raise RuntimeError(
            f"Not enough valid rows for balanced batch: normal {len(normal_rows)}/{n_normal}, "
            f"attack {len(attack_rows)}/{n_attack}"
        )

    rng = np.random.default_rng(int(seed))
    selected = np.concatenate(
        [
            rng.choice(np.asarray(normal_rows, dtype=np.int64), size=n_normal, replace=False),
            rng.choice(np.asarray(attack_rows, dtype=np.int64), size=n_attack, replace=False),
        ]
    )
    rng.shuffle(selected)
    return [int(v) for v in selected.tolist()]


def _compute_phi(x_int: np.ndarray, w_int: np.ndarray, x_ref_int: np.ndarray, group_ids: np.ndarray, n_groups: int) -> List[int]:
    phi = [0] * n_groups
    contrib = (x_int.astype(np.int64) - x_ref_int.astype(np.int64)) * w_int.astype(np.int64)
    for idx, value in enumerate(contrib):
        phi[int(group_ids[idx]) - 1] += int(value)
    return phi


def _rank_groups(phi: Sequence[int]) -> tuple[List[int], List[int]]:
    ranked = sorted([(idx + 1, abs(int(value))) for idx, value in enumerate(phi)], key=lambda item: (-item[1], item[0]))
    return [gid for gid, _ in ranked[:3]], [gid for gid, _ in ranked[3:5]]


def _make_case(
    *,
    batch_id: int,
    row: int,
    X_test,
    y_test,
    test_idx,
    model: Dict,
    bounds: Dict,
    reference: Dict,
    group_map: Dict,
) -> BatchCase:
    sx = int(model["Sx"])
    max_abs_x = int(bounds["max_abs_x_int"])
    max_abs_w = int(bounds["max_abs_w_int"])
    w_int = np.asarray(model["w_int"], dtype=np.int64)
    b_int = int(model["b_int"])
    x_ref_int = np.asarray(reference["x_ref_int"], dtype=np.int64)
    group_ids = np.asarray(group_map["feature_index_to_group_id"], dtype=np.int16)
    group_names = list(group_map["groups"])
    n_groups = int(group_map["n_groups"])

    x_float = np.asarray(X_test[int(row)], dtype=np.float64)
    x_int = np.rint(x_float * sx).astype(np.int64)
    if np.any(x_int < -max_abs_x) or np.any(x_int > max_abs_x):
        raise ValueError(f"Batch row {row} exceeds x_int bounds")

    score = int(np.dot(x_int, w_int) + b_int)
    if score < -B_SCORE or score >= B_SCORE:
        raise ValueError(f"Batch row {row} score {score} exceeds circuit score bounds")

    phi = _compute_phi(x_int, w_int, x_ref_int, group_ids, n_groups)
    if any(abs(int(value)) >= B_PHI for value in phi):
        raise ValueError(f"Batch row {row} exceeds Stage 3.4 SHAP bounds")

    top3_ids, other2_ids = _rank_groups(phi)
    y_hat = 1 if score >= 0 else 0
    return BatchCase(
        batch_id=int(batch_id),
        row_in_test_split=int(row),
        dataset_index=int(test_idx[int(row)]),
        y_true=int(y_test[int(row)]),
        y_hat=int(y_hat),
        top3_ids=[int(v) for v in top3_ids],
        other2_ids=[int(v) for v in other2_ids],
        top3_groups=[group_names[gid - 1] for gid in top3_ids],
        x_shifted=[int(v + max_abs_x) for v in x_int.tolist()],
        w_shifted=[int(v + max_abs_w) for v in w_int.tolist()],
        b_shifted=int(b_int + B_SCORE),
    )


def _summarize(values: Sequence[int]) -> Dict[str, float | int | None]:
    vals = [int(v) for v in values]
    if not vals:
        return {"count": 0, "min": None, "max": None, "mean": None, "median": None}
    return {
        "count": len(vals),
        "min": min(vals),
        "max": max(vals),
        "mean": round(float(statistics.mean(vals)), 3),
        "median": round(float(statistics.median(vals)), 3),
    }


def _status(step: Dict[str, object]) -> str:
    return "PASS" if int(step.get("returncode", 1)) == 0 else "FAIL"


def _run_case(case: BatchCase, *, prove: bool, keep_artifacts: bool) -> Dict[str, object]:
    input_dir = BATCH_DIR / "inputs"
    witness_dir = BATCH_DIR / "witnesses"
    proof_dir = BATCH_DIR / "proofs"
    for path in [input_dir, witness_dir, proof_dir]:
        path.mkdir(parents=True, exist_ok=True)

    stem = f"batch_sample_{case.batch_id:03d}"
    input_path = input_dir / f"{stem}_input.json"
    witness_path = witness_dir / f"{stem}.wtns"
    proof_path = proof_dir / f"{stem}_proof.json"
    public_path = proof_dir / f"{stem}_public.json"
    expected_public = case.w_shifted + [case.b_shifted, case.y_hat] + case.top3_ids

    _write_json(
        input_path,
        {
            "x_shifted": case.x_shifted,
            "w_shifted": case.w_shifted,
            "b_shifted": case.b_shifted,
            "y_hat": case.y_hat,
            "top3_ids": case.top3_ids,
            "other2_ids": case.other2_ids,
        },
    )

    witness = _timed(["node", str(WITNESS_GEN), str(WASM), str(input_path), str(witness_path)], timeout=120)
    result: Dict[str, object] = {
        "batch_id": case.batch_id,
        "row_in_test_split": case.row_in_test_split,
        "dataset_index": case.dataset_index,
        "y_true": case.y_true,
        "y_hat": case.y_hat,
        "top3_ids": case.top3_ids,
        "top3_groups": case.top3_groups,
        "witness_status": _status(witness),
        "witness_ms": witness["duration_ms"],
        "prove_status": "SKIP",
        "verify_status": "SKIP",
        "public_signal_count": None,
        "public_outputs_match": None,
        "proof_bytes": None,
        "public_bytes": None,
    }
    if _status(witness) != "PASS":
        result["error_tail"] = witness.get("stderr_tail") or witness.get("stdout_tail")
        return result

    if prove:
        prove_step = _timed(["node", str(SNARKJS), "groth16", "prove", str(ZKEY_FINAL), str(witness_path), str(proof_path), str(public_path)], timeout=600)
        result["prove_status"] = _status(prove_step)
        result["prove_ms"] = prove_step["duration_ms"]
        if _status(prove_step) != "PASS":
            result["error_tail"] = prove_step.get("stderr_tail") or prove_step.get("stdout_tail")
            return result

        verify_step = _timed(["node", str(SNARKJS), "groth16", "verify", str(VKEY), str(public_path), str(proof_path)], timeout=120)
        result["verify_status"] = _status(verify_step)
        result["verify_ms"] = verify_step["duration_ms"]
        if public_path.exists():
            public = [int(v) for v in _read_json(public_path)]
            result["public_signal_count"] = len(public)
            result["public_outputs_match"] = public == expected_public
            result["public_bytes"] = int(public_path.stat().st_size)
        if proof_path.exists():
            result["proof_bytes"] = int(proof_path.stat().st_size)
        if _status(verify_step) != "PASS":
            result["error_tail"] = verify_step.get("stderr_tail") or verify_step.get("stdout_tail")
            return result

    if not keep_artifacts:
        for path in [input_path, witness_path, proof_path, public_path]:
            if path.exists():
                path.unlink()
    return result


def _classification_counts(results: Sequence[Dict[str, object]]) -> Dict[str, int]:
    out = {"tn": 0, "fp": 0, "fn": 0, "tp": 0}
    for row in results:
        y_true = int(row["y_true"])
        y_hat = int(row["y_hat"])
        if y_true == 0 and y_hat == 0:
            out["tn"] += 1
        elif y_true == 0 and y_hat == 1:
            out["fp"] += 1
        elif y_true == 1 and y_hat == 0:
            out["fn"] += 1
        elif y_true == 1 and y_hat == 1:
            out["tp"] += 1
    return out


def _write_report(payload: Dict[str, object]) -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    json_path = REPORTS / "STAGE34_BATCH_SMOKE_REPORT.json"
    md_path = REPORTS / "STAGE34_BATCH_SMOKE_REPORT.md"
    _write_json(json_path, payload)

    summary = payload["summary"]
    results = payload["sample_results"]
    lines: List[str] = []
    lines.append("# Stage 3.4 Batch Smoke-Test Report\n\n")
    lines.append(f"Generated: {payload['created_utc']} (UTC)\n\n")
    lines.append("## Purpose\n\n")
    lines.append(
        "This supplemental smoke test runs the current Stage 3.4 witness/prove/verify path on a deterministic "
        "label-balanced batch from the processed test split. It complements the eight curated Stage 3.4 vectors; "
        "it does not replace the authoritative proof report or the full ML evaluation.\n\n"
    )
    lines.append("## Configuration\n\n")
    lines.append("| Item | Value |\n|---|---:|\n")
    for key in [
        "requested_samples",
        "proved_samples",
        "seed",
        "curated_vector_files",
        "excluded_curated_rows_with_metadata",
        "candidate_normals",
        "candidate_attacks",
    ]:
        lines.append(f"| {key} | {payload[key]} |\n")
    lines.append(f"| temporary_artifacts_retained | {payload['temporary_artifacts_retained']} |\n")
    lines.append("\n## Summary\n\n")
    lines.append("| Metric | Value |\n|---|---:|\n")
    for key, value in summary.items():
        lines.append(f"| {key} | {value} |\n")
    lines.append("\n## Classification Counts In Batch\n\n")
    lines.append("| TN | FP | FN | TP |\n|---:|---:|---:|---:|\n")
    cls = payload["classification_counts"]
    lines.append(f"| {cls['tn']} | {cls['fp']} | {cls['fn']} | {cls['tp']} |\n")
    lines.append("\n## Timing Summary\n\n")
    lines.append("| Step | Count | Min ms | Median ms | Mean ms | Max ms |\n|---|---:|---:|---:|---:|---:|\n")
    for key, stats in payload["timing_summary"].items():
        lines.append(
            f"| {key} | {stats['count']} | {stats['min']} | {stats['median']} | {stats['mean']} | {stats['max']} |\n"
        )
    lines.append("\n## Sample Results\n\n")
    lines.append("| Batch ID | Test row | Dataset index | y_true | y_hat | Public top-3 groups | Witness | Prove | Verify | Public signals | Public match |\n")
    lines.append("|---:|---:|---:|---:|---:|---|---|---|---|---:|---|\n")
    for row in results:
        lines.append(
            f"| {row['batch_id']} | {row['row_in_test_split']} | {row['dataset_index']} | {row['y_true']} | {row['y_hat']} | "
            f"{', '.join(row['top3_groups'])} | {row['witness_status']} | {row['prove_status']} | {row['verify_status']} | "
            f"{row.get('public_signal_count') or ''} | {row.get('public_outputs_match')} |\n"
        )
    lines.append("\n## Limitations\n\n")
    lines.append("- The batch is deterministic and label-balanced, not a statistical reliability estimate for the full test split.\n")
    lines.append("- Proof success means the circuit relation was satisfied for the selected witnesses; it does not imply ground-truth correctness.\n")
    lines.append("- The report intentionally omits private feature vectors, full witness files, proof JSON, and public-signal JSON.\n")
    lines.append("- The authoritative Stage 3.4 proof-cost numbers remain in `stage3_zk/reports/STAGE34_PROOF_REPORT.md`.\n")
    md_path.write_text("".join(lines), encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=int, default=30, help="Number of deterministic batch rows to select.")
    parser.add_argument("--prove", type=int, default=30, help="Number of selected rows to prove and verify.")
    parser.add_argument("--seed", type=int, default=34030, help="Deterministic RNG seed for row selection.")
    parser.add_argument("--chunk-size", type=int, default=50000, help="Rows per selection chunk.")
    parser.add_argument("--keep-artifacts", action="store_true", help="Keep temporary input/witness/proof/public files.")
    args = parser.parse_args(argv)

    if args.samples <= 0:
        raise ValueError("--samples must be positive")
    if args.prove < 0 or args.prove > args.samples:
        raise ValueError("--prove must be between 0 and --samples")

    _require([WASM, WITNESS_GEN, SNARKJS, ZKEY_FINAL, VKEY])
    model = _read_json(ARTIFACTS / "model_public.json")
    bounds = _read_json(ARTIFACTS / "bounds.json")
    reference = _read_json(ARTIFACTS / "exact_shap_reference.json")
    group_map = _read_json(ARTIFACTS / "group_map.json")

    w_int = np.asarray(model["w_int"], dtype=np.int64)
    curated_rows = _load_curated_rows()
    rows = _select_rows(
        n_samples=int(args.samples),
        seed=int(args.seed),
        chunk_size=int(args.chunk_size),
        sx=int(model["Sx"]),
        w_int=w_int,
        b_int=int(model["b_int"]),
        max_abs_x=int(bounds["max_abs_x_int"]),
        exclude_rows=curated_rows,
    )

    X_test = np.load(OUTPUTS / "processed" / "X_test.npy", mmap_mode="r")
    y_test = np.load(OUTPUTS / "processed" / "y_test.npy", mmap_mode="r").reshape(-1).astype(np.int8)
    test_idx = np.load(OUTPUTS / "splits" / "test_idx.npy", mmap_mode="r")

    results: List[Dict[str, object]] = []
    for idx, row in enumerate(rows, 1):
        case = _make_case(
            batch_id=idx,
            row=row,
            X_test=X_test,
            y_test=y_test,
            test_idx=test_idx,
            model=model,
            bounds=bounds,
            reference=reference,
            group_map=group_map,
        )
        print(f"Batch {idx:03d}/{len(rows)} row={row} y_true={case.y_true} y_hat={case.y_hat}")
        result = _run_case(case, prove=(idx <= int(args.prove)), keep_artifacts=bool(args.keep_artifacts))
        results.append(result)
        ok = result["witness_status"] == "PASS" and (
            result["prove_status"] == "SKIP"
            or (result["prove_status"] == "PASS" and result["verify_status"] == "PASS" and result["public_outputs_match"] is True)
        )
        if not ok:
            print(json.dumps(result, indent=2))
            return 1

    witness_ms = [int(r["witness_ms"]) for r in results if r.get("witness_status") == "PASS"]
    prove_ms = [int(r["prove_ms"]) for r in results if r.get("prove_status") == "PASS"]
    verify_ms = [int(r["verify_ms"]) for r in results if r.get("verify_status") == "PASS"]
    proved = [r for r in results if r.get("prove_status") == "PASS" and r.get("verify_status") == "PASS"]

    y_values = np.load(OUTPUTS / "processed" / "y_test.npy", mmap_mode="r").reshape(-1).astype(np.int8)
    sx = int(model["Sx"])
    max_abs_x = int(bounds["max_abs_x_int"])
    normal_candidates = 0
    attack_candidates = 0
    for start, end in _chunks(int(X_test.shape[0]), int(args.chunk_size)):
        Xc = np.asarray(X_test[start:end], dtype=np.float64)
        x_int = np.rint(Xc * sx).astype(np.int64)
        valid_x = np.all((x_int >= -max_abs_x) & (x_int <= max_abs_x), axis=1)
        scores = x_int @ w_int.astype(np.int64) + int(model["b_int"])
        valid = valid_x & (scores >= -B_SCORE) & (scores < B_SCORE)
        y = np.asarray(y_values[start:end], dtype=np.int8)
        normal_candidates += int(np.sum(valid & (y == 0)))
        attack_candidates += int(np.sum(valid & (y == 1)))

    payload: Dict[str, object] = {
        "created_utc": _utc_now_iso(),
        "requested_samples": int(args.samples),
        "proved_samples": int(args.prove),
        "seed": int(args.seed),
        "curated_vector_files": _curated_vector_file_count(),
        "excluded_curated_rows_with_metadata": len(curated_rows),
        "candidate_normals": normal_candidates,
        "candidate_attacks": attack_candidates,
        "temporary_artifacts_retained": bool(args.keep_artifacts),
        "summary": {
            "selected_samples": len(results),
            "witness_pass": sum(1 for r in results if r.get("witness_status") == "PASS"),
            "prove_pass": sum(1 for r in results if r.get("prove_status") == "PASS"),
            "verify_pass": sum(1 for r in results if r.get("verify_status") == "PASS"),
            "public_output_match_pass": sum(1 for r in proved if r.get("public_outputs_match") is True),
            "failures": sum(1 for r in results if r.get("witness_status") == "FAIL" or r.get("prove_status") == "FAIL" or r.get("verify_status") == "FAIL"),
        },
        "classification_counts": _classification_counts(results),
        "timing_summary": {
            "witness": _summarize(witness_ms),
            "prove": _summarize(prove_ms),
            "verify": _summarize(verify_ms),
        },
        "sample_results": results,
    }
    _write_report(payload)
    print("Wrote:")
    print("  stage3_zk/reports/STAGE34_BATCH_SMOKE_REPORT.json")
    print("  stage3_zk/reports/STAGE34_BATCH_SMOKE_REPORT.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
