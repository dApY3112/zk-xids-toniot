#!/usr/bin/env python
"""Stage 3.5 optional input-commitment prototype runner.

This runner is intentionally separate from Stage 3.4. It tests an appendix-only
prototype that adds a public Poseidon commitment to the private input witness
and simulated event metadata, while keeping the main Stage 3.4 claim unchanged.
"""

from __future__ import annotations

import argparse
import json
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
BUILD_DIR = STAGE3_ZK_DIR / "circuits" / "exact_shap_top3_commitment" / "build"
PROOFS_DIR = STAGE3_ZK_DIR / "outputs" / "proofs" / "stage35"
REPORTS_DIR = STAGE3_ZK_DIR / "reports"
SNARKJS = STAGE3_ZK_DIR / "node_modules" / "snarkjs" / "cli.js"
PTAU = STAGE3_ZK_DIR / "circuits" / "semantic_groups" / "powersOfTau28_hez_final_15.ptau"
PREPARE_INPUT = SCRIPT_DIR / "01_prepare_input_stage35.py"
STAGE34_REPORT = REPORTS_DIR / "STAGE34_PROOF_REPORT.json"

R1CS = BUILD_DIR / "exact_shap_top3_commitment.r1cs"
WASM = BUILD_DIR / "exact_shap_top3_commitment_js" / "exact_shap_top3_commitment.wasm"
WITNESS_GEN = BUILD_DIR / "exact_shap_top3_commitment_js" / "generate_witness.js"
ZKEY_0000 = BUILD_DIR / "exact_shap_top3_commitment_0000.zkey"
ZKEY_FINAL = BUILD_DIR / "exact_shap_top3_commitment_final.zkey"
VKEY = BUILD_DIR / "verification_key.json"

BN254_PRIME = 21888242871839275222246405745257275088548364400416034343698204186575808495617


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
        raise FileNotFoundError("Missing required Stage 3.5 artifacts:\n" + "\n".join(f"  - {p}" for p in missing))


def _file_size(path: Path) -> int:
    return int(path.stat().st_size) if path.exists() else 0


def _read_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


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
        timeout=900,
    )
    setup["step"] = "groth16_setup"
    setup["status"] = "PASS" if setup["returncode"] == 0 else "FAIL"
    steps.append(setup)
    if setup["returncode"] != 0:
        return steps

    entropy = "stage35-input-commitment-" + secrets.token_hex(16)
    contribute = _timed(
        [
            "node",
            str(SNARKJS),
            "zkey",
            "contribute",
            str(ZKEY_0000),
            str(ZKEY_FINAL),
            "--name=Stage3.5-InputCommitment",
            "-v",
            f"-e={entropy}",
        ],
        timeout=900,
    )
    contribute["step"] = "zkey_contribute"
    contribute["status"] = "PASS" if contribute["returncode"] == 0 else "FAIL"
    steps.append(contribute)
    if contribute["returncode"] != 0:
        return steps

    export = _timed(
        ["node", str(SNARKJS), "zkey", "export", "verificationkey", str(ZKEY_FINAL), str(VKEY)],
        timeout=180,
    )
    export["step"] = "export_verification_key"
    export["status"] = "PASS" if export["returncode"] == 0 else "FAIL"
    steps.append(export)
    return steps


def prepare_inputs(samples: Sequence[int]) -> List[Dict[str, object]]:
    steps: List[Dict[str, object]] = []
    _require([PREPARE_INPUT])
    for sample_id in samples:
        step = _timed([sys.executable, str(PREPARE_INPUT), str(int(sample_id))], timeout=120)
        step["step"] = f"prepare_input_sample_{sample_id}"
        step["status"] = "PASS" if step["returncode"] == 0 else "FAIL"
        steps.append(step)
    return steps


def tamper_public_commitment(public_path: Path, proof_path: Path, sample_id: int) -> Dict[str, object]:
    public_signals = _read_json(public_path)
    if not public_signals:
        raise RuntimeError(f"Public signal file is empty: {public_path}")

    tampered = list(public_signals)
    tampered[0] = str((int(tampered[0]) + 1) % BN254_PRIME)
    tampered_path = PROOFS_DIR / f"public_stage35_sample_{sample_id}_tampered_commitment.json"
    _write_json(tampered_path, tampered)

    verify = _timed(
        ["node", str(SNARKJS), "groth16", "verify", str(VKEY), str(tampered_path), str(proof_path)],
        timeout=120,
    )
    verify["step"] = f"verify_tampered_commitment_sample_{sample_id}"
    verify["status"] = "PASS" if verify["returncode"] != 0 else "FAIL"
    verify["expected_result"] = "verification_failure"
    verify["tampered_public"] = str(tampered_path.relative_to(STAGE3_ZK_DIR))
    return verify


def prove_and_verify(sample_id: int) -> Dict[str, object]:
    _require([WITNESS_GEN, WASM, ZKEY_FINAL, VKEY, SNARKJS])
    input_path = BUILD_DIR / f"input_sample_{sample_id}.json"
    witness_path = BUILD_DIR / f"witness_sample_{sample_id}.wtns"
    proof_path = PROOFS_DIR / f"proof_stage35_sample_{sample_id}.json"
    public_path = PROOFS_DIR / f"public_stage35_sample_{sample_id}.json"
    _require([input_path])
    PROOFS_DIR.mkdir(parents=True, exist_ok=True)

    witness = _timed(
        ["node", str(WITNESS_GEN), str(WASM), str(input_path), str(witness_path)],
        timeout=180,
    )
    witness["step"] = f"witness_sample_{sample_id}"
    witness["status"] = "PASS" if witness["returncode"] == 0 else "FAIL"
    if witness["returncode"] != 0:
        return {"sample": sample_id, "steps": [witness]}

    prove = _timed(
        ["node", str(SNARKJS), "groth16", "prove", str(ZKEY_FINAL), str(witness_path), str(proof_path), str(public_path)],
        timeout=900,
    )
    prove["step"] = f"prove_sample_{sample_id}"
    prove["status"] = "PASS" if prove["returncode"] == 0 else "FAIL"
    if prove["returncode"] != 0:
        return {"sample": sample_id, "steps": [witness, prove]}

    verify = _timed(
        ["node", str(SNARKJS), "groth16", "verify", str(VKEY), str(public_path), str(proof_path)],
        timeout=180,
    )
    verify["step"] = f"verify_sample_{sample_id}"
    verify["status"] = "PASS" if verify["returncode"] == 0 else "FAIL"
    if verify["returncode"] != 0:
        return {"sample": sample_id, "steps": [witness, prove, verify]}

    tamper = tamper_public_commitment(public_path, proof_path, sample_id)

    public_signals = _read_json(public_path)
    return {
        "sample": sample_id,
        "steps": [witness, prove, verify, tamper],
        "artifacts": {
            "witness": str(witness_path.relative_to(STAGE3_ZK_DIR)),
            "witness_bytes": _file_size(witness_path),
            "proof": str(proof_path.relative_to(STAGE3_ZK_DIR)),
            "proof_bytes": _file_size(proof_path),
            "public": str(public_path.relative_to(STAGE3_ZK_DIR)),
            "public_bytes": _file_size(public_path),
            "public_signal_count": len(public_signals),
            "input_commitment_public_signal_0": public_signals[0],
        },
    }


def _load_stage34_baseline() -> Dict[str, object]:
    if not STAGE34_REPORT.exists():
        return {}
    payload = _read_json(STAGE34_REPORT)
    stats = payload.get("circuit_stats", {})
    sample_results = payload.get("sample_results", [])
    prove_times = []
    verify_times = []
    witness_times = []
    for result in sample_results:
        for step in result.get("steps", []):
            name = str(step.get("step", ""))
            if name.startswith("witness_sample_"):
                witness_times.append(int(step.get("duration_ms", 0)))
            elif name.startswith("prove_sample_"):
                prove_times.append(int(step.get("duration_ms", 0)))
            elif name.startswith("verify_sample_"):
                verify_times.append(int(step.get("duration_ms", 0)))
    return {
        "constraints": stats.get("constraints"),
        "wires": stats.get("wires"),
        "public_inputs": stats.get("public_inputs"),
        "private_inputs": stats.get("private_inputs"),
        "outputs": stats.get("outputs"),
        "mean_witness_ms": round(sum(witness_times) / len(witness_times), 1) if witness_times else None,
        "mean_prove_ms": round(sum(prove_times) / len(prove_times), 1) if prove_times else None,
        "mean_verify_ms": round(sum(verify_times) / len(verify_times), 1) if verify_times else None,
    }


def _mean(values: Sequence[int]) -> float | None:
    return round(sum(values) / len(values), 1) if values else None


def _sample_step_times(sample_results: Sequence[Dict[str, object]], prefix: str) -> List[int]:
    out: List[int] = []
    for result in sample_results:
        for step in result.get("steps", []):
            if str(step.get("step", "")).startswith(prefix):
                out.append(int(step.get("duration_ms", 0)))
    return out


def write_reports(payload: Dict[str, object]) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out_json = REPORTS_DIR / "STAGE35_INPUT_COMMITMENT_REPORT.json"
    out_md = REPORTS_DIR / "STAGE35_INPUT_COMMITMENT_REPORT.md"
    appendix_md = STAGE3_ZK_DIR.parent / "reports" / "input_commitment_appendix.md"
    _write_json(out_json, payload)

    stats = payload["circuit_stats"]
    sizes = payload["artifact_sizes"]
    baseline = payload.get("stage34_baseline", {})
    sample_results = payload["sample_results"]
    constraints = stats.get("constraints")
    base_constraints = baseline.get("constraints") if isinstance(baseline, dict) else None
    overhead = None
    if isinstance(constraints, int) and isinstance(base_constraints, int) and base_constraints:
        overhead = round(constraints / base_constraints, 2)

    witness_mean = _mean(_sample_step_times(sample_results, "witness_sample_"))
    prove_mean = _mean(_sample_step_times(sample_results, "prove_sample_"))
    verify_mean = _mean(_sample_step_times(sample_results, "verify_sample_"))

    lines: List[str] = []
    lines.append("# Stage 3.5 Input Commitment Prototype Report\n\n")
    lines.append(f"Generated: {payload['created_utc']} (UTC)\n\n")
    lines.append("## Status\n\n")
    lines.append(
        "This is an optional appendix prototype, not part of the main Stage 3.4 claim. "
        "It adds a public Poseidon rolling commitment over the private input vector, a private salt, and a public metadata hash. "
        "A deployment would bind a proof to a concrete log row by comparing the public `input_commitment` signal against a commitment registered at ingestion time.\n\n"
    )
    lines.append("## Circuit Delta\n\n")
    lines.append("| Metric | Stage 3.4 | Stage 3.5 Prototype |\n|---|---:|---:|\n")
    for key in ["constraints", "wires", "public_inputs", "private_inputs", "outputs"]:
        base_val = baseline.get(key, "") if isinstance(baseline, dict) else ""
        lines.append(f"| {key.replace('_', ' ').title()} | {base_val} | {stats.get(key, '')} |\n")
    if overhead is not None:
        lines.append(f"\nConstraint overhead vs Stage 3.4: {overhead}x.\n")

    lines.append("\n## Artifact Sizes\n\n")
    lines.append("| Artifact | Bytes |\n|---|---:|\n")
    for key, value in sizes.items():
        lines.append(f"| {key} | {value} |\n")

    lines.append("\n## Proof Results\n\n")
    lines.append("| Sample | Witness ms | Prove ms | Verify ms | Tampered Commitment Rejected | Public Signals | Proof Bytes |\n")
    lines.append("|---:|---:|---:|---:|---|---:|---:|\n")
    for result in sample_results:
        steps = result.get("steps", [])
        step_map = {str(step.get("step", "")).split("_sample_")[0]: step for step in steps}
        witness_ms = step_map.get("witness", {}).get("duration_ms", "")
        prove_ms = step_map.get("prove", {}).get("duration_ms", "")
        verify_ms = step_map.get("verify", {}).get("duration_ms", "")
        tamper_ok = any(
            str(step.get("step", "")).startswith("verify_tampered_commitment")
            and step.get("status") == "PASS"
            for step in steps
        )
        artifacts = result.get("artifacts", {})
        lines.append(
            f"| {result['sample']} | {witness_ms} | {prove_ms} | {verify_ms} | "
            f"{'yes' if tamper_ok else 'no'} | {artifacts.get('public_signal_count', '')} | {artifacts.get('proof_bytes', '')} |\n"
        )

    lines.append("\n## Timing Summary\n\n")
    lines.append("| Metric | Stage 3.4 Mean | Stage 3.5 Mean |\n|---|---:|---:|\n")
    lines.append(f"| Witness ms | {baseline.get('mean_witness_ms', '') if isinstance(baseline, dict) else ''} | {witness_mean} |\n")
    lines.append(f"| Prove ms | {baseline.get('mean_prove_ms', '') if isinstance(baseline, dict) else ''} | {prove_mean} |\n")
    lines.append(f"| Verify ms | {baseline.get('mean_verify_ms', '') if isinstance(baseline, dict) else ''} | {verify_mean} |\n")

    lines.append("\n## Interpretation\n\n")
    lines.append("- The prototype closes the narrow `some private witness` gap only when an external system stores the same public commitment at ingestion time.\n")
    lines.append("- It does not authenticate SIEM provenance by itself; the verifier must compare public signal 0 to a trusted commitment registry entry.\n")
    lines.append("- It does not add differential privacy or model confidentiality. The public values remain `input_commitment`, `metadata_hash`, `y_hat`, and `top3_ids`.\n")
    lines.append("- The measured overhead is large enough that this should stay in the appendix unless the thesis needs a stronger provenance story.\n")

    with out_md.open("w", encoding="utf-8") as f:
        f.writelines(lines)

    appendix_lines: List[str] = []
    appendix_lines.append("# Appendix: Optional Input Commitment Prototype\n\n")
    appendix_lines.append(
        "The main ZK-XIDS prototype proves correct Logistic Regression prediction and semantic-group Exact SHAP top-3 explanation for a private witness, "
        "but Stage 3.4 deliberately does not bind that witness to a concrete log row. "
        "This appendix evaluates a small Stage 3.5 extension that adds such a binding point without changing the main claim.\n\n"
    )
    appendix_lines.append(
        "The extension computes a public Poseidon rolling commitment over `(domain_tag, metadata_hash, salt, x_shifted[104])`. "
        "`metadata_hash` is public, `salt` and `x_shifted` are private, and the resulting `input_commitment` is a public signal. "
        "A verifier can then reject proofs whose public commitment does not match a commitment registered when the log row was ingested.\n\n"
    )
    if overhead is not None:
        appendix_lines.append(
            f"In this experiment the circuit grows from {base_constraints} to {constraints} constraints, "
            f"about {overhead}x the Stage 3.4 constraint count. "
            f"The mean proving time over the tested samples is {prove_mean} ms and the mean verification time is {verify_mean} ms.\n\n"
        )
    appendix_lines.append(
        "The negative test tampers with public signal 0, which is the commitment, and the Groth16 verifier rejects the proof. "
        "This supports the appendix claim that commitment binding is technically feasible, but it should not be described as a full provenance system unless an external trusted ingestion registry is also implemented.\n\n"
    )
    appendix_lines.append(f"Detailed generated evidence: `stage3_zk/reports/{out_md.name}`.\n")
    appendix_md.parent.mkdir(parents=True, exist_ok=True)
    with appendix_md.open("w", encoding="utf-8") as f:
        f.writelines(appendix_lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", default="1", help="Comma-separated sample IDs.")
    parser.add_argument("--force-setup", action="store_true", help="Regenerate zkey and verification key.")
    args = parser.parse_args(argv)

    _require([R1CS, WASM, WITNESS_GEN, SNARKJS])
    samples = [int(x.strip()) for x in str(args.samples).split(",") if x.strip()]
    started = _utc_now_iso()

    print("Stage 3.5: optional input-commitment prototype")
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
        "stage34_baseline": _load_stage34_baseline(),
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
    print("  reports/STAGE35_INPUT_COMMITMENT_REPORT.json")
    print("  reports/STAGE35_INPUT_COMMITMENT_REPORT.md")
    print("  ../reports/input_commitment_appendix.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
