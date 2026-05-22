#!/usr/bin/env python
"""Repeated Stage 3.4 witness/prove/verify benchmark.

This is a lightweight thesis evidence script. It reuses the existing Stage 3.4
artifacts and writes a separate benchmark report without modifying circuits,
model artifacts, or the canonical Stage 3.4 proof report.
"""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
STAGE3 = REPO_ROOT / "stage3_zk"
BUILD = STAGE3 / "circuits" / "exact_shap_top3" / "build"
PROOF_DIR = STAGE3 / "outputs" / "proofs" / "stage34_bench"
REPORT_JSON = STAGE3 / "reports" / "zk_stage34_scaling_benchmark.json"
REPORT_MD = STAGE3 / "reports" / "zk_stage34_scaling_benchmark.md"
SNARKJS = STAGE3 / "node_modules" / "snarkjs" / "cli.js"

WASM = BUILD / "exact_shap_top3_js" / "exact_shap_top3.wasm"
WITNESS_GEN = BUILD / "exact_shap_top3_js" / "generate_witness.js"
ZKEY = BUILD / "exact_shap_top3_final.zkey"
VKEY = BUILD / "verification_key.json"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _require(paths: Sequence[Path]) -> None:
    missing = [str(p) for p in paths if not p.exists()]
    if missing:
        raise FileNotFoundError("Missing required artifacts:\n" + "\n".join(missing))


def _timed(cmd: Sequence[str], timeout: int) -> Dict[str, object]:
    start = time.perf_counter()
    proc = subprocess.run(cmd, cwd=str(STAGE3), capture_output=True, text=True, timeout=timeout)
    elapsed_ms = int(round((time.perf_counter() - start) * 1000))
    return {
        "cmd": list(cmd),
        "returncode": proc.returncode,
        "duration_ms": elapsed_ms,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def _p95(values: Sequence[int]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = int(0.95 * (len(ordered) - 1) + 0.999999)
    return float(ordered[min(idx, len(ordered) - 1)])


def _summary(values: Sequence[int]) -> Dict[str, float]:
    return {
        "count": len(values),
        "mean_ms": float(statistics.mean(values)) if values else 0.0,
        "median_ms": float(statistics.median(values)) if values else 0.0,
        "p95_ms": _p95(values),
        "min_ms": float(min(values)) if values else 0.0,
        "max_ms": float(max(values)) if values else 0.0,
    }


def _size(path: Path) -> int:
    return int(path.stat().st_size) if path.exists() else 0


def run_once(sample: int, run_id: int, *, timeout: int) -> Dict[str, object]:
    input_path = BUILD / f"input_sample_{sample}.json"
    witness_path = PROOF_DIR / f"witness_stage34_sample{sample}_run{run_id}.wtns"
    proof_path = PROOF_DIR / f"proof_stage34_sample{sample}_run{run_id}.json"
    public_path = PROOF_DIR / f"public_stage34_sample{sample}_run{run_id}.json"
    _require([input_path])

    witness = _timed(["node", str(WITNESS_GEN), str(WASM), str(input_path), str(witness_path)], timeout)
    witness["step"] = "witness"
    if witness["returncode"] != 0:
        return {"run": run_id, "status": "FAIL", "steps": [witness]}

    prove = _timed(["node", str(SNARKJS), "groth16", "prove", str(ZKEY), str(witness_path), str(proof_path), str(public_path)], timeout)
    prove["step"] = "prove"
    if prove["returncode"] != 0:
        return {"run": run_id, "status": "FAIL", "steps": [witness, prove]}

    verify = _timed(["node", str(SNARKJS), "groth16", "verify", str(VKEY), str(public_path), str(proof_path)], timeout)
    verify["step"] = "verify"
    status = "PASS" if verify["returncode"] == 0 else "FAIL"
    public_signals = []
    if public_path.exists():
        public_signals = json.loads(public_path.read_text(encoding="utf-8"))
    return {
        "run": run_id,
        "status": status,
        "steps": [witness, prove, verify],
        "artifacts": {
            "proof_bytes": _size(proof_path),
            "public_bytes": _size(public_path),
            "public_signal_count": len(public_signals),
        },
    }


def write_reports(payload: Dict[str, object]) -> None:
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    summary = payload["summary"]
    lines: List[str] = []
    lines.append("# Stage 3.4 Repeated Prove/Verify Benchmark\n\n")
    lines.append(f"Generated: {payload['created_utc']} (UTC)\n\n")
    lines.append(
        "This report benchmarks the implemented Stage 3.4 Exact SHAP circuit on repeated runs for one fixed test sample. "
        "It is timing evidence only; it does not change the circuit, model, proof relation, or benchmark numbers in other reports.\n\n"
    )
    lines.append(f"- Sample: `{payload['sample']}`\n")
    lines.append(f"- Warmup runs: `{payload['warmup']}`\n")
    lines.append(f"- Analyzed runs: `{payload['runs']}`\n")
    lines.append("- Proof system: Circom + Groth16 via repository-local snarkjs CLI\n\n")
    lines.append("| Step | Mean ms | Median ms | p95 ms | Min ms | Max ms |\n")
    lines.append("|---|---:|---:|---:|---:|---:|\n")
    for step in ["witness", "prove", "verify"]:
        row = summary[step]
        lines.append(
            f"| {step} | {row['mean_ms']:.0f} | {row['median_ms']:.0f} | {row['p95_ms']:.0f} | "
            f"{row['min_ms']:.0f} | {row['max_ms']:.0f} |\n"
        )
    lines.append("\n## Artifact Stability\n\n")
    lines.append(f"- Proof bytes range: `{summary['proof_bytes_min']}-{summary['proof_bytes_max']}`\n")
    lines.append(f"- Public bytes range: `{summary['public_bytes_min']}-{summary['public_bytes_max']}`\n")
    lines.append(f"- Public signal count: `{summary['public_signal_count']}`\n\n")
    lines.append("## Thesis Interpretation\n\n")
    lines.append(
        "Stage 3.4 adds verified semantic-group Exact SHAP top-3 authenticity while keeping proof sizes small and verification "
        "substantially cheaper than proving under this CLI harness. These measurements should be reported as local prototype "
        "evidence, not as a hardware-independent performance guarantee.\n"
    )
    REPORT_MD.write_text("".join(lines), encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=1)
    ap.add_argument("--runs", type=int, default=30)
    ap.add_argument("--warmup", type=int, default=2)
    ap.add_argument("--timeout", type=int, default=300)
    args = ap.parse_args(argv)

    _require([SNARKJS, WASM, WITNESS_GEN, ZKEY, VKEY])
    PROOF_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Stage 3.4 repeated benchmark: sample={args.sample}, warmup={args.warmup}, runs={args.runs}")

    for i in range(args.warmup):
        result = run_once(args.sample, -(i + 1), timeout=args.timeout)
        if result["status"] != "PASS":
            print(json.dumps(result, indent=2))
            return 1
        print(f"warmup {i + 1}/{args.warmup}: PASS")

    results = []
    for i in range(1, args.runs + 1):
        result = run_once(args.sample, i, timeout=args.timeout)
        results.append(result)
        print(f"run {i}/{args.runs}: {result['status']}")
        if result["status"] != "PASS":
            print(json.dumps(result, indent=2))
            return 1

    durations = {step: [] for step in ["witness", "prove", "verify"]}
    proof_sizes: List[int] = []
    public_sizes: List[int] = []
    public_signal_counts: List[int] = []
    for result in results:
        for step in result["steps"]:
            durations[step["step"]].append(int(step["duration_ms"]))
        artifacts = result["artifacts"]
        proof_sizes.append(int(artifacts["proof_bytes"]))
        public_sizes.append(int(artifacts["public_bytes"]))
        public_signal_counts.append(int(artifacts["public_signal_count"]))

    payload: Dict[str, object] = {
        "created_utc": _utc_now_iso(),
        "sample": args.sample,
        "runs": args.runs,
        "warmup": args.warmup,
        "results": results,
        "summary": {
            "witness": _summary(durations["witness"]),
            "prove": _summary(durations["prove"]),
            "verify": _summary(durations["verify"]),
            "proof_bytes_min": min(proof_sizes),
            "proof_bytes_max": max(proof_sizes),
            "public_bytes_min": min(public_sizes),
            "public_bytes_max": max(public_sizes),
            "public_signal_count": sorted(set(public_signal_counts)),
        },
    }
    write_reports(payload)
    print(f"Wrote: {REPORT_JSON}")
    print(f"Wrote: {REPORT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
