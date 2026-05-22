#!/usr/bin/env python
"""Replication runner (thesis-oriented).

This is a *single entrypoint* for reproducibility tasks:
- Validate artifact invariants (feature count/order consistency)
- Run ZK Stage 3 tests (via stage3_zk/scripts/run_stage3_tests.py)

It intentionally defaults to Stage 3 checks because Stage 1/2 notebook execution
can be expensive (multi-million row data). You can still extend this script to
run notebooks with papermill if you want full pipeline automation.

Usage (from repo root):
  python tools/reproduce.py check
    python tools/reproduce.py metrics
    python tools/reproduce.py eval
    python tools/reproduce.py drift
  python tools/reproduce.py zk --stage all --samples 1,2,3
  python tools/reproduce.py zk --stage 33 --build

Exit code: 0 on success; 1 on failure.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from typing import List, Sequence


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
STAGE3_ZK_DIR = os.path.join(REPO_ROOT, "stage3_zk")


@dataclass
class Check:
    name: str
    ok: bool
    details: str = ""


def _read_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _exists(path: str) -> bool:
    return os.path.exists(path)


def check_artifacts() -> List[Check]:
    checks: List[Check] = []

    # ML-side frozen features
    feature_schema = os.path.join(REPO_ROOT, "outputs", "preprocess", "feature_schema.json")
    feature_names = os.path.join(REPO_ROOT, "outputs", "preprocess", "feature_names.json")
    feature_order = os.path.join(REPO_ROOT, "outputs", "processed", "feature_order.json")

    # ZK-side frozen artifacts
    zk_model = os.path.join(STAGE3_ZK_DIR, "artifacts", "model_public.json")
    zk_group = os.path.join(STAGE3_ZK_DIR, "artifacts", "group_map.json")
    zk_feature_order = os.path.join(STAGE3_ZK_DIR, "artifacts", "feature_order.json")

    required = [feature_schema, feature_names, feature_order, zk_model, zk_group, zk_feature_order]
    missing = [p for p in required if not _exists(p)]
    if missing:
        checks.append(Check("required_files_present", False, "Missing: " + ", ".join(missing)))
        return checks

    schema = _read_json(feature_schema)
    names = _read_json(feature_names)
    order = _read_json(feature_order)

    model = _read_json(zk_model)
    group = _read_json(zk_group)
    zk_order = _read_json(zk_feature_order)

    # Feature count consistency
    expected_n = int(schema.get("final_feature_count", -1))
    checks.append(Check("feature_schema_final_feature_count_is_104", expected_n == 104, f"final_feature_count={expected_n}"))

    checks.append(Check("feature_names_len_matches_schema", len(names) == expected_n, f"len(feature_names)={len(names)}, n={expected_n}"))
    checks.append(Check("feature_order_len_matches_schema", len(order) == expected_n, f"len(feature_order)={len(order)}, n={expected_n}"))

    checks.append(Check("zk_model_n_matches_schema", int(model.get("n", -1)) == expected_n, f"model.n={model.get('n')}"))
    checks.append(Check("zk_group_n_features_matches_schema", int(group.get("n_features", -1)) == expected_n, f"group_map.n_features={group.get('n_features')}"))

    # Order consistency: output feature_names/order must match ZK feature_order
    checks.append(Check("zk_feature_order_len_matches_schema", len(zk_order) == expected_n, f"len(zk_feature_order)={len(zk_order)}"))

    same_order = (list(names) == list(order) == list(zk_order))
    checks.append(Check("feature_order_is_identical_across_ml_and_zk", same_order, "Expected outputs/preprocess/feature_names.json == outputs/processed/feature_order.json == stage3_zk/artifacts/feature_order.json"))

    # Group map length consistency
    idx_to_gid = group.get("feature_index_to_group_id", [])
    checks.append(Check("group_map_index_length_matches_n", len(idx_to_gid) == expected_n, f"len(feature_index_to_group_id)={len(idx_to_gid)}, n={expected_n}"))

    return checks


def run_zk_tests(
    stage: str,
    samples: str,
    build: bool,
    *,
    no_witness_smoke: bool,
    validate_proofs: bool,
    clean: bool,
    prove: bool,
    verify: bool,
    report: bool,
    report_dir: str | None,
    report_prefix: str | None,
) -> int:
    harness = os.path.join(STAGE3_ZK_DIR, "scripts", "run_stage3_tests.py")
    if not os.path.exists(harness):
        print(f"Missing ZK harness: {harness}")
        return 1

    cmd = [sys.executable, harness, "--stage", stage, "--samples", samples]
    if build:
        cmd.append("--build")
    if clean:
        cmd.append("--clean")
    if no_witness_smoke:
        cmd.append("--no-witness-smoke")
    if prove:
        cmd.append("--prove")
    if verify:
        cmd.append("--verify")
    if validate_proofs:
        cmd.append("--validate-proofs")

    if report:
        cmd.append("--report")
        if report_dir:
            cmd.extend(["--report-dir", report_dir])
        if report_prefix:
            cmd.extend(["--report-prefix", report_prefix])

    proc = subprocess.run(cmd, cwd=STAGE3_ZK_DIR)
    return int(proc.returncode)


def run_baseline_metrics(*, criterion: str, tune_on: str) -> int:
    script = os.path.join(REPO_ROOT, "tools", "baseline_metrics.py")
    if not os.path.exists(script):
        print(f"Missing baseline metrics script: {script}")
        return 1

    cmd = [sys.executable, script, "--criterion", criterion, "--tune-on", tune_on]
    proc = subprocess.run(cmd, cwd=REPO_ROOT)
    return int(proc.returncode)


def run_decision_eval(*, low_fpr: float, high_recall: float, ece_bins: int) -> int:
    script = os.path.join(REPO_ROOT, "tools", "eval_decision_engineering.py")
    if not os.path.exists(script):
        print(f"Missing decision-eval script: {script}")
        return 1

    cmd = [
        sys.executable,
        script,
        "--low-fpr",
        str(low_fpr),
        "--high-recall",
        str(high_recall),
        "--ece-bins",
        str(ece_bins),
    ]
    proc = subprocess.run(cmd, cwd=REPO_ROOT)
    return int(proc.returncode)


def run_drift_eval(*, chunks: int) -> int:
    script = os.path.join(REPO_ROOT, "tools", "eval_drift_chunks.py")
    if not os.path.exists(script):
        print(f"Missing drift-eval script: {script}")
        return 1

    cmd = [sys.executable, script, "--chunks", str(int(chunks))]
    proc = subprocess.run(cmd, cwd=REPO_ROOT)
    return int(proc.returncode)


def run_semantic_group_ablation() -> int:
    script = os.path.join(REPO_ROOT, "tools", "eval_semantic_group_ablation.py")
    if not os.path.exists(script):
        print(f"Missing semantic-group ablation script: {script}")
        return 1

    cmd = [sys.executable, script]
    proc = subprocess.run(cmd, cwd=REPO_ROOT)
    return int(proc.returncode)


def run_zk_scaling_benchmark(*, stage: str, sample: int, runs: int, warmup: int, clean_first: bool) -> int:
    script = os.path.join(REPO_ROOT, "tools", "eval_zk_scaling_benchmark.py")
    if not os.path.exists(script):
        print(f"Missing ZK scaling benchmark script: {script}")
        return 1

    cmd = [
        sys.executable,
        script,
        "--stage",
        str(stage),
        "--sample",
        str(int(sample)),
        "--runs",
        str(int(runs)),
        "--warmup",
        str(int(warmup)),
    ]
    if clean_first:
        cmd.append("--clean-first")

    proc = subprocess.run(cmd, cwd=REPO_ROOT)
    return int(proc.returncode)


def run_zk_stage34(*, samples: str, force_setup: bool) -> int:
    script = os.path.join(STAGE3_ZK_DIR, "scripts", "stage 3.4", "04_run_phase_c_stage34.py")
    if not os.path.exists(script):
        print(f"Missing Stage 3.4 runner: {script}")
        return 1

    cmd = [sys.executable, script, "--samples", str(samples)]
    if force_setup:
        cmd.append("--force-setup")

    proc = subprocess.run(cmd, cwd=REPO_ROOT)
    return int(proc.returncode)


def run_cost_based_thresholds(*, ratios: str) -> int:
    script = os.path.join(REPO_ROOT, "tools", "eval_cost_based_thresholds.py")
    if not os.path.exists(script):
        print(f"Missing cost-based threshold script: {script}")
        return 1

    cmd = [sys.executable, script, "--ratios", str(ratios)]
    proc = subprocess.run(cmd, cwd=REPO_ROOT)
    return int(proc.returncode)


def run_all_eval(
    *,
    criterion: str,
    tune_on: str,
    low_fpr: float,
    high_recall: float,
    ece_bins: int,
    chunks: int,
    ratios: str,
    include_zk_scale: bool,
    zk_stage: str,
    zk_sample: int,
    zk_runs: int,
    zk_warmup: int,
    zk_clean_first: bool,
) -> int:
    steps = [
        ("metrics", lambda: run_baseline_metrics(criterion=criterion, tune_on=tune_on)),
        ("eval", lambda: run_decision_eval(low_fpr=low_fpr, high_recall=high_recall, ece_bins=ece_bins)),
        ("drift", lambda: run_drift_eval(chunks=chunks)),
        ("semantic-groups", run_semantic_group_ablation),
        ("cost", lambda: run_cost_based_thresholds(ratios=ratios)),
    ]

    if include_zk_scale:
        steps.append(
            (
                "zk-scale",
                lambda: run_zk_scaling_benchmark(
                    stage=zk_stage,
                    sample=zk_sample,
                    runs=zk_runs,
                    warmup=zk_warmup,
                    clean_first=zk_clean_first,
                ),
            )
        )

    print("=" * 78)
    print("ALL-EVAL PACK")
    print("=" * 78)
    for name, fn in steps:
        print(f"\n>>> Running: {name}")
        rc = int(fn())
        if rc != 0:
            print(f"\n❌ all-eval failed at step '{name}' (exit={rc}).")
            return rc
    print("\n✅ all-eval completed successfully.")
    return 0


def _print_checks(checks: Sequence[Check]) -> None:
    failures = [c for c in checks if not c.ok]

    print("=" * 78)
    print("REPRODUCIBILITY CHECKS")
    print("=" * 78)

    for c in checks:
        status = "PASS" if c.ok else "FAIL"
        suffix = f" — {c.details}" if c.details else ""
        print(f"[{status}] {c.name}{suffix}")

    if failures:
        print("\nSome checks failed. Fix the above issues before claiming full reproducibility.")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("check", help="Validate artifact invariants (104 features, consistent ordering, etc).")

    metrics = sub.add_parser(
        "metrics",
        help="Generate imbalance-aware baseline metrics + threshold tuning (writes JSON+MD reports).",
    )
    metrics.add_argument("--criterion", default="mcc", choices=["mcc", "bacc"], help="Threshold tuning criterion.")
    metrics.add_argument("--tune-on", default="val", choices=["val", "test"], help="Tune threshold on val or test split.")

    ev = sub.add_parser(
        "eval",
        help="Decision-engineering evaluation: tradeoff curves + operating points + calibration (writes figures + MD report).",
    )
    ev.add_argument("--low-fpr", type=float, default=0.01, help="Low-FPR operating point target (validation).")
    ev.add_argument("--high-recall", type=float, default=0.995, help="High-recall operating point target (validation).")
    ev.add_argument("--ece-bins", type=int, default=15, help="Bins for ECE / reliability diagram.")

    drift = sub.add_parser(
        "drift",
        help="Drift/robustness check: metric stability over ordered test chunks (writes figures + MD report).",
    )
    drift.add_argument("--chunks", type=int, default=20, help="Number of contiguous test chunks.")

    sub.add_parser(
        "semantic-groups",
        help="Semantic-group ablation: compare raw group frequency vs size-normalized frequency (writes figures + MD report).",
    )

    zk_scale = sub.add_parser(
        "zk-scale",
        help="ZK scaling benchmark: repeated witness/prove/verify timings with p50/p95 summary (writes JSON+MD under stage3_zk/reports).",
    )
    zk_scale.add_argument("--stage", default="33", choices=["31", "32", "33"], help="Which Stage 3 circuit to benchmark.")
    zk_scale.add_argument("--sample", type=int, default=1, choices=[1, 2, 3], help="Which test sample to benchmark.")
    zk_scale.add_argument("--runs", type=int, default=30, help="Total number of runs (including warmup).")
    zk_scale.add_argument("--warmup", type=int, default=2, help="Warmup runs excluded from stats.")
    zk_scale.add_argument("--clean-first", action="store_true", help="Clean outputs on the first iteration (slower).")

    zk_stage34 = sub.add_parser(
        "zk-stage34",
        help="Run Stage 3.4 Exact SHAP Groth16 setup/prove/verify evidence runner.",
    )
    zk_stage34.add_argument(
        "--samples",
        nargs="+",
        default=["1,2,3"],
        help="Stage 3 test sample IDs. Accepts '1,2,3' or PowerShell-split '1 2 3'.",
    )
    zk_stage34.add_argument("--force-setup", action="store_true", help="Regenerate Stage 3.4 zkey and verification key.")

    cost = sub.add_parser(
        "cost",
        help="Cost-based threshold selection: sweep FN/FP cost ratios and choose thresholds by minimizing validation cost (writes JSON+MD + figures).",
    )
    cost.add_argument(
        "--ratios",
        default="0.25,0.5,1,2,5,10,20,50,100",
        help="Comma-separated FN/FP ratios (C_FP=1, C_FN=ratio).",
    )

    all_eval = sub.add_parser(
        "all-eval",
        help=(
            "Run the full evaluation pack: metrics, eval, drift, semantic-groups, cost "
            "(optionally zk-scale)."
        ),
    )
    all_eval.add_argument("--criterion", default="mcc", choices=["mcc", "bacc"], help="Threshold tuning criterion for metrics.")
    all_eval.add_argument("--tune-on", default="val", choices=["val", "test"], help="Tune threshold on val or test split (metrics only).")
    all_eval.add_argument("--low-fpr", type=float, default=0.01, help="Low-FPR operating point target (validation).")
    all_eval.add_argument("--high-recall", type=float, default=0.995, help="High-recall operating point target (validation).")
    all_eval.add_argument("--ece-bins", type=int, default=15, help="Bins for ECE / reliability diagram.")
    all_eval.add_argument("--chunks", type=int, default=20, help="Number of contiguous test chunks (drift).")
    all_eval.add_argument(
        "--ratios",
        default="0.25,0.5,1,2,5,10,20,50,100",
        help="Comma-separated FN/FP ratios for cost-based thresholds (quote this string in PowerShell).",
    )
    all_eval.add_argument("--include-zk-scale", action="store_true", help="Also run the ZK scaling benchmark (slower).")
    all_eval.add_argument("--zk-stage", default="33", choices=["31", "32", "33"], help="ZK benchmark stage.")
    all_eval.add_argument("--zk-sample", type=int, default=1, choices=[1, 2, 3], help="ZK benchmark sample.")
    all_eval.add_argument("--zk-runs", type=int, default=30, help="ZK benchmark total runs.")
    all_eval.add_argument("--zk-warmup", type=int, default=2, help="ZK benchmark warmup runs excluded.")
    all_eval.add_argument("--zk-clean-first", action="store_true", help="Clean ZK outputs on first benchmark iteration.")

    zk = sub.add_parser("zk", help="Run ZK Stage 3 test harness.")
    zk.add_argument("--stage", default="all", choices=["31", "32", "33", "all"])
    zk.add_argument("--samples", default="1,2,3")
    zk.add_argument("--build", action="store_true")
    zk.add_argument(
        "--no-witness-smoke",
        action="store_true",
        help="Skip witness-generation smoke tests (useful if circuits are not built).",
    )
    zk.add_argument(
        "--validate-proofs",
        action="store_true",
        help="Validate existing Stage 3.3 public signals under stage3_zk/outputs/proofs (opt-in).",
    )
    zk.add_argument("--clean", action="store_true", help="Clean generated ZK outputs before running.")
    zk.add_argument("--prove", action="store_true", help="Generate Groth16 proofs for correct inputs.")
    zk.add_argument("--verify", action="store_true", help="Verify generated Groth16 proofs (implies --prove).")
    zk.add_argument("--report", action="store_true", help="Write a JSON+MD evidence report under stage3_zk/reports.")
    zk.add_argument("--report-dir", default=None, help="Override report output directory.")
    zk.add_argument("--report-prefix", default=None, help="Override report filename prefix.")

    args = parser.parse_args(argv)

    if args.cmd == "check":
        checks = check_artifacts()
        _print_checks(checks)
        return 0 if all(c.ok for c in checks) else 1

    if args.cmd == "semantic-groups":
        return run_semantic_group_ablation()

    if args.cmd == "metrics":
        return run_baseline_metrics(criterion=str(args.criterion), tune_on=str(args.tune_on))

    if args.cmd == "eval":
        return run_decision_eval(low_fpr=float(args.low_fpr), high_recall=float(args.high_recall), ece_bins=int(args.ece_bins))

    if args.cmd == "drift":
        return run_drift_eval(chunks=int(args.chunks))

    if args.cmd == "zk-scale":
        return run_zk_scaling_benchmark(
            stage=str(args.stage),
            sample=int(args.sample),
            runs=int(args.runs),
            warmup=int(args.warmup),
            clean_first=bool(args.clean_first),
        )

    if args.cmd == "zk-stage34":
        samples = ",".join(str(x) for x in args.samples)
        return run_zk_stage34(samples=samples, force_setup=bool(args.force_setup))

    if args.cmd == "cost":
        return run_cost_based_thresholds(ratios=str(args.ratios))

    if args.cmd == "all-eval":
        return run_all_eval(
            criterion=str(args.criterion),
            tune_on=str(args.tune_on),
            low_fpr=float(args.low_fpr),
            high_recall=float(args.high_recall),
            ece_bins=int(args.ece_bins),
            chunks=int(args.chunks),
            ratios=str(args.ratios),
            include_zk_scale=bool(args.include_zk_scale),
            zk_stage=str(args.zk_stage),
            zk_sample=int(args.zk_sample),
            zk_runs=int(args.zk_runs),
            zk_warmup=int(args.zk_warmup),
            zk_clean_first=bool(args.zk_clean_first),
        )

    if args.cmd == "zk":
        return run_zk_tests(
            stage=args.stage,
            samples=args.samples,
            build=args.build,
            no_witness_smoke=bool(args.no_witness_smoke),
            validate_proofs=bool(args.validate_proofs),
            clean=bool(args.clean),
            prove=bool(args.prove),
            verify=bool(args.verify),
            report=bool(args.report),
            report_dir=(str(args.report_dir) if args.report_dir else None),
            report_prefix=(str(args.report_prefix) if args.report_prefix else None),
        )

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
