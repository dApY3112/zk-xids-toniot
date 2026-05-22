#!/usr/bin/env python
"""ZK scaling benchmark: repeated prove/verify timings (p50/p95).

This script repeatedly invokes `stage3_zk/scripts/run_stage3_tests.py` with
`--prove --verify --report` (JSON-only), then aggregates timings from the harness
report (`duration_ms` per step).

Primary thesis outputs:
- stage3_zk/reports/zk_scaling_benchmark.json
- stage3_zk/reports/zk_scaling_benchmark.md

Notes:
- We default to stage 33 (top3_explanation) because it is the most complete Stage 3.3.
- We benchmark *runtime* (witness/prove/verify) and also record proof/public sizes.
- We avoid circuit rebuild/clean by default; pass --clean-first if you want.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from glob import glob
from typing import Dict, List, Optional, Sequence, Tuple


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
STAGE3_ZK_DIR = os.path.join(REPO_ROOT, "stage3_zk")
HARNESS = os.path.join(STAGE3_ZK_DIR, "scripts", "run_stage3_tests.py")


@dataclass
class RunSample:
    run_index: int
    report_json: str
    wall_ms: int
    prepare_ms: Optional[int]
    witness_ms: Optional[int]
    prove_ms: Optional[int]
    verify_ms: Optional[int]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _read_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _percentile(values: Sequence[float], q: float) -> float:
    if not values:
        return float("nan")
    if q <= 0:
        return float(min(values))
    if q >= 1:
        return float(max(values))
    xs = sorted(float(v) for v in values)
    # Linear interpolation between closest ranks
    pos = (len(xs) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(xs) - 1)
    frac = pos - lo
    return xs[lo] * (1.0 - frac) + xs[hi] * frac


def _summ(values: Sequence[Optional[int]]) -> Dict[str, float]:
    xs = [float(v) for v in values if v is not None]
    if not xs:
        return {"n": 0.0, "mean": float("nan"), "std": float("nan"), "p50": float("nan"), "p95": float("nan"), "min": float("nan"), "max": float("nan")}
    mean = statistics.fmean(xs)
    std = statistics.pstdev(xs) if len(xs) > 1 else 0.0
    return {
        "n": float(len(xs)),
        "mean": float(mean),
        "std": float(std),
        "p50": float(_percentile(xs, 0.50)),
        "p95": float(_percentile(xs, 0.95)),
        "min": float(min(xs)),
        "max": float(max(xs)),
    }


def _find_latest_report(prefix: str, report_dir: str) -> str:
    # Harness writes: {report_prefix}_{safe_ts}.json
    pattern = os.path.join(report_dir, f"{prefix}_*.json")
    candidates = glob(pattern)
    if not candidates:
        raise FileNotFoundError(f"No report JSON found for prefix '{prefix}' in {report_dir}")
    candidates.sort(key=lambda p: os.path.getmtime(p))
    return candidates[-1]


def _extract_step_duration(report: dict, step_name: str) -> Optional[int]:
    steps = report.get("results") or report.get("steps")
    if isinstance(steps, list):
        for s in steps:
            if s.get("name") == step_name:
                d = s.get("duration_ms")
                return int(d) if d is not None else None
    return None


def _run_harness(
    *,
    stage: str,
    sample: int,
    report_dir: str,
    report_prefix: str,
    clean: bool,
) -> Tuple[int, str, int]:
    if not os.path.exists(HARNESS):
        raise FileNotFoundError(f"Missing harness: {HARNESS}")

    cmd = [
        sys.executable,
        HARNESS,
        "--stage",
        str(stage),
        "--samples",
        str(sample),
        "--prove",
        "--verify",
        "--report",
        "--report-dir",
        str(report_dir),
        "--report-prefix",
        str(report_prefix),
        "--report-formats",
        "json",
    ]
    if clean:
        cmd.append("--clean")

    t0 = time.perf_counter()
    proc = subprocess.run(cmd, cwd=STAGE3_ZK_DIR)
    wall_ms = int((time.perf_counter() - t0) * 1000)
    report_json = _find_latest_report(report_prefix, report_dir)
    return int(proc.returncode), report_json, wall_ms


def _write_markdown(out_md: str, payload: dict) -> None:
    lines: List[str] = []
    lines.append("# ZK Scaling Benchmark (Repeated Prove/Verify)\n")
    lines.append(f"Generated: {payload['created_utc']} (UTC)\n")
    lines.append("\n## Configuration\n")
    cfg = payload["config"]
    lines.append(f"- Stage: `{cfg['stage']}`\n")
    lines.append(f"- Sample: `{cfg['sample']}`\n")
    lines.append(f"- Runs (total): `{cfg['runs_total']}`\n")
    lines.append(f"- Warmup (excluded): `{cfg['warmup']}`\n")
    lines.append(f"- Runs analyzed: `{cfg['runs_analyzed']}`\n")

    env = payload.get("environment", {})
    if env:
        lines.append("\n## Environment (from harness report)\n")
        py = env.get("python", {})
        node = env.get("node", {})
        snarkjs = env.get("snarkjs", {})
        lines.append(f"- Python: {py.get('version', 'unknown')} ({py.get('executable', 'unknown')})\n")
        lines.append(f"- Node: {node.get('version', 'unknown')} (npm {node.get('npm_version', 'unknown')})\n")
        lines.append(f"- snarkjs: {snarkjs.get('version', 'unknown')}\n")

    stats = payload["timing_summary_ms"]
    lines.append("\n## Timing summary (ms)\n")
    lines.append("Each row is summarized across runs: min/mean/p50/p95/max (std shown separately).\n\n")
    lines.append("| Step | n | min | mean | p50 | p95 | max | std |\n")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|\n")
    for key, label in [
        ("wall_ms", "wall_total"),
        ("prepare_ms", "prepare_input"),
        ("witness_ms", "witness_smoke"),
        ("prove_ms", "prove"),
        ("verify_ms", "verify"),
    ]:
        s = stats.get(key, {})
        lines.append(
            f"| {label} | {int(s.get('n', 0))} | {s.get('min', float('nan')):.0f} | {s.get('mean', float('nan')):.0f} | {s.get('p50', float('nan')):.0f} | {s.get('p95', float('nan')):.0f} | {s.get('max', float('nan')):.0f} | {s.get('std', float('nan')):.0f} |\n"
        )

    comm = payload.get("communication", {})
    if comm:
        lines.append("\n## Communication (bytes)\n")
        lines.append("From the circuit stats (sizes are stable across runs).\n\n")
        lines.append("| Artifact | Size (bytes) |\n")
        lines.append("|---|---:|\n")
        for k in ["r1cs_bytes", "wasm_bytes", "zkey_bytes", "vkey_bytes", "proof_bytes", "public_bytes", "n_public_signals", "constraints"]:
            if k in comm:
                lines.append(f"| {k} | {comm[k]} |\n")

    _ensure_dir(os.path.dirname(out_md))
    with open(out_md, "w", encoding="utf-8") as f:
        f.writelines(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="33", choices=["31", "32", "33"], help="Which Stage 3 circuit to benchmark.")
    ap.add_argument("--sample", type=int, default=1, choices=[1, 2, 3], help="Which test sample to use.")
    ap.add_argument("--runs", type=int, default=30, help="Total number of runs (including warmup).")
    ap.add_argument("--warmup", type=int, default=2, help="Number of initial runs to exclude from stats.")
    ap.add_argument("--clean-first", action="store_true", help="Run a clean on the first iteration (slower, but removes stale outputs).")
    ap.add_argument(
        "--bench-dir",
        default=os.path.join(STAGE3_ZK_DIR, "reports", "bench"),
        help="Directory to store per-run harness JSON reports.",
    )
    ap.add_argument(
        "--out-json",
        default=os.path.join(STAGE3_ZK_DIR, "reports", "zk_scaling_benchmark.json"),
        help="Output JSON summary path.",
    )
    ap.add_argument(
        "--out-md",
        default=os.path.join(STAGE3_ZK_DIR, "reports", "zk_scaling_benchmark.md"),
        help="Output Markdown summary path.",
    )
    args = ap.parse_args()

    runs_total = int(args.runs)
    warmup = int(args.warmup)
    if runs_total <= 0:
        raise SystemExit("--runs must be > 0")
    if warmup < 0 or warmup >= runs_total:
        raise SystemExit("--warmup must be >= 0 and < runs")

    _ensure_dir(args.bench_dir)

    report_prefix = f"zk_bench_stage{args.stage}_sample{args.sample}"

    samples: List[RunSample] = []
    environment: dict = {}
    communication: dict = {}

    for i in range(runs_total):
        clean = bool(args.clean_first and i == 0)
        rc, report_json, wall_ms = _run_harness(
            stage=str(args.stage),
            sample=int(args.sample),
            report_dir=str(args.bench_dir),
            report_prefix=report_prefix,
            clean=clean,
        )
        if rc != 0:
            print(f"❌ Harness failed on iteration {i+1}/{runs_total}. Report: {report_json}")
            return 1

        report = _read_json(report_json)
        if not environment:
            environment = report.get("environment", {})

        # Communication / complexity: stable, take from first report
        if not communication:
            cs = (report.get("circuit_stats", {}) or {}).get(str(args.stage), {})
            r1cs_info = (cs.get("r1cs_info", {}) or {})
            proofs = cs.get("proofs", [])
            proof_row = None
            for row in proofs:
                if int(row.get("sample", -1)) == int(args.sample):
                    proof_row = row
                    break
            communication = {
                "constraints": r1cs_info.get("constraints"),
                "n_public_signals": (proof_row or {}).get("public", {}).get("n_public_signals"),
                "r1cs_bytes": (cs.get("r1cs", {}) or {}).get("size_bytes"),
                "wasm_bytes": (cs.get("wasm", {}) or {}).get("size_bytes"),
                "zkey_bytes": (cs.get("zkey_final", {}) or {}).get("size_bytes"),
                "vkey_bytes": (cs.get("verification_key", {}) or {}).get("size_bytes"),
                "proof_bytes": (proof_row or {}).get("proof", {}).get("size_bytes"),
                "public_bytes": (proof_row or {}).get("public", {}).get("size_bytes"),
            }

        step_prepare = f"prepare_input_stage{args.stage}_sample{args.sample}"
        step_witness = f"witness_smoke_stage{args.stage}_sample{args.sample}"
        step_prove = f"prove_stage{args.stage}_sample{args.sample}"
        step_verify = f"verify_stage{args.stage}_sample{args.sample}"

        samples.append(
            RunSample(
                run_index=i,
                report_json=os.path.relpath(report_json, REPO_ROOT).replace("\\", "/"),
                wall_ms=int(wall_ms),
                prepare_ms=_extract_step_duration(report, step_prepare),
                witness_ms=_extract_step_duration(report, step_witness),
                prove_ms=_extract_step_duration(report, step_prove),
                verify_ms=_extract_step_duration(report, step_verify),
            )
        )

        # Light progress line (helps long runs)
        if (i + 1) % 5 == 0 or (i + 1) == runs_total:
            print(f"… benchmark progress: {i+1}/{runs_total}")

    analyzed = samples[warmup:]
    payload = {
        "created_utc": _utc_now_iso(),
        "config": {
            "stage": str(args.stage),
            "sample": int(args.sample),
            "runs_total": int(runs_total),
            "warmup": int(warmup),
            "runs_analyzed": int(len(analyzed)),
            "bench_dir": os.path.relpath(str(args.bench_dir), REPO_ROOT).replace("\\", "/"),
        },
        "environment": environment,
        "communication": communication,
        "runs": [
            {
                "run_index": r.run_index,
                "report_json": r.report_json,
                "wall_ms": r.wall_ms,
                "prepare_ms": r.prepare_ms,
                "witness_ms": r.witness_ms,
                "prove_ms": r.prove_ms,
                "verify_ms": r.verify_ms,
            }
            for r in samples
        ],
        "timing_summary_ms": {
            "wall_ms": _summ([r.wall_ms for r in analyzed]),
            "prepare_ms": _summ([r.prepare_ms for r in analyzed]),
            "witness_ms": _summ([r.witness_ms for r in analyzed]),
            "prove_ms": _summ([r.prove_ms for r in analyzed]),
            "verify_ms": _summ([r.verify_ms for r in analyzed]),
        },
    }

    _ensure_dir(os.path.dirname(str(args.out_json)))
    with open(str(args.out_json), "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    _write_markdown(str(args.out_md), payload)

    print(f"✅ Wrote: {args.out_json}")
    print(f"✅ Wrote: {args.out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
