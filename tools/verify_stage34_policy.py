#!/usr/bin/env python
"""Verifier-policy checks for the Stage 3.4 public-model design.

This script does not replace Groth16 verification. It checks the thesis-level
policy layer around Stage 3.4: approved artifact hashes, public model binding,
public signal layout, and optionally snarkjs proof verification.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Sequence, Tuple


REPO_ROOT = Path(__file__).resolve().parents[1]
STAGE3 = REPO_ROOT / "stage3_zk"
DEFAULT_REGISTRY = STAGE3 / "artifacts" / "model_registry_stage34.json"
DEFAULT_MODEL = STAGE3 / "artifacts" / "model_public.json"
DEFAULT_BOUNDS = STAGE3 / "artifacts" / "bounds.json"
DEFAULT_PUBLIC = STAGE3 / "outputs" / "proofs" / "public_stage34_sample_1.json"
DEFAULT_PROOF = STAGE3 / "outputs" / "proofs" / "proof_stage34_sample_1.json"
DEFAULT_VKEY = STAGE3 / "circuits" / "exact_shap_top3" / "build" / "verification_key.json"
SNARKJS = STAGE3 / "node_modules" / "snarkjs" / "cli.js"
STAGE34_CIRCUIT = STAGE3 / "circuits" / "exact_shap_top3" / "exact_shap_top3.circom"


class PolicyError(RuntimeError):
    pass


def _read_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _combined_digest(records: Sequence[Dict[str, object]]) -> str:
    present = [
        f"{record['path']}:{record['sha256']}"
        for record in records
        if record.get("status") == "present" and record.get("sha256")
    ]
    return hashlib.sha256("\n".join(sorted(present)).encode("utf-8")).hexdigest()


def _parse_stage34_constants() -> Tuple[int, int, int, int, int, int]:
    text = STAGE34_CIRCUIT.read_text(encoding="utf-8")
    match = re.search(r"ExactShapTop3\((\d+),\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\)", text)
    if not match:
        raise PolicyError("Could not parse Stage 3.4 circuit constants")
    return tuple(int(x) for x in match.groups())  # n, nBits, B, maxAbsX, maxAbsW, nGroups


def _expected_public_prefix(model: Dict[str, object], max_abs_w: int, bias_shift: int) -> List[int]:
    w_int = [int(x) for x in model["w_int"]]
    b_int = int(model["b_int"])
    return [w + max_abs_w for w in w_int] + [b_int + bias_shift]


def check_registry(registry: Dict[str, object], *, repo_root: Path = REPO_ROOT) -> List[str]:
    messages: List[str] = []
    if registry.get("stage") != "3.4":
        raise PolicyError("Registry stage is not 3.4")
    if registry.get("model_visibility") != "public":
        raise PolicyError("Registry model_visibility is not public")
    if registry.get("input_visibility") != "private witness":
        raise PolicyError("Registry input_visibility is not private witness")

    for record in registry.get("artifacts", []):
        rel = str(record["path"])
        path = repo_root / rel
        status = record.get("status")
        if status == "missing":
            if path.exists():
                raise PolicyError(f"Registry marks artifact missing but file exists: {rel}")
            messages.append(f"OK missing optional artifact: {rel}")
            continue
        if not path.exists():
            raise PolicyError(f"Registry artifact missing on disk: {rel}")
        actual = _sha256_file(path)
        if actual != record.get("sha256"):
            raise PolicyError(f"SHA-256 mismatch for {rel}: expected {record.get('sha256')}, got {actual}")
        messages.append(f"OK artifact hash: {rel}")

    actual_combined = _combined_digest(registry.get("artifacts", []))
    if actual_combined != registry.get("combined_sha256"):
        raise PolicyError(
            f"Combined digest mismatch: expected {registry.get('combined_sha256')}, got {actual_combined}"
        )
    messages.append(f"OK combined digest: {actual_combined}")
    return messages


def check_public_signals(public_path: Path, *, model_path: Path = DEFAULT_MODEL) -> List[str]:
    model = _read_json(model_path)
    public = [int(x) for x in _read_json(public_path)]
    n, _n_bits, bias_shift, _max_abs_x, max_abs_w, _n_groups = _parse_stage34_constants()
    if int(model.get("n")) != n:
        raise PolicyError(f"Model feature count {model.get('n')} does not match circuit n={n}")
    expected_prefix = _expected_public_prefix(model, max_abs_w, bias_shift)
    expected_len = n + 1 + 1 + 3
    if len(public) != expected_len:
        raise PolicyError(f"Public signal count mismatch: expected {expected_len}, got {len(public)}")
    if public[: n + 1] != expected_prefix:
        raise PolicyError("Public weights/bias do not match approved model_public.json and circuit shifts")
    y_hat = public[n + 1]
    top3 = public[n + 2 : n + 5]
    if y_hat not in (0, 1):
        raise PolicyError(f"Public y_hat is not binary: {y_hat}")
    if len(set(top3)) != 3 or any(gid < 1 or gid > 5 for gid in top3):
        raise PolicyError(f"Public top3_ids are not distinct valid group IDs: {top3}")
    return [
        "OK public model signals match approved model_public.json",
        f"OK public y_hat: {y_hat}",
        f"OK public top3_ids: {top3}",
    ]


def verify_proof(proof_path: Path, public_path: Path, vkey_path: Path) -> str:
    if not SNARKJS.exists():
        raise PolicyError(f"Missing snarkjs CLI: {SNARKJS}")
    cmd = ["node", str(SNARKJS), "groth16", "verify", str(vkey_path), str(public_path), str(proof_path)]
    proc = subprocess.run(cmd, cwd=str(STAGE3), capture_output=True, text=True, timeout=120)
    if proc.returncode != 0:
        raise PolicyError("Groth16 verification failed:\n" + (proc.stderr or proc.stdout))
    return "OK Groth16 proof verifies"


def run_policy_checks(args: argparse.Namespace) -> List[str]:
    messages: List[str] = []
    registry = _read_json(Path(args.registry))
    messages.extend(check_registry(registry))
    messages.extend(check_public_signals(Path(args.public)))
    if not args.skip_proof:
        messages.append(verify_proof(Path(args.proof), Path(args.public), Path(args.vkey)))
    return messages


def _expect_fail(label: str, fn) -> str:
    try:
        fn()
    except PolicyError:
        return f"PASS negative policy case rejected: {label}"
    raise AssertionError(f"Negative policy case unexpectedly passed: {label}")


def run_self_test(args: argparse.Namespace) -> List[str]:
    registry = _read_json(Path(args.registry))
    public_path = Path(args.public)
    public = _read_json(public_path)
    messages = ["PASS positive policy case accepted"]
    run_policy_checks(args)

    bad_combined = copy.deepcopy(registry)
    bad_combined["combined_sha256"] = "0" * 64
    messages.append(_expect_fail("wrong combined registry digest", lambda: check_registry(bad_combined)))

    bad_artifact = copy.deepcopy(registry)
    for record in bad_artifact["artifacts"]:
        if record.get("status") == "present":
            record["sha256"] = "f" * 64
            break
    messages.append(_expect_fail("wrong artifact hash", lambda: check_registry(bad_artifact)))

    tmp_public = [str(x) for x in public]
    tmp_public[0] = str(int(tmp_public[0]) + 1)
    original_read = globals()["_read_json"]

    def fake_read_json(path: Path):
        if Path(path) == public_path:
            return tmp_public
        return original_read(path)

    globals()["_read_json"] = fake_read_json
    try:
        messages.append(_expect_fail("wrong public model signal", lambda: check_public_signals(public_path)))
    finally:
        globals()["_read_json"] = original_read

    tmp_public = [str(x) for x in public]
    tmp_public[-1] = tmp_public[-2]

    def fake_read_json_dup(path: Path):
        if Path(path) == public_path:
            return tmp_public
        return original_read(path)

    globals()["_read_json"] = fake_read_json_dup
    try:
        messages.append(_expect_fail("duplicate public top3 id", lambda: check_public_signals(public_path)))
    finally:
        globals()["_read_json"] = original_read

    return messages


def build_arg_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry", default=str(DEFAULT_REGISTRY))
    ap.add_argument("--public", default=str(DEFAULT_PUBLIC))
    ap.add_argument("--proof", default=str(DEFAULT_PROOF))
    ap.add_argument("--vkey", default=str(DEFAULT_VKEY))
    ap.add_argument("--skip-proof", action="store_true", help="Skip snarkjs Groth16 verification.")
    ap.add_argument("--self-test", action="store_true", help="Run in-memory negative policy tests.")
    return ap


def main(argv: Sequence[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    try:
        messages = run_self_test(args) if args.self_test else run_policy_checks(args)
    except (PolicyError, AssertionError) as exc:
        print(f"FAIL: {exc}")
        return 1
    for message in messages:
        print(message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
