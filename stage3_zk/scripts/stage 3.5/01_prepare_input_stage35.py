#!/usr/bin/env python
"""Stage 3.5: prepare input for optional input-commitment prototype.

This builds on the Stage 3.4 Exact SHAP input and adds:

- public metadata_hash: a field hash of simulated event metadata
- private salt: deterministic per-sample salt for reproducible experiments

The circuit computes a public Poseidon rolling commitment over
metadata_hash, salt, and x_shifted[104]. A production deployment would record
the resulting commitment at ingestion time and require the verifier to compare
the public proof signal against that registered commitment.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict


SCRIPT_DIR = Path(__file__).resolve().parent
STAGE3 = SCRIPT_DIR.parents[1]
STAGE34_PREPARE = STAGE3 / "scripts" / "stage 3.4" / "01_prepare_input_stage34.py"
STAGE34_BUILD = STAGE3 / "circuits" / "exact_shap_top3" / "build"
STAGE35_BUILD = STAGE3 / "circuits" / "exact_shap_top3_commitment" / "build"
TEST_VECTORS = STAGE3 / "test_vectors"
REGISTRY_DIR = STAGE3 / "outputs" / "commitments"

BN254_PRIME = 21888242871839275222246405745257275088548364400416034343698204186575808495617


def _read_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def _field_hash(text: str) -> int:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return int.from_bytes(digest, byteorder="big") % BN254_PRIME


def _ensure_stage34_input(sample_id: int) -> Path:
    proc = subprocess.run(
        [sys.executable, str(STAGE34_PREPARE), str(int(sample_id))],
        cwd=str(STAGE3.parent),
        capture_output=True,
        text=True,
        timeout=120,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or proc.stdout)
    input_path = STAGE34_BUILD / f"input_sample_{sample_id}.json"
    if not input_path.exists():
        raise FileNotFoundError(f"Stage 3.4 input was not generated: {input_path}")
    return input_path


def prepare_input(sample_id: int) -> Path:
    stage34_input = _read_json(_ensure_stage34_input(sample_id))
    test_vec = _read_json(TEST_VECTORS / f"test_sample_{sample_id}.json")

    metadata_text = "|".join(
        [
            "ZK-XIDS-STAGE35",
            f"sample={sample_id}",
            f"label={test_vec.get('label', '')}",
            f"y_true={test_vec.get('y_true', '')}",
            f"y_hat={test_vec.get('y_hat', '')}",
            f"row_in_test_split={test_vec.get('row_in_test_split', test_vec.get('sample_id', ''))}",
            f"dataset_index={test_vec.get('dataset_index', '')}",
        ]
    )
    salt_text = f"ZK-XIDS-STAGE35-SALT|sample={sample_id}|row={test_vec.get('row_in_test_split', test_vec.get('sample_id', ''))}"

    metadata_hash = _field_hash(metadata_text)
    salt = _field_hash(salt_text)

    stage35_input: Dict[str, Any] = dict(stage34_input)
    stage35_input["metadata_hash"] = metadata_hash
    stage35_input["salt"] = salt

    STAGE35_BUILD.mkdir(parents=True, exist_ok=True)
    out_path = STAGE35_BUILD / f"input_sample_{sample_id}.json"
    _write_json(out_path, stage35_input)

    _write_json(
        REGISTRY_DIR / f"sample_{sample_id}_metadata.json",
        {
            "sample": int(sample_id),
            "metadata_text": metadata_text,
            "metadata_hash": str(metadata_hash),
            "salt_note": "The salt is private in the circuit input; deterministic only for this reproducible appendix experiment.",
            "commitment_policy": "Verifier should compare the public input_commitment signal against a commitment registered at ingestion time.",
            "stage35_input": str(out_path.relative_to(STAGE3)),
        },
    )

    print(f"OK: Prepared Stage 3.5 input: {out_path}")
    print(f"   metadata_hash: {metadata_hash}")
    print(f"   private salt: {salt}")
    return out_path


if __name__ == "__main__":
    sid = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    prepare_input(sid)
