#!/usr/bin/env python
"""Generate a lightweight Stage 3.4 public-model registry manifest.

The registry is a thesis-facing verifier-policy artifact. It hashes the public
model, feature schema, semantic group map, bounds, Exact SHAP reference, and
Stage 3.4 circuit source so a verifier can bind proofs to an approved public
model version outside the circuit.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List


REPO_ROOT = Path(__file__).resolve().parents[1]

ARTIFACTS = [
    "stage3_zk/artifacts/model_public.json",
    "stage3_zk/artifacts/feature_order.json",
    "stage3_zk/artifacts/group_map.json",
    "stage3_zk/artifacts/bounds.json",
    "stage3_zk/artifacts/exact_shap_reference.json",
    "stage3_zk/circuits/exact_shap_top3/exact_shap_top3.circom",
    "stage3_zk/circuits/exact_shap_top3/build/verification_key.json",
]

OUT_PATH = REPO_ROOT / "stage3_zk" / "artifacts" / "model_registry_stage34.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json_if_exists(path: Path):
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def infer_feature_count() -> int | None:
    model = read_json_if_exists(REPO_ROOT / "stage3_zk" / "artifacts" / "model_public.json")
    if isinstance(model, dict) and "n" in model:
        return int(model["n"])

    feature_order = read_json_if_exists(REPO_ROOT / "stage3_zk" / "artifacts" / "feature_order.json")
    if isinstance(feature_order, list):
        return len(feature_order)
    if isinstance(feature_order, dict):
        for key in ("features", "feature_names", "feature_order"):
            value = feature_order.get(key)
            if isinstance(value, list):
                return len(value)
    return None


def artifact_records() -> List[Dict[str, object]]:
    records: List[Dict[str, object]] = []
    for rel in ARTIFACTS:
        path = REPO_ROOT / rel
        if path.exists():
            records.append(
                {
                    "path": rel.replace("\\", "/"),
                    "status": "present",
                    "sha256": sha256_file(path),
                    "bytes": path.stat().st_size,
                }
            )
        else:
            records.append(
                {
                    "path": rel.replace("\\", "/"),
                    "status": "missing",
                    "sha256": None,
                    "bytes": None,
                }
            )
    return records


def combined_digest(records: List[Dict[str, object]]) -> str:
    present = [
        f"{record['path']}:{record['sha256']}"
        for record in records
        if record.get("status") == "present" and record.get("sha256")
    ]
    joined = "\n".join(sorted(present)).encode("utf-8")
    return hashlib.sha256(joined).hexdigest()


def main() -> int:
    records = artifact_records()
    payload = {
        "created_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "stage": "3.4",
        "model_visibility": "public",
        "input_visibility": "private witness",
        "proof_system": "Circom + Groth16",
        "model_type": "Logistic Regression",
        "feature_count": infer_feature_count(),
        "artifacts": records,
        "combined_sha256": combined_digest(records),
        "notes": [
            "This registry is a verifier-policy artifact, not a hidden-model commitment.",
            "Missing optional files are recorded instead of failing generation.",
            "The verifier should approve the combined digest before accepting Stage 3.4 proofs for a model version.",
        ],
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")

    print(f"Wrote: {OUT_PATH}")
    print(f"Combined SHA-256: {payload['combined_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
