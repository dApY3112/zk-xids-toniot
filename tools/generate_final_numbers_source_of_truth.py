#!/usr/bin/env python
"""Generate the thesis source-of-truth table for final reported numbers."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any, Dict, List, Sequence


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
OUTPUTS = ROOT / "outputs"
STAGE3 = ROOT / "stage3_zk"


def _read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _f(x: float, digits: int = 6) -> str:
    return f"{float(x):.{digits}f}"


def _pct(x: float) -> str:
    return f"{float(x) * 100.0:.6f}%"


def _conf(conf: Dict[str, Any]) -> str:
    return f"{conf.get('tn')}/{conf.get('fp')}/{conf.get('fn')}/{conf.get('tp')}"


def _durations(stage34: Dict[str, Any], step_prefix: str) -> List[int]:
    values: List[int] = []
    for sample in stage34.get("sample_results", []):
        for step in sample.get("steps", []):
            if str(step.get("step", "")).startswith(step_prefix):
                values.append(int(step.get("duration_ms", 0)))
    return values


def _sizes(stage34: Dict[str, Any], key: str) -> List[int]:
    out: List[int] = []
    for sample in stage34.get("sample_results", []):
        artifacts = sample.get("artifacts", {})
        if key in artifacts:
            out.append(int(artifacts[key]))
    return out


def _range_mean(values: Sequence[int]) -> str:
    if not values:
        return ""
    return f"{min(values)}-{max(values)} (mean {int(round(mean(values)))})"


def _sample_label(stage34: Dict[str, Any]) -> str:
    samples = [int(x) for x in stage34.get("samples", [])]
    if not samples:
        samples = [int(row.get("sample")) for row in stage34.get("sample_results", [])]
    if not samples:
        return "samples"
    if samples == list(range(min(samples), max(samples) + 1)):
        return f"samples {min(samples)}-{max(samples)}"
    return "samples " + ",".join(str(x) for x in samples)


def main() -> int:
    baseline = _read_json(OUTPUTS / "reports" / "baseline_metrics_extended.json")
    decision = _read_json(OUTPUTS / "reports" / "decision_engineering_baselines.json")
    cost = _read_json(OUTPUTS / "reports" / "cost_based_thresholds.json")
    quant = _read_json(OUTPUTS / "reports" / "float_vs_quantized_lr_agreement.json")
    margin = _read_json(OUTPUTS / "reports" / "exact_shap_ranking_margin.json")
    filewise = _read_json(OUTPUTS / "reports" / "filewise_holdout.json")
    attack_types = _read_json(OUTPUTS / "reports" / "attack_type_error_analysis.json")
    stage34 = _read_json(STAGE3 / "reports" / "STAGE34_PROOF_REPORT.json")
    stage35_path = STAGE3 / "reports" / "STAGE35_INPUT_COMMITMENT_REPORT.json"
    stage35 = _read_json(stage35_path) if stage35_path.exists() else None
    registry = _read_json(STAGE3 / "artifacts" / "model_registry_stage34.json")

    lines: List[str] = []
    lines.append("# Final Numbers Source of Truth\n\n")
    lines.append(f"Generated: {_utc_now_iso()} (UTC)\n\n")
    lines.append(
        "Use this file as the checklist for final thesis tables. Older benchmark artifacts may remain useful "
        "as historical optimization notes, but final claims should cite the source files listed here.\n\n"
    )

    lines.append("## Authoritative Files\n\n")
    lines.append("| Topic | Use this source | Notes |\n|---|---|---|\n")
    lines.append("| Baseline ML metrics | `reports/baseline_extended_metrics.md` / `outputs/reports/baseline_metrics_extended.json` | Main test-set classification table. |\n")
    lines.append("| Operating points and calibration | `reports/decision_engineering_baselines.md` / `outputs/reports/decision_engineering_baselines.json` | Low-FPR, balanced-MCC, high-recall thresholds. |\n")
    lines.append("| Cost-sensitive thresholds | `reports/cost_based_thresholds.md` / `outputs/reports/cost_based_thresholds.json` | FN/FP cost-ratio sweep. |\n")
    lines.append("| File-wise holdout robustness | `reports/filewise_holdout.md` / `outputs/reports/filewise_holdout.json` | Train on earlier-numbered files, evaluate on held-out later files. |\n")
    lines.append("| Attack-type error analysis | `reports/attack_type_error_analysis.md` / `outputs/reports/attack_type_error_analysis.json` | Post-hoc false-negative analysis using `type` metadata only after prediction. |\n")
    lines.append("| ML-to-ZK quantization agreement | `reports/float_vs_quantized_lr_agreement.md` / `outputs/reports/float_vs_quantized_lr_agreement.json` | Float sklearn LR vs integer LR relation. |\n")
    lines.append("| Exact SHAP ranking margin | `reports/exact_shap_ranking_margin.md` / `outputs/reports/exact_shap_ranking_margin.json` | Rank-3 vs rank-4 margin self-assessment. |\n")
    lines.append("| Stage 3.1-3.3 ZK evidence | `stage3_zk/reports/LATEST_REPRO_REPORT.md` | Current general ZK harness report. |\n")
    lines.append("| Stage 3.4 proof evidence | `stage3_zk/reports/STAGE34_PROOF_REPORT.md` | Exact SHAP circuit after WSL Circom rebuild and forced setup. |\n")
    lines.append("| Stage 3.4 diverse test vectors | `stage3_zk/reports/STAGE34_DIVERSE_TEST_VECTORS.md` / `stage3_zk/test_vectors/test_sample_4.json`-`test_sample_8.json` | FP, high-confidence, borderline, and near-tie cases. |\n")
    lines.append("| Stage 3.4 verifier policy | `reports/model_registry_and_verifier_policy.md` and `stage3_zk/artifacts/model_registry_stage34.json` | Registry digest and model binding. |\n")
    if stage35:
        lines.append("| Stage 3.5 input-commitment appendix | `reports/input_commitment_appendix.md` / `stage3_zk/reports/STAGE35_INPUT_COMMITMENT_REPORT.md` | Appendix-only provenance binding prototype; not part of the main Stage 3.4 claim. |\n")
    lines.append("\n")

    lines.append("## Baseline Classification Metrics\n\n")
    lines.append("Test-set metrics from `baseline_metrics_extended.json`.\n\n")
    lines.append("| Model | Operating point | Threshold | Balanced Acc | MCC | Attack Recall | Normal Recall/Spec | FPR | Confusion tn/fp/fn/tp |\n")
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|---|\n")
    for model_name in ["xgboost", "logistic_regression"]:
        model = baseline["models"][model_name]
        for point in ["default_0.5", "tuned_mcc", "tuned_bacc"]:
            block = model[point]
            metrics = block["metrics"]
            lines.append(
                f"| {model_name} | {point} | {_f(block['threshold'])} | {_f(metrics['balanced_accuracy'])} "
                f"| {_f(metrics['mcc'])} | {_f(metrics['attack_recall'])} "
                f"| {_f(metrics['normal_recall_specificity'])} | {_f(metrics['fpr'])} "
                f"| {_conf(block['confusion'])} |\n"
            )

    lines.append("\n## Operating Points\n\n")
    lines.append("Thresholds chosen on validation and evaluated on test, from `decision_engineering_baselines.json`.\n\n")
    lines.append("| Model | Point | Threshold | Attack Recall | Normal Recall/Spec | FPR | MCC | Confusion tn/fp/fn/tp |\n")
    lines.append("|---|---|---:|---:|---:|---:|---:|---|\n")
    for model_name in ["xgboost", "logistic_regression"]:
        points = decision["models"][model_name]["operating_points"]
        for point in ["low_fpr", "balanced_mcc", "high_recall"]:
            block = points[point]
            metrics = block["test"]["metrics"]
            lines.append(
                f"| {model_name} | {point} | {_f(block['threshold'])} | {_f(metrics['attack_recall'])} "
                f"| {_f(metrics['normal_recall_specificity'])} | {_f(metrics['fpr'])} "
                f"| {_f(metrics['mcc'])} | {_conf(block['test']['confusion'])} |\n"
            )

    lines.append("\n## Cost-Sensitive Thresholds\n\n")
    lines.append("Use `reports/cost_based_thresholds.md` for the full FN/FP sweep. Key ratio 1.0 rows are listed here.\n\n")
    lines.append("| Model | FN/FP ratio | Threshold | Test FPR | Test Recall | Test MCC | Test cost/sample |\n")
    lines.append("|---|---:|---:|---:|---:|---:|---:|\n")
    for model_name in ["logistic_regression", "xgboost"]:
        rows = cost["models"][model_name]["rows"]
        row = next(r for r in rows if float(r["fn_fp_ratio"]) == 1.0)
        metrics = row["test_metrics"]
        lines.append(
            f"| {model_name} | 1.0 | {_f(row['threshold'])} | {_f(metrics['fpr'])} "
            f"| {_f(metrics['attack_recall'])} | {_f(metrics['mcc'])} | {_f(row['test_cost_per_sample'])} |\n"
        )

    lines.append("\n## ML-to-ZK Quantization Agreement\n\n")
    lines.append("Float sklearn LR vs Stage 3 integer LR relation, from `float_vs_quantized_lr_agreement.json`.\n\n")
    lines.append("| Split | n | Prediction agreement | Mismatches | Ordered Exact SHAP top-3 match | Mean top-3 overlap / 3 |\n")
    lines.append("|---|---:|---:|---:|---:|---:|\n")
    for row in quant["splits"]:
        lines.append(
            f"| {row['split']} | {row['n']} | {_pct(row['prediction_agreement_rate'])} "
            f"| {row['prediction_mismatch_count']} | {_pct(row['top3_ordered_match_rate'])} "
            f"| {_f(row['mean_top3_overlap_count'])} |\n"
        )

    lines.append("\n## Exact SHAP Ranking Margin\n\n")
    lines.append("Rank-3 vs rank-4 margin for the verified quantized Exact SHAP relation.\n\n")
    lines.append("| Split | n | min margin | p5 margin | median margin | <=0.001 rate | <=0.01 rate |\n")
    lines.append("|---|---:|---:|---:|---:|---:|---:|\n")
    for row in margin["splits"]:
        stats = row["margin_scaled_stats"]
        small = row["small_margin_thresholds_scaled"]
        lines.append(
            f"| {row['split']} | {row['n']} | {_f(stats['min'])} | {_f(stats['p5'])} | {_f(stats['median'])} "
            f"| {_pct(small['0.001']['rate'])} | {_pct(small['0.01']['rate'])} |\n"
        )

    lines.append("\n## File-wise Holdout Robustness\n\n")
    lines.append(
        "Supplementary robustness check from `filewise_holdout.json`. This is a file-wise split by source CSV number, "
        "not a true timestamp-ordered temporal deployment simulation.\n\n"
    )
    holdout = filewise["holdout"]
    summary = filewise["data_summary"]
    lines.append(f"- Held-out files: `{', '.join(holdout['holdout_files'])}`\n")
    lines.append(
        f"- Sample fraction: `{filewise['meta']['sample_frac']}`, train/val cap: `{filewise['meta']['max_train_rows']}`, "
        f"holdout n: `{summary['holdout']['n']}`, holdout attack rate: `{summary['holdout']['attack_pct']:.4f}%`.\n\n"
    )
    lines.append("| Point | Threshold | Attack Recall | Normal Recall/Spec | FPR | MCC | Confusion tn/fp/fn/tp |\n")
    lines.append("|---|---:|---:|---:|---:|---:|---|\n")
    for point in ["default_0.5", "low_fpr", "balanced_mcc", "high_recall"]:
        block = filewise["operating_points"][point]
        metrics = block["metrics"]
        lines.append(
            f"| {point} | {_f(block['threshold'])} | {_f(metrics['attack_recall'])} "
            f"| {_f(metrics['normal_recall_specificity'])} | {_f(metrics['fpr'])} "
            f"| {_f(metrics['mcc'])} | {_conf(block['confusion'])} |\n"
        )

    lines.append("\n## Attack-Type Error Analysis\n\n")
    lines.append(
        "`type` is excluded from training and used only as post-hoc metadata. Rows below show the highest-FN-rate "
        "attack type for each model and operating point among attack types meeting the report support threshold.\n\n"
    )
    lines.append(f"- Metadata/test label alignment mismatches: `{attack_types['meta']['label_mismatch_count']}`.\n")
    lines.append(f"- Minimum attack-type support: `{attack_types['meta']['min_count']}` true attack rows.\n\n")
    lines.append("| Model | Point | Worst attack type | n | FN | Attack recall | FN rate |\n")
    lines.append("|---|---|---|---:|---:|---:|---:|\n")
    for model_name in ["xgboost", "logistic_regression"]:
        model = attack_types["models"][model_name]
        for point in ["default_0.5", "balanced_mcc", "low_fpr", "high_recall"]:
            rows = model["attack_type_errors"][point]
            if not rows:
                continue
            row = rows[0]
            lines.append(
                f"| {model_name} | {point} | {row['attack_type']} | {row['n']} | {row['fn']} "
                f"| {_f(row['attack_recall'])} | {_f(row['fn_rate'])} |\n"
            )

    lines.append("\n## Stage 3.4 Exact SHAP Proof Evidence\n\n")
    stats = stage34["circuit_stats"]
    sizes = stage34["artifact_sizes"]
    sample_label = _sample_label(stage34)
    lines.append("| Metric | Value | Source |\n|---|---:|---|\n")
    lines.append(f"| Constraints | {stats['constraints']} | `STAGE34_PROOF_REPORT.md` |\n")
    lines.append(f"| Wires | {stats['wires']} | `STAGE34_PROOF_REPORT.md` |\n")
    lines.append(f"| Public inputs | {stats['public_inputs']} | `STAGE34_PROOF_REPORT.md` |\n")
    lines.append(f"| Private inputs | {stats['private_inputs']} | `STAGE34_PROOF_REPORT.md` |\n")
    lines.append(f"| R1CS bytes | {sizes['r1cs_bytes']} | `STAGE34_PROOF_REPORT.md` |\n")
    lines.append(f"| WASM bytes | {sizes['wasm_bytes']} | `STAGE34_PROOF_REPORT.md` |\n")
    lines.append(f"| ZKey bytes | {sizes['zkey_bytes']} | `STAGE34_PROOF_REPORT.md` |\n")
    lines.append(f"| Verification key bytes | {sizes['vkey_bytes']} | `STAGE34_PROOF_REPORT.md` |\n")
    lines.append(f"| Witness ms, {sample_label} | {_range_mean(_durations(stage34, 'witness_sample_'))} | `STAGE34_PROOF_REPORT.md` |\n")
    lines.append(f"| Prove ms, {sample_label} | {_range_mean(_durations(stage34, 'prove_sample_'))} | `STAGE34_PROOF_REPORT.md` |\n")
    lines.append(f"| Verify ms, {sample_label} | {_range_mean(_durations(stage34, 'verify_sample_'))} | `STAGE34_PROOF_REPORT.md` |\n")
    lines.append(f"| Proof bytes, {sample_label} | {_range_mean(_sizes(stage34, 'proof_bytes'))} | `STAGE34_PROOF_REPORT.md` |\n")
    lines.append(f"| Public bytes, {sample_label} | {_range_mean(_sizes(stage34, 'public_bytes'))} | `STAGE34_PROOF_REPORT.md` |\n")

    lines.append("\n## Stage 3.4 Registry Digest\n\n")
    lines.append(f"- Current approved combined digest: `{registry['combined_sha256']}`\n")
    lines.append("- Policy verifier: `python tools/verify_stage34_policy.py --self-test` and `python tools/verify_stage34_policy.py`.\n")
    lines.append("- Do not mix this digest with older verification keys or pre-rebuild Stage 3.4 reports.\n\n")

    if stage35:
        lines.append("## Stage 3.5 Input-Commitment Appendix\n\n")
        lines.append(
            "Appendix-only evidence from `stage3_zk/reports/STAGE35_INPUT_COMMITMENT_REPORT.md`. "
            "This prototype adds a public Poseidon commitment to the private input witness and simulated event metadata. "
            "It demonstrates feasibility of a commitment check, but full provenance still requires an external trusted commitment registry.\n\n"
        )
        stats35 = stage35["circuit_stats"]
        sample_label35 = _sample_label(stage35)
        tamper_samples = []
        for result in stage35.get("sample_results", []):
            ok = any(
                str(step.get("step", "")).startswith("verify_tampered_commitment")
                and step.get("status") == "PASS"
                for step in result.get("steps", [])
            )
            if ok:
                tamper_samples.append(str(result.get("sample")))
        base_constraints = stage35.get("stage34_baseline", {}).get("constraints")
        overhead = ""
        if base_constraints:
            overhead = f"{round(float(stats35['constraints']) / float(base_constraints), 1)}x"
        lines.append("| Metric | Value | Source |\n|---|---:|---|\n")
        lines.append(f"| Constraints | {stats35['constraints']} | `STAGE35_INPUT_COMMITMENT_REPORT.md` |\n")
        lines.append(f"| Wires | {stats35['wires']} | `STAGE35_INPUT_COMMITMENT_REPORT.md` |\n")
        lines.append(f"| Public inputs | {stats35['public_inputs']} | `STAGE35_INPUT_COMMITMENT_REPORT.md` |\n")
        lines.append(f"| Private inputs | {stats35['private_inputs']} | `STAGE35_INPUT_COMMITMENT_REPORT.md` |\n")
        lines.append(f"| Public outputs | {stats35.get('outputs', '')} | `STAGE35_INPUT_COMMITMENT_REPORT.md` |\n")
        lines.append(f"| Constraint overhead vs Stage 3.4 | {overhead} | `STAGE35_INPUT_COMMITMENT_REPORT.md` |\n")
        lines.append(f"| Witness ms, {sample_label35} | {_range_mean(_durations(stage35, 'witness_sample_'))} | `STAGE35_INPUT_COMMITMENT_REPORT.md` |\n")
        lines.append(f"| Prove ms, {sample_label35} | {_range_mean(_durations(stage35, 'prove_sample_'))} | `STAGE35_INPUT_COMMITMENT_REPORT.md` |\n")
        lines.append(f"| Verify ms, {sample_label35} | {_range_mean(_durations(stage35, 'verify_sample_'))} | `STAGE35_INPUT_COMMITMENT_REPORT.md` |\n")
        lines.append(f"| Tampered public commitment | rejected for samples {', '.join(tamper_samples)} | `STAGE35_INPUT_COMMITMENT_REPORT.md` |\n\n")

    lines.append("## Historical Or Appendix-Only Numbers\n\n")
    lines.append("- Older Node API timing artifacts under `stage3_zk/outputs/proofs/` and `stage3_zk/reports/bench/` should be labelled historical if cited.\n")
    lines.append("- `stage3_zk/reports/STAGE34_EXACT_SHAP_SUMMARY.md` is an implementation status summary; use `STAGE34_PROOF_REPORT.md` for current proof timings.\n")
    if stage35:
        lines.append("- Stage 3.5 input commitment numbers are appendix-only; cite them as a feasibility prototype, not as the main system baseline.\n")
    lines.append("- `drift_chunks.md` is a drift/robustness proxy over ordered random-test chunks, not a true temporal holdout.\n")
    lines.append("- `filewise_holdout.md` is a source-file robustness check; cite it as file-wise holdout, not timestamp validation.\n")

    out = REPORTS / "final_numbers_source_of_truth.md"
    out.write_text("".join(lines), encoding="utf-8")
    print(f"Wrote: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
