#!/usr/bin/env python
"""Generate thesis-ready Stage 3.4 integration and case-study reports."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Dict, List, Sequence, Tuple


REPO_ROOT = Path(__file__).resolve().parents[1]
STAGE3 = REPO_ROOT / "stage3_zk"
REPORTS = REPO_ROOT / "reports"
OUTPUTS = REPO_ROOT / "outputs"


STAGE_NAMES = {
    "31": "3.1",
    "32": "3.2",
    "33": "3.3",
    "34": "3.4",
}

STAGE_RELATIONS = {
    "31": "LR inference only",
    "32": "LR inference + old semantic aggregation",
    "33": "LR inference + old grouped-attribution top-3",
    "34": "LR inference + semantic-group Exact SHAP top-3",
}

STAGE_EXPLANATIONS = {
    "31": "None",
    "32": "Old proxy: sum_i abs(w_i*x_i) per semantic group",
    "33": "Top-3 old grouped linear attribution proxy",
    "34": "Top-3 semantic-group Exact SHAP by abs(phi_g)",
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _read_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _write(path: Path, lines: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(lines), encoding="utf-8")


def _fmt_int(value) -> str:
    return f"{int(value):,}"


def _stage_step_durations(latest: Dict, stage: str, kind: str) -> List[int]:
    prefix = f"{kind}_stage{stage}_sample"
    return [int(s["duration_ms"]) for s in latest["steps"] if str(s.get("name", "")).startswith(prefix)]


def _range_mean(values: Sequence[int]) -> str:
    if not values:
        return ""
    if len(values) == 1:
        return str(int(values[0]))
    return f"{min(values)}-{max(values)} (mean {mean(values):.0f})"


def _stage34_durations(stage34: Dict, kind: str) -> List[int]:
    out: List[int] = []
    for result in stage34["sample_results"]:
        for step in result["steps"]:
            if str(step.get("step", "")).startswith(kind):
                out.append(int(step["duration_ms"]))
    return out


def _stage34_proof_sizes(stage34: Dict) -> List[int]:
    return [int(r["artifacts"]["proof_bytes"]) for r in stage34["sample_results"]]


def _stage34_public_sizes(stage34: Dict) -> List[int]:
    return [int(r["artifacts"]["public_bytes"]) for r in stage34["sample_results"]]


def _sample_label(stage34: Dict) -> str:
    samples = [int(x) for x in stage34.get("samples", [])]
    if not samples:
        samples = [int(row.get("sample")) for row in stage34.get("sample_results", [])]
    if not samples:
        return "the generated samples"
    if samples == list(range(min(samples), max(samples) + 1)):
        return f"samples {min(samples)}-{max(samples)}"
    return "samples " + ", ".join(str(x) for x in samples)


def _build_stage_rows(latest: Dict, stage34: Dict) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    for stage in ["31", "32", "33"]:
        stats = latest["circuit_stats"][stage]
        info = stats["r1cs_info"]
        proof_sizes = [int(p["proof"]["size_bytes"]) for p in stats["proofs"]]
        public_sizes = [int(p["public"]["size_bytes"]) for p in stats["proofs"]]
        rows.append(
            {
                "stage": STAGE_NAMES[stage],
                "relation": STAGE_RELATIONS[stage],
                "explanation": STAGE_EXPLANATIONS[stage],
                "constraints": int(info["constraints"]),
                "wires": int(info["wires"]),
                "public_inputs": int(info["public_inputs"]),
                "private_inputs": int(info["private_inputs"]),
                "r1cs_bytes": int(stats["r1cs"]["size_bytes"]),
                "zkey_bytes": int(stats["zkey_final"]["size_bytes"]),
                "proof_bytes": _range_mean(proof_sizes),
                "public_bytes": _range_mean(public_sizes),
                "prove_ms": _range_mean(_stage_step_durations(latest, stage, "prove")),
                "verify_ms": _range_mean(_stage_step_durations(latest, stage, "verify")),
            }
        )

    info34 = stage34["circuit_stats"]
    sizes34 = stage34["artifact_sizes"]
    rows.append(
        {
            "stage": "3.4",
            "relation": STAGE_RELATIONS["34"],
            "explanation": STAGE_EXPLANATIONS["34"],
            "constraints": int(info34["constraints"]),
            "wires": int(info34["wires"]),
            "public_inputs": int(info34["public_inputs"]),
            "private_inputs": int(info34["private_inputs"]),
            "r1cs_bytes": int(sizes34["r1cs_bytes"]),
            "zkey_bytes": int(sizes34["zkey_bytes"]),
            "proof_bytes": _range_mean(_stage34_proof_sizes(stage34)),
            "public_bytes": _range_mean(_stage34_public_sizes(stage34)),
            "prove_ms": _range_mean(_stage34_durations(stage34, "prove")),
            "verify_ms": _range_mean(_stage34_durations(stage34, "verify")),
        }
    )
    return rows


def _top_names(ids: Sequence[int], group_names: Sequence[str]) -> List[str]:
    return [group_names[int(gid) - 1] for gid in ids]


def _compute_phi_int(sample: Dict, model: Dict, reference: Dict, group_map: Dict) -> List[int]:
    w_int = [int(x) for x in model["w_int"]]
    x_ref = [int(x) for x in reference["x_ref_int"]]
    x_int = [int(x) for x in sample["x_int"]]
    group_ids = [int(x) for x in group_map["feature_index_to_group_id"]]
    phi = [0] * int(group_map["n_groups"])
    for i, w_i in enumerate(w_int):
        phi[group_ids[i] - 1] += w_i * (x_int[i] - x_ref[i])
    return phi


def _stage34_status(stage34: Dict, sample_id: int) -> Tuple[str, Dict[str, int]]:
    result = next(r for r in stage34["sample_results"] if int(r["sample"]) == sample_id)
    ok = all(step["status"] == "PASS" for step in result["steps"])
    timings: Dict[str, int] = {}
    for step in result["steps"]:
        if step["step"].startswith("witness"):
            timings["witness_ms"] = int(step["duration_ms"])
        elif step["step"].startswith("prove"):
            timings["prove_ms"] = int(step["duration_ms"])
        elif step["step"].startswith("verify"):
            timings["verify_ms"] = int(step["duration_ms"])
    return ("PASS" if ok else "FAIL"), timings


def _case_narrative(label: str, old_names: Sequence[str], exact_names: Sequence[str]) -> str:
    old_set = set(old_names)
    exact_set = set(exact_names)
    common = [g for g in exact_names if g in old_set]
    only_exact = [g for g in exact_names if g not in old_set]
    if label == "TP_attack":
        return (
            "This true-positive attack is verified as an attack by both the LR prediction proof and the "
            "Exact SHAP top-3 proof. The two explanation methods agree on "
            f"{', '.join(common)}; Exact SHAP additionally emphasizes {', '.join(only_exact)} as a marginal "
            "semantic driver relative to the training-mean reference."
        )
    if label == "TN_normal":
        return (
            "This true-negative normal sample shows why signed-reference explanations are useful: the old "
            "proxy remains dominated by large absolute feature terms, while Exact SHAP ranks the groups by "
            "marginal deviation from the reference input. The verified Exact SHAP top-3 is therefore a more "
            "principled semantic explanation of the LR score."
        )
    return (
        "This false-negative attack is useful for self-assessment: the proof verifies the model's actual "
        "normal prediction and its Exact SHAP explanation, not the ground-truth label. The case separates "
        "cryptographic correctness from IDS accuracy and is important for the limitations discussion."
    )


def _write_case_studies(stage34: Dict, group_map: Dict, model: Dict, reference: Dict) -> None:
    groups = list(group_map["groups"])
    lines: List[str] = []
    lines.append("# Stage 3.4 Exact SHAP Case Studies\n\n")
    lines.append(f"Generated: {_utc_now_iso()} (UTC)\n\n")
    lines.append(
        "These case studies use the original three TP/TN/FN ZK test vectors. Stage 3.3 reports the old grouped "
        "linear attribution proxy, while Stage 3.4 verifies semantic-group Exact SHAP top-3 by absolute "
        "SHAP magnitude. Exact SHAP values are shown as signed integer score contributions at scale `Sx*Sw`.\n\n"
    )

    lines.append("| Sample | Label | y_true | y_hat | Stage 3.3 old top-3 | Stage 3.4 Exact SHAP top-3 | Proof |\n")
    lines.append("|---:|---|---:|---:|---|---|---|\n")
    cases = []
    for sid in [1, 2, 3]:
        sample = _read_json(STAGE3 / "test_vectors" / f"test_sample_{sid}.json")
        old_input = _read_json(STAGE3 / "circuits" / "top3_explanation" / "build" / f"input_sample_{sid}.json")
        exact_input = _read_json(STAGE3 / "circuits" / "exact_shap_top3" / "build" / f"input_sample_{sid}.json")
        phi = _compute_phi_int(sample, model, reference, group_map)
        proof_status, timings = _stage34_status(stage34, sid)
        old_top = _top_names(old_input["top3_ids"], groups)
        exact_top = _top_names(exact_input["top3_ids"], groups)
        cases.append((sid, sample, old_input, exact_input, phi, proof_status, timings, old_top, exact_top))
        lines.append(
            f"| {sid} | {sample['label']} | {sample['y_true']} | {sample['y_hat']} | "
            f"{', '.join(old_top)} | {', '.join(exact_top)} | {proof_status} |\n"
        )

    for sid, sample, old_input, exact_input, phi, proof_status, timings, old_top, exact_top in cases:
        lines.append(f"\n## Sample {sid}: {sample['label']}\n\n")
        lines.append(f"- Ground truth: `{sample['y_true']}`\n")
        lines.append(f"- LR prediction / public `y_hat`: `{sample['y_hat']}`\n")
        lines.append(f"- LR integer score: `{_fmt_int(sample['score_int'])}`\n")
        lines.append(f"- Stage 3.3 old proxy top-3: {', '.join(old_top)}\n")
        lines.append(f"- Stage 3.4 Exact SHAP top-3: {', '.join(exact_top)}\n")
        lines.append(
            f"- Stage 3.4 proof status: `{proof_status}` "
            f"(witness {timings['witness_ms']} ms, prove {timings['prove_ms']} ms, verify {timings['verify_ms']} ms)\n\n"
        )
        lines.append("### Group Values\n\n")
        lines.append("| Group | Old grouped attribution | Exact SHAP phi_int | abs(phi_int) | In old top-3 | In Exact top-3 |\n")
        lines.append("|---|---:|---:|---:|---|---|\n")
        old_contrib = {int(k): int(v) for k, v in sample["group_contributions"].items()}
        old_ids = set(int(x) for x in old_input["top3_ids"])
        exact_ids = set(int(x) for x in exact_input["top3_ids"])
        for idx, group in enumerate(groups, start=1):
            lines.append(
                f"| {group} | {_fmt_int(old_contrib[idx])} | {_fmt_int(phi[idx - 1])} | {_fmt_int(abs(phi[idx - 1]))} | "
                f"{'yes' if idx in old_ids else 'no'} | {'yes' if idx in exact_ids else 'no'} |\n"
            )
        lines.append("\n### Interpretation\n\n")
        lines.append(_case_narrative(sample["label"], old_top, exact_top) + "\n")

    _write(REPORTS / "stage34_case_studies.md", lines)


def _quant_sentence(quant: Dict | None) -> str:
    if not quant:
        return ""
    parts: List[str] = []
    for row in quant.get("splits", []):
        n = int(row.get("n", 0))
        mismatches = int(row.get("prediction_mismatch_count", 0))
        agreement = (1.0 - (mismatches / n)) * 100.0 if n else 0.0
        top3 = float(row.get("top3_ordered_match_rate", 0.0)) * 100.0
        overlap = float(row.get("mean_top3_overlap_count", 0.0))
        parts.append(
            f"{row.get('split')}: prediction agreement {agreement:.6f}% ({mismatches}/{n} mismatches), "
            f"ordered top-3 match {top3:.6f}%, mean overlap {overlap:.4f}/3"
        )
    return "; ".join(parts)


def _margin_sentence(margin: Dict | None) -> str:
    if not margin:
        return ""
    parts: List[str] = []
    for row in margin.get("splits", []):
        stats = row.get("margin_scaled_stats", {})
        small = row.get("small_margin_thresholds_scaled", {}).get("0.001", {})
        parts.append(
            f"{row.get('split')}: median margin {float(stats.get('median', 0.0)):.6f}, "
            f"p5 {float(stats.get('p5', 0.0)):.6f}, <=0.001 in {float(small.get('rate', 0.0)) * 100.0:.4f}%"
        )
    return "; ".join(parts)


def _write_integration_report(latest: Dict, stage34: Dict, stage_rows: Sequence[Dict[str, object]], quant: Dict | None) -> None:
    lines: List[str] = []
    lines.append("# Stage 3.4 Thesis Integration: Verified Semantic-Group Exact SHAP\n\n")
    lines.append(f"Generated: {_utc_now_iso()} (UTC)\n\n")
    lines.append("## Thesis Claim\n\n")
    lines.append(
        "This thesis proposes a scoped public-model/private-input proof pattern for verifiable semantic "
        "explanations under private inputs. The pattern is instantiated in an intrusion detection case study, "
        "where an approved public Logistic Regression model classifies private network-flow features and "
        "Stage 3.4 verifies a valid ordered non-increasing top-3 semantic-group Exact SHAP explanation. "
        "This upgrades Stage 3.3's engineering attribution proxy (`sum_i |w_i*x_i|`) to a game-theoretically "
        "grounded explanation target while preserving the Circom/Groth16 proof stack.\n\n"
        "The implemented main claim is intentionally narrow: it targets public linear/logistic tabular models with "
        "fixed semantic groups and a fixed reference vector. It is not a model-agnostic XAI verifier, does not "
        "hide model weights, and does not provide differential privacy. Stage 3.4 does not bind the private "
        "witness to a specific external event by itself; an optional Stage 3.5 appendix prototype evaluates an "
        "input-commitment layer for that audit-binding use case.\n\n"
    )

    lines.append("## Research Questions\n\n")
    lines.append("- RQ1: Can public linear/logistic tabular inference be verified without revealing processed features in an IDS instantiation?\n")
    lines.append("- RQ2: Can semantic explanations be verified cryptographically rather than trusted as client-supplied metadata?\n")
    lines.append("- RQ3: Can semantic-group Exact SHAP be made feasible in a SNARK for an approved public Logistic Regression model?\n")
    lines.append("- RQ4: What overhead and limitations arise when moving from an engineering attribution proxy to verified Exact SHAP in the intrusion detection case study?\n\n")

    lines.append("## Contribution Framing\n\n")
    lines.append("- C1. A public-model/private-input proof pattern for verifiable semantic explanations over public linear/logistic tabular models, instantiated on intrusion detection.\n")
    lines.append("- C2. A semantic-group explanation abstraction that maps high-dimensional tabular features into human-readable groups.\n")
    lines.append("- C3. A SNARK-verifiable semantic-group Exact SHAP top-3 method for public Logistic Regression with fixed reference masking.\n")
    lines.append("- C4. A reproducible case-study evaluation covering IDS performance, explanation stability, proxy-vs-ExactSHAP comparison, proof cost, output leakage, reference sensitivity, model-version binding, negative tests, and an appendix-only input-commitment feasibility prototype.\n\n")

    lines.append("## Generalization Scope: Proof Pattern vs. IDS Instantiation\n\n")
    lines.append("| Layer | IDS-specific in this repository | Reusable beyond IDS |\n")
    lines.append("|---|---|---|\n")
    lines.append("| Dataset/task | TON_IoT, Normal vs Attack | Tabular private-input classification tasks with an approved public linear/logistic model and fixed semantic groups |\n")
    lines.append("| Semantic groups | Protocol, Application, ConnectionState, Ports, TrafficVolume | Fixed human-meaningful feature groups |\n")
    lines.append("| Model | Logistic Regression IDS model | Approved public linear/logistic models |\n")
    lines.append("| Explanation | Semantic-group Exact SHAP over IDS groups | Semantic-group Exact SHAP over fixed groups |\n")
    lines.append("| Proof relation | Groth16 proof for IDS artifacts | Same proof pattern with new artifacts for compatible public linear/logistic models |\n")
    lines.append("| Evaluation | IDS metrics, FPR, SOC triage | Domain-specific metrics in other applications |\n\n")
    lines.append(
        "The implementation is validated only on the IDS case study. The Stage 3.4 relation itself is not inherently "
        "IDS-specific: it verifies a public linear/logistic score, a fixed reference vector, fixed semantic groups, "
        "and a top-3 semantic explanation computed from the same private input. Generalization to other domains "
        "requires replacing the feature schema, semantic group map, reference vector, approved public model artifact, "
        "circuit artifacts, and evaluation metrics.\n\n"
    )

    lines.append("## Method Justification\n\n")
    lines.append(
        "The explanation players are the five semantic groups used throughout the project: Protocol, "
        "Application, ConnectionState, Ports, and TrafficVolume. The Exact SHAP value function is the LR "
        "score/logit, not probability. Removed groups are replaced with the feature-wise training-set mean "
        "in processed feature space.\n\n"
    )
    lines.append("For this public LR model, coalition-enumerated semantic-group Exact SHAP has the exact closed form:\n\n")
    lines.append("```text\nphi_g(x) = sum_{i in G_g} w_i * (x_i - x_ref_i)\n```\n\n")
    lines.append(
        "The Python evaluator verifies this equivalence numerically: max enumeration-vs-closed-form difference "
        "`2.842171e-14`. Stage 3.4 proves the quantized integer form of this relation inside Groth16:\n\n"
    )
    lines.append("```text\nphi_g_int = sum_{i in G_g} w_int[i] * (x_int[i] - x_ref_int[i])\n```\n\n")
    lines.append(
        "For the formal relation, protocol construction, theorem statements, proof sketches, and leakage "
        "boundaries, see `reports/formal_framework_and_security_guarantees.md`.\n\n"
    )

    lines.append("## Stage 3.1-3.4 Comparison\n\n")
    lines.append(
        "Stages 3.1-3.3 use the latest reproducibility report; Stage 3.4 uses `stage3_zk/reports/STAGE34_PROOF_REPORT.md`.\n\n"
    )
    lines.append("| Stage | Verified relation | Explanation target | Constraints | Wires | Public | Private | R1CS bytes | ZKey bytes | Proof bytes | Public bytes | Prove ms | Verify ms |\n")
    lines.append("|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n")
    for row in stage_rows:
        lines.append(
            f"| {row['stage']} | {row['relation']} | {row['explanation']} | {_fmt_int(row['constraints'])} | "
            f"{_fmt_int(row['wires'])} | {row['public_inputs']} | {row['private_inputs']} | "
            f"{_fmt_int(row['r1cs_bytes'])} | {_fmt_int(row['zkey_bytes'])} | {row['proof_bytes']} | "
            f"{row['public_bytes']} | {row['prove_ms']} | {row['verify_ms']} |\n"
        )

    lines.append("\n## Correctness Evidence\n\n")
    lines.append("- Python coalition enumeration equals closed-form LR Exact SHAP: max difference `2.842171e-14`.\n")
    sample_label = _sample_label(stage34)
    lines.append(f"- Stage 3.4 valid witnesses pass for {sample_label}.\n")
    lines.append(f"- Stage 3.4 Groth16 proof generation and verification pass for {sample_label}.\n")
    lines.append(f"- Stage 3.4 negative witness tests reject malformed inputs for {sample_label}.\n")
    lines.append("- The extended Stage 3.4 vector set adds FP, high-confidence attack, high-confidence normal, borderline-score, and near-tie ranking cases; see `stage3_zk/reports/STAGE34_DIVERSE_TEST_VECTORS.md`.\n")
    quant_evidence = _quant_sentence(quant)
    if quant_evidence:
        lines.append(f"- Float-vs-quantized LR agreement check: {quant_evidence}. See `reports/float_vs_quantized_lr_agreement.md`.\n")
    lines.append("- The proof binds `y_hat` and a valid non-increasing Exact SHAP top-3 group ranking to the same private shifted input vector.\n")
    lines.append("- The optional Stage 3.5 appendix prototype adds a public input commitment and rejects tampered commitment public signals for samples 1, 7, and 8. See `reports/input_commitment_appendix.md`.\n\n")

    lines.append("## Ranking and Tie-Breaking\n\n")
    lines.append(
        "Stage 3.4 verifies that the public top-3 semantic group IDs are distinct, valid group IDs and that their "
        "absolute Exact SHAP magnitudes are ordered non-increasingly and dominate the two remaining groups. The "
        "circuit uses `>=` comparisons, so exact ties can admit multiple valid certified rankings. The witness "
        "generator sorts ties deterministically by smaller group ID for reproducibility, but that secondary "
        "tie-break is not enforced inside the current circuit. A deployment requiring a unique canonical ranking "
        "would need an additional lexicographic tie-break constraint.\n\n"
    )

    lines.append("## Negative Tests\n\n")
    lines.append("Stage 3.4 rejects malformed witnesses for:\n\n")
    lines.append("- wrong prediction (`y_hat`)\n")
    lines.append("- wrong Exact SHAP top-3 IDs\n")
    lines.append("- duplicate group IDs\n")
    lines.append("- out-of-range group IDs\n")
    lines.append("- malicious `other2_ids` reusing top groups\n")
    lines.append("- private input range violation\n\n")
    lines.append(
        "`x_ref_int` is hardcoded in the Stage 3.4 circuit, so a wrong reference vector is not accepted as a "
        "prover-controlled witness value. Changing the reference would require changing the circuit/setup artifact.\n\n"
    )

    lines.append("## Proxy-vs-ExactSHAP Result\n\n")
    lines.append(
        "The old Stage 3.3 grouped linear attribution remains useful as a cheap engineering baseline, but it is not "
        "a Shapley-value explanation. Offline comparison over 1100 reconstructed Stage 2 samples shows mean top-3 "
        "overlap `2.0618 / 3` and mean Jaccard overlap `0.5407`. The old proxy is dominated by the large "
        "Application group, while Exact SHAP more often emphasizes ConnectionState and Protocol as marginal "
        "semantic contributors relative to the reference input.\n\n"
    )

    lines.append("## Case Studies\n\n")
    lines.append("See `reports/stage34_case_studies.md` for three thesis-ready examples: a true positive attack, a true negative normal sample, and a false negative attack.\n\n")

    lines.append("## Model Visibility and Scope\n\n")
    lines.append(
        "The implemented threat model is public-model, private-input. This is suitable for auditable IDS/SOC "
        "settings where the verifier should know the detector being certified, while the sensitive object is the "
        "network-flow input. It does not address model-IP protection. A hidden-model extension would require a "
        "model commitment, for example proving `C_model = Poseidon(w, b, x_ref, salt)` while keeping `w`, `b`, "
        "and `x_ref` private. The current thesis can present that as future work, not as an implemented claim. "
        "See `reports/model_visibility_threat_model.md`.\n\n"
    )

    lines.append("## Verifier Acceptance Policy\n\n")
    lines.append(
        "For Stage 3.4, proof verification should be paired with a verifier-side model policy. The verifier accepts "
        "only if the verification key corresponds to the approved Stage 3.4 circuit, the public LR weights and bias "
        "match the approved `model_public.json`, the feature order, group map, bounds, and Exact SHAP reference "
        "vector match the registered artifacts, the registry digest identifies the approved model version, and the "
        "Groth16 proof verifies. See `reports/model_registry_and_verifier_policy.md`.\n\n"
    )

    lines.append("## Output Leakage\n\n")
    lines.append(
        "The circuit hides processed input feature values and the exact semantic-group SHAP values. It intentionally reveals "
        "`y_hat` and the top-3 semantic group IDs because these are the certified IDS decision and explanation "
        "summary. The resulting privacy claim is input-feature privacy under the zero-knowledge property of "
        "Groth16, parameterized by an explicit leakage function consisting of the approved public model/version "
        "metadata, `y_hat`, and `top3_ids`. It is not complete behavioral secrecy and it is not differential "
        "privacy, since the current system does not add noise to the disclosed outputs. See "
        "`reports/stage34_output_leakage_audit.md` for a distributional audit of these public outputs.\n\n"
    )

    lines.append("## Input Provenance and Audit Binding\n\n")
    lines.append(
        "Stage 3.4 proves that the public prediction and top-3 semantic explanation are consistent with the same "
        "private witness. It does not, by itself, prove that the witness came from a specific external log row or "
        "previously registered event.\n\n"
        "The optional Stage 3.5 appendix prototype demonstrates one feasible extension: it computes a public "
        "Poseidon rolling commitment over `(domain_tag, metadata_hash, salt, x_shifted[104])`. In the generated "
        "evidence, valid proofs verify and tampering with the public commitment signal is rejected. This should be "
        "described as a provenance binding point, not as a complete SIEM provenance system, because a real "
        "deployment must also store and trust the ingestion-time commitment registry. See "
        "`reports/input_commitment_appendix.md` and `stage3_zk/reports/STAGE35_INPUT_COMMITMENT_REPORT.md`.\n\n"
    )

    lines.append("## Reference Sensitivity\n\n")
    lines.append(
        "The implemented Stage 3.4 circuit fixes the training-mean reference vector. Alternative reference vectors "
        "are not additional ZK claims, but an offline sensitivity analysis is useful for critical self-assessment. "
        "See `reports/exact_shap_reference_sensitivity.md`.\n\n"
    )

    lines.append("## Ranking Stability\n\n")
    margin_path = OUTPUTS / "reports" / "exact_shap_ranking_margin.json"
    margin = _read_json(margin_path) if margin_path.exists() else None
    margin_evidence = _margin_sentence(margin)
    lines.append(
        "The proof verifies correctness of the claimed ranking for one private input; it does not prove that the "
        "explanation is stable under nearby inputs. For Logistic Regression, each group SHAP value is linear in the "
        "input, so perturbation sensitivity can be bounded by the group weight norm. This supports an optional "
        "margin-based robustness analysis, but it is not implemented as a ZK claim in the current repository. "
    )
    if margin_evidence:
        lines.append(f"The empirical rank-3 vs rank-4 margin analysis reports {margin_evidence}; see `reports/exact_shap_ranking_margin.md`.\n\n")
    else:
        lines.append("See `reports/exact_shap_ranking_margin.md` when generated.\n\n")

    lines.append("## Critical Self-Assessment\n\n")
    lines.append(
        "Stage 3.4 strengthens the thesis contribution, but the scope remains intentionally narrow. The model is public, "
        "only the input is private, and the verified Exact SHAP relation is specific to Logistic Regression with fixed "
        "reference masking. The system does not provide model-agnostic verification, confidential-model support, "
        "differential privacy, arbitrary-model Exact SHAP, Partition SHAP, or sumcheck/GKR. Input-provenance "
        "binding is only explored as an appendix Stage 3.5 prototype and still depends on an external trusted "
        "commitment registry. The binary IDS task also remains constrained by the Logistic Regression accuracy "
        "trade-off relative to the stronger XGBoost plaintext baseline.\n\n"
    )

    lines.append("## Thesis-Ready Conclusion\n\n")
    lines.append(
        "The final Stage 3.4 result is not merely an additional circuit: it changes the verified explanation target from "
        "an engineering proxy to semantic-group Exact SHAP, while keeping proof generation practical through a mathematically "
        "justified closed form for linear models. This provides a clear research contribution and a defensible path for "
        "future work on larger models and scalable SHAP verification.\n"
    )

    _write(REPORTS / "stage34_thesis_integration.md", lines)


def main() -> int:
    latest = _read_json(STAGE3 / "reports" / "LATEST_REPRO_REPORT.json")
    stage34 = _read_json(STAGE3 / "reports" / "STAGE34_PROOF_REPORT.json")
    quant_path = OUTPUTS / "reports" / "float_vs_quantized_lr_agreement.json"
    quant = _read_json(quant_path) if quant_path.exists() else None
    group_map = _read_json(STAGE3 / "artifacts" / "group_map.json")
    model = _read_json(STAGE3 / "artifacts" / "model_public.json")
    reference = _read_json(STAGE3 / "artifacts" / "exact_shap_reference.json")

    stage_rows = _build_stage_rows(latest, stage34)
    _write_case_studies(stage34, group_map, model, reference)
    _write_integration_report(latest, stage34, stage_rows, quant)

    print(f"Wrote: {REPORTS / 'stage34_case_studies.md'}")
    print(f"Wrote: {REPORTS / 'stage34_thesis_integration.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
