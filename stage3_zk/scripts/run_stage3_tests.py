#!/usr/bin/env python
"""ZK Stage 3 test harness.

Goal: provide a single entrypoint to run the most important ZK checks used in the thesis:
- Prepare circuit inputs for samples (1..3)
- (Optional) build circuits
- Witness generation smoke tests (correct inputs should succeed)
- Stage 3.3 security tests (wrong explanation / malicious witness should fail)

This script is intentionally placed in stage3_zk/scripts (no spaces in path) so it can
be invoked from npm scripts reliably on Windows.

Usage examples (run from stage3_zk/):
  python scripts/run_stage3_tests.py --stage 33 --samples 1,2,3
  python scripts/run_stage3_tests.py --stage all --build

Exit code: 0 if all selected checks pass; 1 otherwise.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
import shutil
import json
import platform
import time
from datetime import datetime, timezone
from typing import Iterable, List, Sequence


STAGE3_ZK_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


@dataclass
class StepResult:
    name: str
    ok: bool
    details: str = ""
    duration_ms: int | None = None
    skipped: bool = False


def _run(cmd: Sequence[str], cwd: str | None = None, timeout_s: int | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        list(cmd),
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout_s,
    )


def _python() -> str:
    return sys.executable


def _ps() -> str:
    return "powershell"


def _snarkjs_cli() -> list[str] | None:
    """Return a command prefix to invoke snarkjs.

    Prefers:
      1) global snarkjs on PATH
      2) local node_modules/.bin/snarkjs(.cmd)
      3) npx snarkjs
    """

    global_snarkjs = shutil.which("snarkjs")
    if global_snarkjs:
        return [global_snarkjs]

    # Local install in this repo.
    local_bin = Path(STAGE3_ZK_DIR) / "node_modules" / ".bin"
    if os.name == "nt":
        local_snarkjs = local_bin / "snarkjs.cmd"
    else:
        local_snarkjs = local_bin / "snarkjs"

    if local_snarkjs.exists():
        return [str(local_snarkjs)]

    npx = shutil.which("npx")
    if npx:
        return [npx, "snarkjs"]

    return None


def _rel(p: str) -> str:
    try:
        return os.path.relpath(p, STAGE3_ZK_DIR)
    except ValueError:
        return p


def _file_size_bytes(path: str) -> int | None:
    try:
        return int(os.path.getsize(path))
    except OSError:
        return None


def _read_json_file(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _parse_r1cs_info(text: str) -> dict:
    info: dict = {}
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        if "Curve:" in line:
            info["curve"] = line.split("Curve:", 1)[1].strip()
            continue
        if "# of" in line and ":" in line:
            # Example: "[INFO]  snarkJS: # of Constraints: 3831"
            try:
                key_part = line.split("# of", 1)[1]
                key, val = key_part.split(":", 1)
                k = key.strip().lower().replace(" ", "_")
                v = val.strip()
                info[k] = int(v) if v.isdigit() else v
            except Exception:
                continue
    return info


def _r1cs_info_for_stage(stage: str) -> dict | None:
    snarkjs = _snarkjs_cli()
    if not snarkjs:
        return None

    circuit = _stage_circuit_name(stage)
    build_dir, _, _ = _witness_paths(stage)
    r1cs_path = os.path.join(build_dir, f"{circuit}.r1cs")
    if not os.path.exists(r1cs_path):
        return None

    proc = _run([*snarkjs, "r1cs", "info", r1cs_path], cwd=STAGE3_ZK_DIR, timeout_s=30)
    text = (proc.stdout or "") + "\n" + (proc.stderr or "")
    parsed = _parse_r1cs_info(text)
    if parsed:
        parsed["source"] = "snarkjs r1cs info"
    return parsed or None


def _public_signal_count(path: str) -> int | None:
    try:
        v = _read_json_file(path)
    except OSError:
        return None
    except json.JSONDecodeError:
        return None

    if isinstance(v, list):
        return len(v)
    return None


def _collect_circuit_stats(stages: Sequence[str], samples: Sequence[int]) -> dict:
    stats: dict = {}

    for stage in stages:
        circuit = _stage_circuit_name(stage)
        build_dir, wasm_path, _ = _witness_paths(stage)
        build_dir_path = Path(build_dir)

        r1cs = str(build_dir_path / f"{circuit}.r1cs")
        zkey = str(build_dir_path / f"{circuit}_final.zkey")
        vkey = str(build_dir_path / "verification_key.json")

        stage_stats: dict = {
            "stage": stage,
            "circuit": circuit,
            "r1cs": {"path": _rel(r1cs), "size_bytes": _file_size_bytes(r1cs)},
            "wasm": {"path": _rel(wasm_path), "size_bytes": _file_size_bytes(wasm_path)},
            "zkey_final": {"path": _rel(zkey), "size_bytes": _file_size_bytes(zkey)},
            "verification_key": {"path": _rel(vkey), "size_bytes": _file_size_bytes(vkey)},
            "r1cs_info": _r1cs_info_for_stage(stage),
        }

        proofs_dir = Path(_outputs_proofs_dir())
        proof_rows: list[dict] = []
        for sid in samples:
            proof_path = str(proofs_dir / f"proof_stage{stage}_sample_{sid}.json")
            public_path = str(proofs_dir / f"public_stage{stage}_sample_{sid}.json")
            proof_rows.append(
                {
                    "sample": sid,
                    "proof": {"path": _rel(proof_path), "size_bytes": _file_size_bytes(proof_path)},
                    "public": {
                        "path": _rel(public_path),
                        "size_bytes": _file_size_bytes(public_path),
                        "n_public_signals": _public_signal_count(public_path),
                    },
                }
            )

        stage_stats["proofs"] = proof_rows
        stats[stage] = stage_stats

    return stats


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _git_commit() -> str | None:
    repo_root = os.path.abspath(os.path.join(STAGE3_ZK_DIR, ".."))
    try:
        proc = _run(["git", "rev-parse", "HEAD"], cwd=repo_root, timeout_s=10)
        if proc.returncode == 0:
            return (proc.stdout or "").strip() or None
    except OSError:
        return None
    return None


def _cmd_version(cmd: Sequence[str]) -> str | None:
    try:
        proc = _run(cmd, cwd=STAGE3_ZK_DIR, timeout_s=10)
    except OSError:
        if os.name == "nt" and cmd and isinstance(cmd[0], str) and "." not in cmd[0]:
            # Common Windows case: npm is npm.cmd, etc.
            alt0 = cmd[0] + ".cmd"
            try:
                proc = _run([alt0, *cmd[1:]], cwd=STAGE3_ZK_DIR, timeout_s=10)
            except OSError:
                return None
        else:
            return None
    out = ((proc.stdout or "").strip() or (proc.stderr or "").strip())
    if not out:
        return None
    return out.splitlines()[0].strip()


def _snarkjs_version(snarkjs_cmd: list[str] | None) -> str | None:
    # 1) Try cli --version (not always supported)
    if snarkjs_cmd:
        v = _cmd_version([*snarkjs_cmd, "--version"])
        if not v:
            v = _cmd_version([*snarkjs_cmd, "-v"])
        if v:
            return v

    # 2) Try reading the installed module version (works if node_modules present)
    try:
        proc = _run(
            [
                "node",
                "-e",
                "const p=require('snarkjs/package.json'); console.log(p.name+'@'+p.version)",
            ],
            cwd=STAGE3_ZK_DIR,
            timeout_s=10,
        )
        if proc.returncode == 0:
            out = (proc.stdout or "").strip()
            if out:
                return out.splitlines()[0].strip()
    except OSError:
        pass

    return None


def _collect_environment() -> dict:
    snarkjs = _snarkjs_cli()
    return {
        "os": {
            "platform": platform.platform(),
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "python_implementation": platform.python_implementation(),
        },
        "python": {
            "executable": sys.executable,
            "version": platform.python_version(),
            "version_full": sys.version.replace("\n", " "),
        },
        "node": {
            "version": _cmd_version(["node", "--version"]),
            "npm_version": _cmd_version(["npm", "--version"]),
        },
        "snarkjs": {
            "command": snarkjs,
            "version": _snarkjs_version(snarkjs),
        },
        "git": {
            "commit": _git_commit(),
        },
    }


def _repo_path(*parts: str) -> str:
    return os.path.join(STAGE3_ZK_DIR, *parts)


def _outputs_proofs_dir() -> str:
    return _repo_path("outputs", "proofs")


def _witness_paths(stage: str) -> tuple[str, str, str]:
    """Return (build_dir, wasm_path, generate_witness_js_path) for a stage."""

    if stage == "31":
        build_dir = os.path.join(STAGE3_ZK_DIR, "circuits", "inference_only", "build")
        js_dir = os.path.join(build_dir, "inference_only_js")
        wasm = os.path.join(js_dir, "inference_only.wasm")
        gen = os.path.join(js_dir, "generate_witness.js")
        return build_dir, wasm, gen

    if stage == "32":
        build_dir = os.path.join(STAGE3_ZK_DIR, "circuits", "semantic_groups", "build")
        js_dir = os.path.join(build_dir, "semantic_groups_js")
        wasm = os.path.join(js_dir, "semantic_groups.wasm")
        gen = os.path.join(js_dir, "generate_witness.js")
        return build_dir, wasm, gen

    if stage == "33":
        build_dir = os.path.join(STAGE3_ZK_DIR, "circuits", "top3_explanation", "build")
        js_dir = os.path.join(build_dir, "top3_explanation_js")
        wasm = os.path.join(js_dir, "top3_explanation.wasm")
        gen = os.path.join(js_dir, "generate_witness.js")
        return build_dir, wasm, gen

    raise ValueError(f"Unknown stage: {stage}")


def _stage_circuit_name(stage: str) -> str:
    if stage == "31":
        return "inference_only"
    if stage == "32":
        return "semantic_groups"
    if stage == "33":
        return "top3_explanation"
    raise ValueError(f"Unknown stage: {stage}")


def _delete_if_exists(path: str) -> bool:
    try:
        if os.path.exists(path):
            os.remove(path)
            return True
    except OSError:
        return False
    return False


def _clean_stage(stage: str, samples: Sequence[int]) -> StepResult:
    """Remove generated artifacts that can go stale between runs."""


    removed: List[str] = []
    build_dir, _, _ = _witness_paths(stage)
    build_dir_path = Path(build_dir)

    # Inputs / witnesses / malicious artifacts in build dir.
    if build_dir_path.exists():
        for sid in samples:
            for p in [
                build_dir_path / f"input_sample_{sid}.json",
                build_dir_path / f"input_sample_{sid}_WRONG.json",
                build_dir_path / f"witness_sample_{sid}.wtns",
            ]:
                if _delete_if_exists(str(p)):
                    removed.append(str(p))

        # Files created by stage 3.3 security scripts.
        for p in build_dir_path.glob("malicious_input_*.json"):
            if _delete_if_exists(str(p)):
                removed.append(str(p))
        for p in build_dir_path.glob("witness_*.wtns"):
            if _delete_if_exists(str(p)):
                removed.append(str(p))
        for p in build_dir_path.glob("proof_*.json"):
            if _delete_if_exists(str(p)):
                removed.append(str(p))
        for p in build_dir_path.glob("public_*.json"):
            if _delete_if_exists(str(p)):
                removed.append(str(p))

    # Proof/public outputs stored under outputs/proofs (used by validate_stage33.py).
    proofs_dir = Path(_outputs_proofs_dir())
    proofs_dir.mkdir(parents=True, exist_ok=True)
    for sid in samples:
        proof_out = proofs_dir / f"proof_stage{stage}_sample_{sid}.json"
        public_out = proofs_dir / f"public_stage{stage}_sample_{sid}.json"
        if _delete_if_exists(str(proof_out)):
            removed.append(str(proof_out))
        if _delete_if_exists(str(public_out)):
            removed.append(str(public_out))

        # Back-compat names used historically for stage33.
        if stage == "33":
            proof_out2 = proofs_dir / f"proof_stage33_sample_{sid}.json"
            public_out2 = proofs_dir / f"public_stage33_sample_{sid}.json"
            if _delete_if_exists(str(proof_out2)):
                removed.append(str(proof_out2))
            if _delete_if_exists(str(public_out2)):
                removed.append(str(public_out2))

    details = "Removed:\n" + "\n".join(removed[:100]) if removed else "Nothing to remove."
    return StepResult(f"clean_stage{stage}", True, details)


def _prepare_input(stage: str, sample_id: int) -> StepResult:
    if stage == "31":
        script = os.path.join(STAGE3_ZK_DIR, "scripts", "stage 3.1", "01_prepare_input.py")
    elif stage == "32":
        script = os.path.join(STAGE3_ZK_DIR, "scripts", "stage 3.2", "01_prepare_input_stage32.py")
    elif stage == "33":
        script = os.path.join(STAGE3_ZK_DIR, "scripts", "stage 3.3", "01_prepare_input_stage33.py")
    else:
        return StepResult(f"prepare_input_stage{stage}_sample{sample_id}", False, f"Unknown stage {stage}")

    if not os.path.exists(script):
        return StepResult(f"prepare_input_stage{stage}_sample{sample_id}", False, f"Missing script: {script}")

    t0 = time.monotonic()
    proc = _run([_python(), script, str(sample_id)], cwd=STAGE3_ZK_DIR, timeout_s=120)
    dt_ms = int((time.monotonic() - t0) * 1000)
    ok = proc.returncode == 0
    details = (proc.stdout or "")[-1000:] + ("\n" + (proc.stderr or "")[-1000:] if proc.stderr else "")
    return StepResult(f"prepare_input_stage{stage}_sample{sample_id}", ok, details.strip(), dt_ms)


def _build_stage(stage: str) -> StepResult:
    if stage == "31":
        script = os.path.join(STAGE3_ZK_DIR, "scripts", "stage 3.1", "02_build_circuit.ps1")
    elif stage == "32":
        script = os.path.join(STAGE3_ZK_DIR, "scripts", "stage 3.2", "02_build_circuit_stage32.ps1")
    elif stage == "33":
        script = os.path.join(STAGE3_ZK_DIR, "scripts", "stage 3.3", "02_build_circuit_stage33.ps1")
    else:
        return StepResult(f"build_stage{stage}", False, f"Unknown stage {stage}")

    if not os.path.exists(script):
        return StepResult(f"build_stage{stage}", False, f"Missing build script: {script}")

    t0 = time.monotonic()
    proc = _run([_ps(), "-ExecutionPolicy", "Bypass", "-File", script], cwd=STAGE3_ZK_DIR, timeout_s=60 * 30)
    dt_ms = int((time.monotonic() - t0) * 1000)
    ok = proc.returncode == 0
    details = (proc.stdout or "")[-2000:] + ("\n" + (proc.stderr or "")[-2000:] if proc.stderr else "")
    return StepResult(f"build_stage{stage}", ok, details.strip(), dt_ms)


def _witness_smoke(stage: str, sample_id: int) -> StepResult:
    build_dir, wasm, gen = _witness_paths(stage)

    input_file = os.path.join(build_dir, f"input_sample_{sample_id}.json")
    witness_out = os.path.join(build_dir, f"witness_sample_{sample_id}.wtns")

    if not (os.path.exists(wasm) and os.path.exists(gen)):
        return StepResult(
            f"witness_smoke_stage{stage}_sample{sample_id}",
            False,
            "Missing compiled JS/WASM. Run with --build (or run the stage build script) first.",
        )

    if not os.path.exists(input_file):
        return StepResult(
            f"witness_smoke_stage{stage}_sample{sample_id}",
            False,
            f"Missing input: {input_file}. Run prepare_input first.",
        )

    t0 = time.monotonic()
    proc = _run(["node", gen, wasm, input_file, witness_out], cwd=STAGE3_ZK_DIR, timeout_s=120)
    dt_ms = int((time.monotonic() - t0) * 1000)
    ok = proc.returncode == 0
    details = (proc.stdout or "")[-800:] + ("\n" + (proc.stderr or "")[-800:] if proc.stderr else "")
    return StepResult(f"witness_smoke_stage{stage}_sample{sample_id}", ok, details.strip(), dt_ms)


def _prove(stage: str, sample_id: int, *, verify: bool) -> List[StepResult]:
    """Generate (and optionally verify) Groth16 proof for a given stage/sample."""

    circuit = _stage_circuit_name(stage)
    build_dir, _, _ = _witness_paths(stage)
    build_dir_path = Path(build_dir)

    input_file = build_dir_path / f"input_sample_{sample_id}.json"
    witness_file = build_dir_path / f"witness_sample_{sample_id}.wtns"
    zkey_file = build_dir_path / f"{circuit}_final.zkey"
    vkey_file = build_dir_path / "verification_key.json"

    proofs_dir = Path(_outputs_proofs_dir())
    proofs_dir.mkdir(parents=True, exist_ok=True)
    proof_out = proofs_dir / f"proof_stage{stage}_sample_{sample_id}.json"
    public_out = proofs_dir / f"public_stage{stage}_sample_{sample_id}.json"

    results: List[StepResult] = []

    if not zkey_file.exists():
        results.append(
            StepResult(
                f"prove_stage{stage}_sample{sample_id}",
                False,
                f"Missing zkey: {zkey_file}. Run with --build first.",
            )
        )
        return results

    if not witness_file.exists():
        results.append(
            StepResult(
                f"prove_stage{stage}_sample{sample_id}",
                False,
                f"Missing witness: {witness_file}. Run witness smoke (or run without --no-witness-smoke) first.",
            )
        )
        return results

    if not input_file.exists():
        results.append(
            StepResult(
                f"prove_stage{stage}_sample{sample_id}",
                False,
                f"Missing input: {input_file}. Run prepare_input first.",
            )
        )
        return results

    snarkjs = _snarkjs_cli()
    if not snarkjs:
        results.append(
            StepResult(
                f"prove_stage{stage}_sample{sample_id}",
                False,
                "Cannot find snarkjs. Install dependencies in stage3_zk (npm install) or ensure snarkjs/npx is on PATH.",
            )
        )
        return results

    t0 = time.monotonic()
    proc = _run(
        snarkjs
        + ["groth16", "prove", str(zkey_file), str(witness_file), str(proof_out), str(public_out)],
        cwd=STAGE3_ZK_DIR,
        timeout_s=60 * 5,
    )
    dt_ms = int((time.monotonic() - t0) * 1000)
    ok = proc.returncode == 0
    details = (proc.stdout or "")[-1500:] + ("\n" + (proc.stderr or "")[-1500:] if proc.stderr else "")
    results.append(StepResult(f"prove_stage{stage}_sample{sample_id}", ok, details.strip(), dt_ms))

    if not ok:
        return results

    if verify:
        if not vkey_file.exists():
            results.append(
                StepResult(
                    f"verify_stage{stage}_sample{sample_id}",
                    False,
                    f"Missing verification key: {vkey_file}.",
                )
            )
            return results

        t0 = time.monotonic()
        proc = _run(
            snarkjs + ["groth16", "verify", str(vkey_file), str(public_out), str(proof_out)],
            cwd=STAGE3_ZK_DIR,
            timeout_s=60 * 2,
        )
        dt_ms = int((time.monotonic() - t0) * 1000)
        ok = proc.returncode == 0
        details = (proc.stdout or "")[-1500:] + ("\n" + (proc.stderr or "")[-1500:] if proc.stderr else "")
        results.append(StepResult(f"verify_stage{stage}_sample{sample_id}", ok, details.strip(), dt_ms))

    return results


def _run_stage33_security_tests(sample_id: int, *, validate_proofs: bool) -> List[StepResult]:
    results: List[StepResult] = []

    # Wrong top-3 should fail witness generation.
    wrong_script = os.path.join(STAGE3_ZK_DIR, "scripts", "stage 3.3", "test_wrong_explanation.py")
    t0 = time.monotonic()
    proc = _run([_python(), wrong_script, str(sample_id)], cwd=STAGE3_ZK_DIR, timeout_s=120)
    dt_ms = int((time.monotonic() - t0) * 1000)
    results.append(
        StepResult(
            f"stage33_wrong_explanation_sample{sample_id}",
            proc.returncode == 0,
            ((proc.stdout or "") + "\n" + (proc.stderr or ""))[-1500:].strip(),
            dt_ms,
        )
    )

    # Malicious other2 should be rejected.
    mal_script = os.path.join(STAGE3_ZK_DIR, "scripts", "stage 3.3", "test_malicious_other2.py")
    t0 = time.monotonic()
    proc = _run([_python(), mal_script, str(sample_id)], cwd=STAGE3_ZK_DIR, timeout_s=120)
    dt_ms = int((time.monotonic() - t0) * 1000)
    results.append(
        StepResult(
            f"stage33_malicious_other2_sample{sample_id}",
            proc.returncode == 0,
            ((proc.stdout or "") + "\n" + (proc.stderr or ""))[-1500:].strip(),
            dt_ms,
        )
    )

    # If a proof exists, validate public top-3 matches expected.
    validate_script = os.path.join(STAGE3_ZK_DIR, "scripts", "stage 3.3", "validate_stage33.py")
    # By default we validate proof/public files generated by this harness under outputs/proofs.
    # (We keep the opt-in flag to avoid failures due to stale files from old runs.)
    public_file = os.path.join(STAGE3_ZK_DIR, "outputs", "proofs", f"public_stage33_sample_{sample_id}.json")
    if not validate_proofs:
        results.append(
            StepResult(
                f"stage33_validate_public_top3_sample{sample_id}",
                True,
                "Skipped (run with --validate-proofs to validate existing proof public signals).",
                0,
                True,
            )
        )
    elif os.path.exists(public_file):
        t0 = time.monotonic()
        proc = _run([_python(), validate_script, str(sample_id)], cwd=STAGE3_ZK_DIR, timeout_s=60)
        dt_ms = int((time.monotonic() - t0) * 1000)
        results.append(
            StepResult(
                f"stage33_validate_public_top3_sample{sample_id}",
                proc.returncode == 0,
                ((proc.stdout or "") + "\n" + (proc.stderr or ""))[-1500:].strip(),
                dt_ms,
            )
        )
    else:
        results.append(
            StepResult(
                f"stage33_validate_public_top3_sample{sample_id}",
                True,
                f"Skipped (no proof public file found at {public_file}).",
                0,
                True,
            )
        )

    return results


def _print_summary(results: Sequence[StepResult]) -> None:
    failures = [r for r in results if not r.ok]

    print("\n" + "=" * 78)
    print("ZK TEST HARNESS SUMMARY")
    print("=" * 78)

    for r in results:
        status = "SKIP" if r.skipped else ("PASS" if r.ok else "FAIL")
        print(f"[{status}] {r.name}")

    if failures:
        print("\n" + "-" * 78)
        print("Failure details (tail)")
        print("-" * 78)
        for r in failures:
            print(f"\n--- {r.name} ---")
            if r.details:
                print(r.details)
            else:
                print("(no output)")


def _write_report(
    *,
    report_dir: str,
    report_prefix: str,
    run: dict,
    formats: Sequence[str],
) -> list[str]:
    out_dir = Path(report_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    ts = run.get("started_at_utc") or _utc_now_iso()
    safe_ts = ts.replace(":", "").replace("-", "").replace("+", "").replace("T", "_")
    base = out_dir / f"{report_prefix}_{safe_ts}"

    written: list[str] = []

    if "json" in formats:
        json_path = str(base) + ".json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(run, f, indent=2, ensure_ascii=False)
        written.append(json_path)

        latest_json = str(out_dir / "LATEST_REPRO_REPORT.json")
        with open(latest_json, "w", encoding="utf-8") as f:
            json.dump(run, f, indent=2, ensure_ascii=False)
        written.append(latest_json)

    if "md" in formats:
        md_path = str(base) + ".md"
        lines: list[str] = []
        lines.append("# Reproducibility Run Report")
        lines.append("")
        lines.append(f"- Started (UTC): {run.get('started_at_utc')}")
        lines.append(f"- Finished (UTC): {run.get('finished_at_utc')}")
        lines.append(f"- Duration (ms): {run.get('duration_ms')}")
        lines.append(f"- Git commit: {run.get('environment', {}).get('git', {}).get('commit')}")
        lines.append("")
        lines.append("## Command")
        lines.append("")
        lines.append(f"- Args: `{run.get('args')}`")
        lines.append("")
        env = run.get("environment", {})
        lines.append("## Environment")
        lines.append("")
        lines.append(f"- OS: {env.get('os', {}).get('platform')}")
        lines.append(f"- Python: {env.get('python', {}).get('version')} ({env.get('python', {}).get('executable')})")
        lines.append(f"- Node: {env.get('node', {}).get('version')} (npm {env.get('node', {}).get('npm_version')})")
        lines.append(f"- snarkjs: {env.get('snarkjs', {}).get('version')}")
        lines.append("")

        circuit_stats = run.get("circuit_stats")
        if isinstance(circuit_stats, dict) and circuit_stats:
            lines.append("## Complexity & Communication")
            lines.append("")
            lines.append("| Stage | #Constraints | #Wires | Public Inputs | Private Inputs | R1CS (bytes) | WASM (bytes) | ZKey (bytes) | Proof (bytes) | Public (bytes) | #Public Signals |")
            lines.append("|------:|------------:|------:|-------------:|--------------:|------------:|------------:|------------:|------------:|-------------:|---------------:|")
            for stage, st in sorted(circuit_stats.items()):
                info = st.get("r1cs_info") or {}
                constraints = info.get("constraints")
                wires = info.get("wires")
                pub_in = info.get("public_inputs")
                priv_in = info.get("private_inputs")

                r1cs_b = (st.get("r1cs") or {}).get("size_bytes")
                wasm_b = (st.get("wasm") or {}).get("size_bytes")
                zkey_b = (st.get("zkey_final") or {}).get("size_bytes")

                # Use sample 1 proof/public sizes if present (good enough for master-level reporting)
                proof_b = None
                public_b = None
                n_pub_sig = None
                proofs = st.get("proofs") or []
                if isinstance(proofs, list) and proofs:
                    first = proofs[0]
                    proof_b = (first.get("proof") or {}).get("size_bytes")
                    pub = first.get("public") or {}
                    public_b = pub.get("size_bytes")
                    n_pub_sig = pub.get("n_public_signals")

                def _fmt(v):
                    return str(v) if v is not None else ""

                lines.append(
                    "| "
                    + " | ".join(
                        [
                            str(stage),
                            _fmt(constraints),
                            _fmt(wires),
                            _fmt(pub_in),
                            _fmt(priv_in),
                            _fmt(r1cs_b),
                            _fmt(wasm_b),
                            _fmt(zkey_b),
                            _fmt(proof_b),
                            _fmt(public_b),
                            _fmt(n_pub_sig),
                        ]
                    )
                    + " |"
                )
            lines.append("")

        lines.append("## Results")
        lines.append("")
        lines.append("| Step | Status | Duration (ms) |")
        lines.append("|------|--------|--------------:|")
        for s in run.get("steps", []):
            status = "SKIP" if s.get("skipped") else ("PASS" if s.get("ok") else "FAIL")
            dur = s.get("duration_ms")
            dur_str = str(dur) if dur is not None else ""
            lines.append(f"| {s.get('name')} | {status} | {dur_str} |")
        lines.append("")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        written.append(md_path)

        latest_md = str(out_dir / "LATEST_REPRO_REPORT.md")
        with open(latest_md, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        written.append(latest_md)

    return written


def _parse_samples(arg: str) -> List[int]:
    samples: List[int] = []
    for part in arg.split(","):
        part = part.strip()
        if not part:
            continue
        samples.append(int(part))
    if not samples:
        raise ValueError("No samples specified")
    return samples


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--stage",
        default="all",
        choices=["31", "32", "33", "all"],
        help="Which stage(s) to test.",
    )
    parser.add_argument(
        "--samples",
        default="1,2,3",
        help="Comma-separated sample ids (default: 1,2,3).",
    )
    parser.add_argument(
        "--build",
        action="store_true",
        help="Build circuits before running tests (runs PowerShell build scripts).",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove generated inputs/witness/proof/public files before running (avoids stale artifacts).",
    )
    parser.add_argument(
        "--no-witness-smoke",
        action="store_true",
        help="Skip witness-generation smoke tests (useful if not built).",
    )
    parser.add_argument(
        "--prove",
        action="store_true",
        help="Generate Groth16 proofs for correct inputs (requires witness + zkey).",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify generated Groth16 proofs (implies --prove).",
    )
    parser.add_argument(
        "--validate-proofs",
        action="store_true",
        help="Validate existing Groth16 public signals for Stage 3.3 (if present under outputs/proofs).",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Write a reproducibility run report (JSON+MD) to stage3_zk/reports.",
    )
    parser.add_argument(
        "--report-dir",
        default=os.path.join(STAGE3_ZK_DIR, "reports"),
        help="Directory to write reports (default: stage3_zk/reports).",
    )
    parser.add_argument(
        "--report-prefix",
        default="repro_run",
        help="Report filename prefix (default: repro_run).",
    )
    parser.add_argument(
        "--report-formats",
        default="json,md",
        help="Comma-separated formats to write: json,md (default: json,md).",
    )

    args = parser.parse_args(argv)
    samples = _parse_samples(args.samples)

    started_at = _utc_now_iso()
    t_run0 = time.monotonic()

    stages: List[str]
    if args.stage == "all":
        stages = ["31", "32", "33"]
    else:
        stages = [args.stage]

    results: List[StepResult] = []

    # Optional clean.
    if args.clean:
        for st in stages:
            results.append(_clean_stage(st, samples))

    # Optional build.
    if args.build:
        for st in stages:
            results.append(_build_stage(st))

    # Prepare inputs.
    for st in stages:
        for sid in samples:
            results.append(_prepare_input(st, sid))

    # Witness smoke tests.
    if not args.no_witness_smoke:
        for st in stages:
            for sid in samples:
                results.append(_witness_smoke(st, sid))

    # Proof generation / verification for correct inputs.
    if args.verify and not args.prove:
        args.prove = True

    if args.prove:
        for st in stages:
            for sid in samples:
                results.extend(_prove(st, sid, verify=bool(args.verify)))

        # If we just generated proofs for stage33, it is safe and meaningful to validate.
        if "33" in stages:
            args.validate_proofs = True

    # Stage 3.3 security tests.
    if "33" in stages:
        for sid in samples:
            results.extend(_run_stage33_security_tests(sid, validate_proofs=args.validate_proofs))

    _print_summary(results)

    finished_at = _utc_now_iso()
    duration_ms = int((time.monotonic() - t_run0) * 1000)

    if args.report:
        formats = [f.strip().lower() for f in str(args.report_formats).split(",") if f.strip()]
        env = _collect_environment()
        run = {
            "started_at_utc": started_at,
            "finished_at_utc": finished_at,
            "duration_ms": duration_ms,
            "args": {
                "stage": args.stage,
                "samples": samples,
                "build": bool(args.build),
                "clean": bool(args.clean),
                "no_witness_smoke": bool(args.no_witness_smoke),
                "prove": bool(args.prove),
                "verify": bool(args.verify),
                "validate_proofs": bool(args.validate_proofs),
            },
            "environment": env,
            "circuit_stats": _collect_circuit_stats(stages=stages, samples=samples),
            "steps": [
                {
                    "name": r.name,
                    "ok": bool(r.ok),
                    "skipped": bool(r.skipped),
                    "duration_ms": r.duration_ms,
                    "details_tail": r.details,
                }
                for r in results
            ],
        }
        written = _write_report(
            report_dir=str(args.report_dir),
            report_prefix=str(args.report_prefix),
            run=run,
            formats=formats,
        )
        if written:
            print("\nReport written:")
            for p in written:
                print(f"- {p}")

    return 0 if all(r.ok for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
