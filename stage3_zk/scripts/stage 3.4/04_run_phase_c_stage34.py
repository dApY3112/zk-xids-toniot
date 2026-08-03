#!/usr/bin/env python
"""Stage 3.4 Groth16 setup/prove/verify evidence runner.

This script is Windows-friendly and calls the repository-local snarkjs CLI via
`node node_modules/snarkjs/cli.js`, avoiding npx path/cache issues.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Sequence


SCRIPT_DIR = Path(__file__).resolve().parent
STAGE3_ZK_DIR = SCRIPT_DIR.parents[1]
BUILD_DIR = STAGE3_ZK_DIR / "circuits" / "exact_shap_top3" / "build"
PROOFS_DIR = STAGE3_ZK_DIR / "outputs" / "proofs"
REPORTS_DIR = STAGE3_ZK_DIR / "reports"
SNARKJS = STAGE3_ZK_DIR / "node_modules" / "snarkjs" / "cli.js"
PTAU = STAGE3_ZK_DIR / "circuits" / "semantic_groups" / "powersOfTau28_hez_final_15.ptau"

R1CS = BUILD_DIR / "exact_shap_top3.r1cs"
WASM = BUILD_DIR / "exact_shap_top3_js" / "exact_shap_top3.wasm"
WITNESS_GEN = BUILD_DIR / "exact_shap_top3_js" / "generate_witness.js"
ZKEY_0000 = BUILD_DIR / "exact_shap_top3_0000.zkey"
ZKEY_FINAL = BUILD_DIR / "exact_shap_top3_final.zkey"
VKEY = BUILD_DIR / "verification_key.json"
PREPARE_INPUT = SCRIPT_DIR / "01_prepare_input_stage34.py"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _run(cmd: Sequence[str], *, cwd: Path = STAGE3_ZK_DIR, timeout: int = 300) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=timeout)


def _timed(cmd: Sequence[str], *, cwd: Path = STAGE3_ZK_DIR, timeout: int = 300) -> Dict[str, object]:
    start = time.perf_counter()
    proc = _run(cmd, cwd=cwd, timeout=timeout)
    elapsed_ms = int(round((time.perf_counter() - start) * 1000))
    return {
        "cmd": list(cmd),
        "returncode": int(proc.returncode),
        "duration_ms": elapsed_ms,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def _require(paths: Sequence[Path]) -> None:
    missing = [str(p) for p in paths if not p.exists()]
    if missing:
        raise FileNotFoundError("Missing required Stage 3.4 artifacts:\n" + "\n".join(f"  - {p}" for p in missing))


def _file_size(path: Path) -> int:
    return int(path.stat().st_size) if path.exists() else 0


def _parse_r1cs_info(text: str) -> Dict[str, int | str]:
    clean = re.sub(r"\x1b\[[0-9;]*m", "", text)
    out: Dict[str, int | str] = {}
    patterns = {
        "wires": r"# of Wires:\s*(\d+)",
        "constraints": r"# of Constraints:\s*(\d+)",
        "private_inputs": r"# of Private Inputs:\s*(\d+)",
        "public_inputs": r"# of Public Inputs:\s*(\d+)",
        "labels": r"# of Labels:\s*(\d+)",
        "outputs": r"# of Outputs:\s*(\d+)",
        "curve": r"Curve:\s*([A-Za-z0-9_-]+)",
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, clean)
        if match:
            value = match.group(1)
            out[key] = int(value) if value.isdigit() else value
    return out


def r1cs_info() -> Dict[str, int | str]:
    proc = _run(["node", str(SNARKJS), "r1cs", "info", str(R1CS)], timeout=60)
    if proc.returncode != 0:
        raise RuntimeError(f"r1cs info failed:\n{proc.stderr or proc.stdout}")
    return _parse_r1cs_info(proc.stdout + proc.stderr)


def setup_if_needed(*, force: bool) -> List[Dict[str, object]]:
    steps: List[Dict[str, object]] = []
    if ZKEY_FINAL.exists() and VKEY.exists() and not force:
        steps.append({"step": "setup", "status": "SKIP", "duration_ms": 0, "reason": "existing final zkey and verification key"})
        return steps

    _require([R1CS, PTAU, SNARKJS])

    setup = _timed(
        ["node", str(SNARKJS), "groth16", "setup", str(R1CS), str(PTAU), str(ZKEY_0000)],
        timeout=600,
    )
    setup["step"] = "groth16_setup"
    setup["status"] = "PASS" if setup["returncode"] == 0 else "FAIL"
    steps.append(setup)
    if setup["returncode"] != 0:
        return steps

    entropy = "stage34-exact-shap-" + secrets.token_hex(16)
    contribute = _timed(
        [
            "node",
            str(SNARKJS),
            "zkey",
            "contribute",
            str(ZKEY_0000),
            str(ZKEY_FINAL),
            "--name=Stage3.4-ExactSHAP",
            "-v",
            f"-e={entropy}",
        ],
        timeout=600,
    )
    contribute["step"] = "zkey_contribute"
    contribute["status"] = "PASS" if contribute["returncode"] == 0 else "FAIL"
    steps.append(contribute)
    if contribute["returncode"] != 0:
        return steps

    export = _timed(
        ["node", str(SNARKJS), "zkey", "export", "verificationkey", str(ZKEY_FINAL), str(VKEY)],
        timeout=120,
    )
    export["step"] = "export_verification_key"
    export["status"] = "PASS" if export["returncode"] == 0 else "FAIL"
    steps.append(export)

    return steps


def prove_and_verify(sample_id: int) -> Dict[str, object]:
    _require([WITNESS_GEN, WASM, ZKEY_FINAL, VKEY, SNARKJS])
    input_path = BUILD_DIR / f"input_sample_{sample_id}.json"
    witness_path = BUILD_DIR / f"witness_sample_{sample_id}.wtns"
    proof_path = PROOFS_DIR / f"proof_stage34_sample_{sample_id}.json"
    public_path = PROOFS_DIR / f"public_stage34_sample_{sample_id}.json"
    _require([input_path])
    PROOFS_DIR.mkdir(parents=True, exist_ok=True)

    witness = _timed(
        ["node", str(WITNESS_GEN), str(WASM), str(input_path), str(witness_path)],
        timeout=120,
    )
    witness["step"] = f"witness_sample_{sample_id}"
    witness["status"] = "PASS" if witness["returncode"] == 0 else "FAIL"
    if witness["returncode"] != 0:
        return {"sample": sample_id, "steps": [witness]}

    prove = _timed(
        ["node", str(SNARKJS), "groth16", "prove", str(ZKEY_FINAL), str(witness_path), str(proof_path), str(public_path)],
        timeout=600,
    )
    prove["step"] = f"prove_sample_{sample_id}"
    prove["status"] = "PASS" if prove["returncode"] == 0 else "FAIL"
    if prove["returncode"] != 0:
        return {"sample": sample_id, "steps": [witness, prove]}

    verify = _timed(
        ["node", str(SNARKJS), "groth16", "verify", str(VKEY), str(public_path), str(proof_path)],
        timeout=120,
    )
    verify["step"] = f"verify_sample_{sample_id}"
    verify["status"] = "PASS" if verify["returncode"] == 0 else "FAIL"

    public_signals = []
    if public_path.exists():
        with public_path.open("r", encoding="utf-8") as f:
            public_signals = json.load(f)

    return {
        "sample": sample_id,
        "steps": [witness, prove, verify],
        "artifacts": {
            "witness": str(witness_path.relative_to(STAGE3_ZK_DIR)),
            "witness_bytes": _file_size(witness_path),
            "proof": str(proof_path.relative_to(STAGE3_ZK_DIR)),
            "proof_bytes": _file_size(proof_path),
            "public": str(public_path.relative_to(STAGE3_ZK_DIR)),
            "public_bytes": _file_size(public_path),
            "public_signal_count": len(public_signals),
        },
    }


def prepare_inputs(samples: Sequence[int]) -> List[Dict[str, object]]:
    steps: List[Dict[str, object]] = []
    _require([PREPARE_INPUT])
    for sample_id in samples:
        step = _timed([sys.executable, str(PREPARE_INPUT), str(int(sample_id))], timeout=120)
        step["step"] = f"prepare_input_sample_{sample_id}"
        step["status"] = "PASS" if step["returncode"] == 0 else "FAIL"
        steps.append(step)
    return steps


def write_reports(payload: Dict[str, object]) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out_json = REPORTS_DIR / "STAGE34_PROOF_REPORT.json"
    out_md = REPORTS_DIR / "STAGE34_PROOF_REPORT.md"
    with out_json.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    stats = payload["circuit_stats"]
    sizes = payload["artifact_sizes"]
    lines: List[str] = []
    lines.append("# Stage 3.4 Exact SHAP Proof Report\n\n")
    lines.append(f"Generated: {payload['created_utc']} (UTC)\n\n")
    lines.append("## Claim\n\n")
    lines.append(
        "Stage 3.4 verifies semantic-group Exact SHAP top-3 authenticity for the public Logistic Regression model under private input features. "
        "The circuit uses the closed-form Exact SHAP specialization for a linear score model with a fixed public reference vector hardcoded in the circuit.\n\n"
    )
    lines.append("## Circuit Stats\n\n")
    lines.append("| Metric | Value |\n|---|---:|\n")
    for key in ["constraints", "wires", "public_inputs", "private_inputs", "labels", "outputs"]:
        if key in stats:
            lines.append(f"| {key.replace('_', ' ').title()} | {stats[key]} |\n")
    lines.append("\n## Artifact Sizes\n\n")
    lines.append("| Artifact | Bytes |\n|---|---:|\n")
    for key, value in sizes.items():
        lines.append(f"| {key} | {value} |\n")

    lines.append("\n## Results\n\n")
    lines.append("| Sample | Witness ms | Prove ms | Verify ms | Proof bytes | Public bytes | Public signals | Status |\n")
    lines.append("|---:|---:|---:|---:|---:|---:|---:|---|\n")
    for result in payload["sample_results"]:
        step_map = {step["step"].split("_sample_")[0]: step for step in result["steps"]}
        witness_ms = step_map.get("witness", {}).get("duration_ms", "")
        prove_ms = step_map.get("prove", {}).get("duration_ms", "")
        verify_ms = step_map.get("verify", {}).get("duration_ms", "")
        artifacts = result.get("artifacts", {})
        ok = all(step.get("status") == "PASS" for step in result["steps"])
        lines.append(
            f"| {result['sample']} | {witness_ms} | {prove_ms} | {verify_ms} | "
            f"{artifacts.get('proof_bytes', '')} | {artifacts.get('public_bytes', '')} | "
            f"{artifacts.get('public_signal_count', '')} | {'PASS' if ok else 'FAIL'} |\n"
        )

    lines.append("\n## Limitations\n\n")
    lines.append("- Public-model, private-input only; model confidentiality is not implemented.\n")
    lines.append("- Model-agnostic verification, differential privacy, and input-provenance binding are not implemented in Stage 3.4.\n")
    lines.append("- Exact SHAP verification is specialized to Logistic Regression with fixed reference masking.\n")
    lines.append("- The reference vector is fixed by the circuit artifact; changing it requires a changed circuit/setup.\n")
    lines.append("- Sumcheck/GKR, Partition SHAP, and XGBoost-in-ZK are not implemented.\n")

    with out_md.open("w", encoding="utf-8") as f:
        f.writelines(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", default="1,2,3", help="Comma-separated sample IDs.")
    parser.add_argument("--force-setup", action="store_true", help="Regenerate zkey and verification key.")
    args = parser.parse_args(argv)

    _require([R1CS, WASM, WITNESS_GEN, SNARKJS])
    samples = [int(x.strip()) for x in str(args.samples).split(",") if x.strip()]
    started = _utc_now_iso()

    print("Stage 3.4 Phase C: Groth16 setup/prove/verify")
    setup_steps = setup_if_needed(force=bool(args.force_setup))
    for step in setup_steps:
        print(f"{step['status']}: {step['step']} ({step.get('duration_ms', 0)} ms)")
        if step.get("status") == "FAIL":
            print((step.get("stderr") or step.get("stdout") or "")[-2000:])
            return 1

    prepare_steps = prepare_inputs(samples)
    for step in prepare_steps:
        print(f"{step['status']}: {step['step']} ({step.get('duration_ms', 0)} ms)")
        if step.get("status") == "FAIL":
            print((step.get("stderr") or step.get("stdout") or "")[-2000:])
            return 1

    stats = r1cs_info()
    sample_results = []
    for sample_id in samples:
        print(f"\nSample {sample_id}:")
        result = prove_and_verify(sample_id)
        sample_results.append(result)
        for step in result["steps"]:
            print(f"  {step['status']}: {step['step']} ({step['duration_ms']} ms)")
            if step.get("status") == "FAIL":
                print((step.get("stderr") or step.get("stdout") or "")[-2000:])
                return 1

    payload: Dict[str, object] = {
        "created_utc": _utc_now_iso(),
        "started_utc": started,
        "samples": samples,
        "setup_steps": setup_steps,
        "prepare_steps": prepare_steps,
        "circuit_stats": stats,
        "artifact_sizes": {
            "r1cs_bytes": _file_size(R1CS),
            "wasm_bytes": _file_size(WASM),
            "zkey_bytes": _file_size(ZKEY_FINAL),
            "vkey_bytes": _file_size(VKEY),
        },
        "sample_results": sample_results,
    }
    write_reports(payload)
    print("\nWrote reports:")
    print("  reports/STAGE34_PROOF_REPORT.json")
    print("  reports/STAGE34_PROOF_REPORT.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
