#!/usr/bin/env python
"""Exact SHAP over semantic feature groups for the ZK-XIDS Logistic Regression model.

This script treats the five semantic groups as SHAP players and enumerates all
coalitions exactly. Exact SHAP is computed outside the ZK circuit. The existing
grouped linear attribution, sum_g |w_i * x_i|, is kept as an engineering
baseline for comparison with the current Stage 3.2/3.3 circuits.
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import os
import warnings
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

import joblib
import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
GROUPS_DEFAULT = ["Protocol", "Application", "ConnectionState", "Ports", "TrafficVolume"]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _read_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _load_feature_names(path: Path) -> List[str]:
    names = _read_json(path)
    if not isinstance(names, list) or not names:
        raise ValueError(f"Invalid feature-name file: {path}")
    return [str(x) for x in names]


def _load_group_map(path: Path, n_features: int) -> Tuple[List[str], np.ndarray]:
    group_map = _read_json(path)
    groups = list(group_map.get("groups") or GROUPS_DEFAULT)
    group_ids = np.asarray(group_map.get("feature_index_to_group_id"), dtype=np.int32)

    if group_ids.shape[0] != n_features:
        raise ValueError(f"group_map has {group_ids.shape[0]} features, expected {n_features}")
    if int(group_map.get("n_groups", len(groups))) != len(groups):
        raise ValueError("group_map.n_groups does not match len(groups)")
    if sorted(set(group_ids.tolist())) != list(range(1, len(groups) + 1)):
        raise ValueError("group ids must be contiguous 1..n_groups")

    return groups, group_ids


def _load_lr_model(path: Path):
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="Trying to unpickle estimator")
        return joblib.load(path)


def _select_stage2_subset(
    *,
    X_test: np.ndarray,
    y_test: np.ndarray | None,
    model,
    random_state: int,
    stage2_tp: int,
    stage2_fn: int,
    fallback_n: int,
) -> Tuple[np.ndarray, str]:
    """Reconstruct the Stage 2 subset when labels and LR predictions are available."""

    if y_test is not None:
        try:
            y_pred = np.asarray(model.predict(X_test), dtype=np.int64)
            y_arr = np.asarray(y_test, dtype=np.int64)

            tp_idx = np.where((y_arr == 1) & (y_pred == 1))[0]
            fn_idx = np.where((y_arr == 1) & (y_pred == 0))[0]

            rng = np.random.default_rng(random_state)
            n_tp = min(int(stage2_tp), len(tp_idx))
            n_fn = min(int(stage2_fn), len(fn_idx))
            if n_tp + n_fn > 0:
                tp_sample = rng.choice(tp_idx, size=n_tp, replace=False) if n_tp else np.array([], dtype=np.int64)
                fn_sample = rng.choice(fn_idx, size=n_fn, replace=False) if n_fn else np.array([], dtype=np.int64)
                selected = np.unique(np.concatenate([tp_sample, fn_sample])).astype(np.int64)
                return selected, f"reconstructed_stage2_lr_tp{n_tp}_fn{n_fn}_seed{random_state}"
        except Exception as exc:
            print(f"Stage 2 subset reconstruction failed; falling back to random subset. Reason: {exc}")

    n = min(int(fallback_n), int(X_test.shape[0]))
    rng = np.random.default_rng(random_state)
    selected = np.sort(rng.choice(np.arange(X_test.shape[0]), size=n, replace=False)).astype(np.int64)
    return selected, f"fallback_random_test_n{n}_seed{random_state}"


def _group_masks(group_ids: np.ndarray, n_groups: int) -> List[np.ndarray]:
    return [group_ids == gid for gid in range(1, n_groups + 1)]


def _score_deltas_by_group(
    X: np.ndarray,
    w: np.ndarray,
    x_ref: np.ndarray,
    masks: Sequence[np.ndarray],
) -> np.ndarray:
    """Return per-sample group score deltas relative to the reference vector."""

    deltas = np.zeros((X.shape[0], len(masks)), dtype=np.float64)
    for j, mask in enumerate(masks):
        deltas[:, j] = (np.asarray(X[:, mask], dtype=np.float64) - x_ref[mask]) @ w[mask]
    return deltas


def _exact_group_shap_from_deltas(deltas: np.ndarray, base_score: float) -> np.ndarray:
    """Enumerate all semantic-group coalitions and compute exact SHAP values."""

    n_samples, m = deltas.shape
    phi = np.zeros((n_samples, m), dtype=np.float64)
    players = list(range(m))
    m_factorial = math.factorial(m)

    for g in players:
        others = [p for p in players if p != g]
        for r in range(m):
            weight = math.factorial(r) * math.factorial(m - r - 1) / m_factorial
            for coalition in itertools.combinations(others, r):
                if coalition:
                    score_without = base_score + deltas[:, coalition].sum(axis=1)
                else:
                    score_without = np.full(n_samples, base_score, dtype=np.float64)
                score_with = score_without + deltas[:, g]
                phi[:, g] += weight * (score_with - score_without)

    return phi


def _old_grouped_linear_attribution(X: np.ndarray, w: np.ndarray, masks: Sequence[np.ndarray]) -> np.ndarray:
    feature_attr = np.abs(np.asarray(X, dtype=np.float64) * w.reshape(1, -1))
    out = np.zeros((X.shape[0], len(masks)), dtype=np.float64)
    for j, mask in enumerate(masks):
        out[:, j] = feature_attr[:, mask].sum(axis=1)
    return out


def _conservative_phi_bound(w_int: np.ndarray, group_ids: np.ndarray, max_abs_x_int: int, max_abs_x_ref_int: int) -> int:
    """Conservative integer bound for phi_g = sum_i w_i * (x_i - x_ref_i)."""

    max_abs_diff = int(max_abs_x_int) + int(max_abs_x_ref_int)
    max_by_group = 0
    for gid in sorted(set(int(x) for x in group_ids.tolist())):
        mask = group_ids == gid
        bound = int(np.sum(np.abs(w_int[mask]).astype(object)) * max_abs_diff)
        max_by_group = max(max_by_group, bound)
    return int(max_by_group)


def _write_reference_artifact(
    *,
    out_path: Path,
    created_utc: str,
    x_ref: np.ndarray,
    model_public: Dict,
    group_ids: np.ndarray,
    bounds: Dict,
) -> Dict[str, object]:
    sx = int(model_public["Sx"])
    sw = int(model_public["Sw"])
    w_int = np.asarray(model_public["w_int"], dtype=np.int64)
    x_ref_int = np.rint(x_ref * sx).astype(np.int64)
    max_abs_x_ref_int = int(np.max(np.abs(x_ref_int)))
    conservative_max_abs_phi_int = _conservative_phi_bound(
        w_int=w_int,
        group_ids=group_ids,
        max_abs_x_int=int(bounds["max_abs_x_int"]),
        max_abs_x_ref_int=max_abs_x_ref_int,
    )

    payload: Dict[str, object] = {
        "created_utc": created_utc,
        "n": int(x_ref_int.shape[0]),
        "Sx": sx,
        "Sw": sw,
        "source": "feature-wise training-set mean in processed feature space",
        "x_ref": [float(x) for x in x_ref.tolist()],
        "x_ref_int": [int(x) for x in x_ref_int.tolist()],
        "max_abs_x_ref_int": max_abs_x_ref_int,
        "conservative_max_abs_phi_int": conservative_max_abs_phi_int,
        "scaling_notes": "x_ref_int = round(x_ref * Sx); phi_g_int = sum_i w_int[i] * (x_int[i] - x_ref_int[i]); scale is Sx*Sw.",
    }

    _ensure_parent(out_path)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def _topk_groups(values: np.ndarray, groups: Sequence[str], *, k: int, use_abs: bool) -> Tuple[List[int], List[str]]:
    sortable = []
    for j, val in enumerate(values):
        rank_value = abs(float(val)) if use_abs else float(val)
        sortable.append((-rank_value, j + 1, groups[j]))
    sortable.sort()
    ids = [gid for _, gid, _ in sortable[:k]]
    names = [name for _, _, name in sortable[:k]]
    return ids, names


def _jaccard(a: Iterable[int], b: Iterable[int]) -> float:
    sa, sb = set(a), set(b)
    return float(len(sa & sb) / len(sa | sb)) if sa or sb else 1.0


def _format_top(items: Sequence[str]) -> str:
    return ";".join(items)


def _frequency(top3_rows: Sequence[Sequence[str]], groups: Sequence[str]) -> Dict[str, int]:
    counter: Counter[str] = Counter()
    for row in top3_rows:
        counter.update(row)
    return {g: int(counter.get(g, 0)) for g in groups}


def _write_exact_report(
    *,
    out_md: Path,
    created_utc: str,
    args: argparse.Namespace,
    csv_path: Path,
    n_samples: int,
    subset_source: str,
    groups: Sequence[str],
    group_sizes: Sequence[int],
    mean_abs_phi: Sequence[float],
    mean_old_attr: Sequence[float],
    exact_freq: Dict[str, int],
    old_freq: Dict[str, int],
    mean_overlap_count: float,
    mean_overlap_jaccard: float,
    additivity_error_max: float,
    score_diff_max: float,
    closed_form_diff_max: float,
    reference_artifact_path: Path,
    reference_payload: Dict[str, object],
) -> None:
    lines: List[str] = []
    lines.append("# Semantic-Group Exact SHAP Results\n\n")
    lines.append(f"Generated: {created_utc} (UTC)\n\n")
    lines.append("## Scope\n\n")
    lines.append(
        "This evaluation computes semantic-group Exact SHAP for the public Logistic Regression model and "
        "compares it with the older grouped linear attribution proxy. The same closed-form Exact SHAP "
        "relation is now verified by the Stage 3.4 Circom/Groth16 circuit for the fixed public LR model "
        "under private input features.\n\n"
    )
    lines.append("For group `g`, with `m=5` semantic groups, the script computes:\n\n")
    lines.append("```text\n")
    lines.append("phi_g(x) = sum_{S subseteq G \\ {g}} |S|! (m-|S|-1)! / m! * (v_x(S union {g}) - v_x(S))\n")
    lines.append("```\n\n")
    lines.append(
        "Here `v_x(S)` is the Logistic Regression score/logit after keeping groups in `S` from `x` and "
        "replacing all removed groups with `x_ref`.\n\n"
    )
    lines.append("## Configuration\n\n")
    lines.append(f"- Model: Logistic Regression (`{args.model}`)\n")
    lines.append("- Value function: model score/logit, not probability\n")
    lines.append("- Reference vector: feature-wise training-set mean in processed feature space\n")
    lines.append(f"- Quantized reference artifact: `{reference_artifact_path.as_posix()}`\n")
    lines.append(f"- Subset: `{subset_source}` ({n_samples} samples)\n")
    lines.append(f"- Output CSV: `{csv_path.as_posix()}`\n")
    lines.append("- SHAP players: five semantic groups\n")
    lines.append("- Exact SHAP top-3 ranking: descending absolute SHAP value, preserving signed SHAP columns\n")
    lines.append("- Engineering baseline: grouped `sum_i |w_i * x_i|`, matching the current Stage 2/3 attribution family\n\n")

    lines.append("## Group Summary\n\n")
    lines.append("| Group | Size | Mean abs Exact SHAP | Mean old grouped attribution | Exact top-3 count | Old top-3 count |\n")
    lines.append("|---|---:|---:|---:|---:|---:|\n")
    for g, size, phi, old in zip(groups, group_sizes, mean_abs_phi, mean_old_attr):
        lines.append(f"| {g} | {int(size)} | {float(phi):.6f} | {float(old):.6f} | {exact_freq[g]} | {old_freq[g]} |\n")

    lines.append("\n## Agreement Between Methods\n\n")
    lines.append(f"- Mean top-3 overlap count: `{mean_overlap_count:.4f}` out of 3\n")
    lines.append(f"- Mean top-3 Jaccard overlap: `{mean_overlap_jaccard:.4f}`\n")
    lines.append(f"- Max enumeration-vs-closed-form SHAP difference: `{closed_form_diff_max:.6e}`\n")
    lines.append(f"- Max SHAP additivity residual: `{additivity_error_max:.6e}`\n")
    lines.append(f"- Max score reconstruction difference: `{score_diff_max:.6e}`\n\n")

    lines.append("## Closed-Form Equivalence for Logistic Regression\n\n")
    lines.append(
        "For a linear score model and fixed reference masking, the marginal contribution of group `g` "
        "does not depend on the coalition `S`. Therefore the exact Shapley sum collapses to:\n\n"
    )
    lines.append("```text\n")
    lines.append("phi_g(x) = sum_{i in G_g} w_i * (x_i - x_ref_i)\n")
    lines.append("```\n\n")
    lines.append(
        "The script verifies this by comparing coalition enumeration over the five groups with the "
        "closed-form group score difference. This closed form is the Stage 3.4 circuit target.\n\n"
    )
    lines.append("For integer ZK arithmetic, the reference artifact stores:\n\n")
    lines.append(f"- `Sx = {int(reference_payload['Sx'])}` and `Sw = {int(reference_payload['Sw'])}`\n")
    lines.append(f"- `max_abs_x_ref_int = {int(reference_payload['max_abs_x_ref_int'])}`\n")
    lines.append(f"- conservative `max_abs_phi_int` bound = `{int(reference_payload['conservative_max_abs_phi_int'])}`\n")
    lines.append("- `phi_g_int = sum_i w_int[i] * (x_int[i] - x_ref_int[i])`\n\n")

    lines.append("## Interpretation\n\n")
    lines.append(
        "The old grouped linear attribution is useful for engineering because it is cheap, deterministic, "
        "easy to quantize, and already has a compact SNARK relation in Stage 3.2/3.3. Its limitation is "
        "that `abs(w_i*x_i)` measures contribution magnitude relative to zero, not marginal contribution "
        "relative to a well-defined background input.\n\n"
    )
    lines.append(
        "Semantic-group Exact SHAP is academically stronger because each group receives a Shapley value "
        "computed from all coalitions of present/removed semantic groups. Removed groups are replaced by "
        "the training-set mean, so the explanation is tied to an explicit reference distribution and the "
        "LR score decomposition satisfies the SHAP efficiency property.\n\n"
    )
    lines.append(
        "Because there are only five semantic groups, exact enumeration is feasible: each sample evaluates "
        "all coalitions over five players, avoiding sampling variance and avoiding Partition SHAP heuristics "
        "in the current implementation.\n\n"
    )

    lines.append("## ZK Status\n\n")
    lines.append(
        "Stage 3 remains SNARK-only. Stages 3.1-3.3 prove Logistic Regression inference and the older "
        "grouped linear attribution proxy. Stage 3.4 verifies the semantic-group Exact SHAP top-3 relation "
        "for the public Logistic Regression model by using the closed-form LR specialization above. This "
        "is not confidential-model support, not arbitrary-model SHAP verification, and not sumcheck/GKR or "
        "Partition SHAP.\n"
    )

    _ensure_parent(out_md)
    out_md.write_text("".join(lines), encoding="utf-8")


def _write_method_report(*, out_md: Path, created_utc: str) -> None:
    lines: List[str] = []
    lines.append("# Method Choice: Semantic-Group Exact SHAP for ZK-XIDS\n\n")
    lines.append(f"Generated: {created_utc} (UTC)\n\n")
    lines.append("## Why keep the grouped linear attribution baseline\n\n")
    lines.append(
        "The existing attribution `sum_i |w_i*x_i|` per semantic group is engineering-heavy in a useful way: "
        "it is simple, deterministic, cheap to compute, easy to quantize, and already maps cleanly to the "
        "current Circom/Groth16 Stage 3.2 and Stage 3.3 circuits. That makes it a good proof-of-concept "
        "baseline for verifiable explanation authenticity.\n\n"
    )
    lines.append(
        "Its academic limitation is that it is not a Shapley-value explanation. It depends on the feature "
        "origin and uses absolute linear terms rather than marginal contributions under a coalition game.\n\n"
    )

    lines.append("## Why semantic-group Exact SHAP is stronger\n\n")
    lines.append(
        "Exact SHAP treats the five semantic groups as players and assigns each group the weighted average "
        "of its marginal effect over every coalition. The value function is the Logistic Regression score "
        "or logit, and removed groups are replaced by the feature-wise training-set mean in processed feature "
        "space. This gives a thesis-ready explanation method with a clear cooperative-game definition.\n\n"
    )
    lines.append(
        "The method is feasible here because there are only five players. Exact enumeration requires only "
        "2^5 coalition states per sample, so there is no need to approximate with Monte Carlo SHAP or "
        "Partition SHAP in the current scope.\n\n"
    )

    lines.append("## ZK positioning\n\n")
    lines.append(
        "The current system setting is public-model, private-input: the Logistic Regression weights and "
        "bias are public, while the processed network traffic features remain private witness values. The "
        "Stage 3 SNARK stack is Circom + Groth16 only.\n\n"
    )
    lines.append(
        "Stage 3.4 verifies semantic-group Exact SHAP top-3 authenticity for the public Logistic Regression "
        "model. This works because the Exact SHAP coalition definition collapses exactly to a group-wise "
        "closed form for a linear score model with fixed reference masking. Sumcheck/GKR is future "
        "scalability work and is not implemented or tested in this repo. Partition SHAP is also future work "
        "for larger or hierarchical group sets.\n\n"
    )

    lines.append("## Algorithm: Semantic-Group Exact SHAP for ZK-XIDS\n\n")
    lines.append("Inputs: public model `F`, private input `x`, semantic groups `G`, reference vector `x_ref`\n\n")
    lines.append("Outputs: `y_hat`, `phi_g(x)`, top-k groups, proof `pi`\n\n")
    lines.append("```text\n")
    lines.append("1. Compute y_hat = F(x).\n")
    lines.append("2. For each semantic group g in G:\n")
    lines.append("   a. Enumerate all coalitions S subseteq G \\ {g}.\n")
    lines.append("   b. For each S, form masked inputs where groups outside S are set to x_ref.\n")
    lines.append("   c. Compute the marginal score contribution F(x_{S union g}) - F(x_S).\n")
    lines.append("   d. Weight the marginal by |S|! (m-|S|-1)! / m!.\n")
    lines.append("3. Sum weighted marginals to obtain phi_g(x) for every group.\n")
    lines.append("4. Select the top-k semantic groups by explanation magnitude.\n")
    lines.append("5. Stage 3.4 proves prediction and top-k Exact SHAP groups are tied to the same private input x.\n")
    lines.append("6. The circuit keeps phi_g(x) private and publishes only y_hat plus top-k group IDs.\n")
    lines.append("```\n\n")
    lines.append(
        "This circuit is model-specific to Logistic Regression. No sumcheck protocol, GKR verifier, "
        "Partition SHAP implementation, confidential-model proof, or arbitrary-model Exact SHAP circuit "
        "has been implemented or tested.\n"
    )

    _ensure_parent(out_md)
    out_md.write_text("".join(lines), encoding="utf-8")


def build_arg_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=str(REPO_ROOT / "outputs" / "models" / "logreg_baseline.pkl"))
    ap.add_argument("--x-train", default=str(REPO_ROOT / "outputs" / "processed" / "X_train.npy"))
    ap.add_argument("--x-test", default=str(REPO_ROOT / "outputs" / "processed" / "X_test.npy"))
    ap.add_argument("--y-test", default=str(REPO_ROOT / "outputs" / "processed" / "y_test.npy"))
    ap.add_argument("--test-idx", default=str(REPO_ROOT / "outputs" / "splits" / "test_idx.npy"))
    ap.add_argument("--feature-names", default=str(REPO_ROOT / "outputs" / "processed" / "feature_order.json"))
    ap.add_argument("--group-map", default=str(REPO_ROOT / "stage3_zk" / "artifacts" / "group_map.json"))
    ap.add_argument("--model-public", default=str(REPO_ROOT / "stage3_zk" / "artifacts" / "model_public.json"))
    ap.add_argument("--bounds", default=str(REPO_ROOT / "stage3_zk" / "artifacts" / "bounds.json"))
    ap.add_argument("--random-state", type=int, default=42)
    ap.add_argument("--stage2-tp", type=int, default=1000)
    ap.add_argument("--stage2-fn", type=int, default=100)
    ap.add_argument("--fallback-n", type=int, default=500)
    ap.add_argument("--top-k", type=int, default=3)
    ap.add_argument(
        "--out-csv",
        default=str(REPO_ROOT / "outputs" / "explainability" / "exact_shap_semantic_groups.csv"),
    )
    ap.add_argument(
        "--out-report",
        default=str(REPO_ROOT / "reports" / "exact_shap_semantic_groups.md"),
    )
    ap.add_argument(
        "--out-method-report",
        default=str(REPO_ROOT / "reports" / "method_choice_exact_shap.md"),
    )
    ap.add_argument(
        "--out-reference",
        default=str(REPO_ROOT / "stage3_zk" / "artifacts" / "exact_shap_reference.json"),
    )
    return ap


def main(argv: Sequence[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)

    model_path = Path(args.model)
    x_train_path = Path(args.x_train)
    x_test_path = Path(args.x_test)
    y_test_path = Path(args.y_test)
    test_idx_path = Path(args.test_idx)
    feature_names_path = Path(args.feature_names)
    group_map_path = Path(args.group_map)
    model_public_path = Path(args.model_public)
    bounds_path = Path(args.bounds)
    out_csv = Path(args.out_csv)
    out_report = Path(args.out_report)
    out_method_report = Path(args.out_method_report)
    out_reference = Path(args.out_reference)

    feature_names = _load_feature_names(feature_names_path)
    n_features = len(feature_names)
    groups, group_ids = _load_group_map(group_map_path, n_features)
    masks = _group_masks(group_ids, len(groups))
    group_sizes = [int(mask.sum()) for mask in masks]
    model_public = _read_json(model_public_path)
    bounds = _read_json(bounds_path)

    model = _load_lr_model(model_path)
    w = np.asarray(model.coef_, dtype=np.float64).reshape(-1)
    b = float(np.asarray(model.intercept_, dtype=np.float64).reshape(-1)[0])
    if w.shape[0] != n_features:
        raise ValueError(f"Model has {w.shape[0]} coefficients, expected {n_features}")

    X_train = np.load(x_train_path, mmap_mode="r")
    X_test = np.load(x_test_path, mmap_mode="r")
    y_test = np.load(y_test_path, mmap_mode="r") if y_test_path.exists() else None
    test_idx = np.load(test_idx_path, mmap_mode="r") if test_idx_path.exists() else None

    if X_train.shape[1] != n_features or X_test.shape[1] != n_features:
        raise ValueError(f"Feature-count mismatch: X_train={X_train.shape}, X_test={X_test.shape}, n={n_features}")

    print("Computing processed-space training mean reference vector...")
    x_ref = np.asarray(np.mean(X_train, axis=0), dtype=np.float64)
    created = _utc_now_iso()
    reference_payload = _write_reference_artifact(
        out_path=out_reference,
        created_utc=created,
        x_ref=x_ref,
        model_public=model_public,
        group_ids=group_ids,
        bounds=bounds,
    )

    selected_idx, subset_source = _select_stage2_subset(
        X_test=X_test,
        y_test=y_test,
        model=model,
        random_state=int(args.random_state),
        stage2_tp=int(args.stage2_tp),
        stage2_fn=int(args.stage2_fn),
        fallback_n=int(args.fallback_n),
    )
    X = np.asarray(X_test[selected_idx], dtype=np.float64)
    y_true = np.asarray(y_test[selected_idx], dtype=np.int64) if y_test is not None else None
    dataset_idx = np.asarray(test_idx[selected_idx], dtype=np.int64) if test_idx is not None else None

    print(f"Selected {len(selected_idx)} samples via {subset_source}.")
    print("Enumerating Exact SHAP coalitions over semantic groups...")

    base_score = float(x_ref @ w + b)
    closed_form_phi = _score_deltas_by_group(X, w, x_ref, masks)
    phi = _exact_group_shap_from_deltas(closed_form_phi, base_score)
    closed_form_diff_max = float(np.max(np.abs(phi - closed_form_phi)))
    scores = base_score + closed_form_phi.sum(axis=1)
    y_pred = (scores >= 0.0).astype(np.int64)
    old_attr = _old_grouped_linear_attribution(X, w, masks)

    direct_scores = X @ w + b
    score_diff_max = float(np.max(np.abs(scores - direct_scores)))
    additivity_error = (phi.sum(axis=1) - (scores - base_score))
    additivity_error_max = float(np.max(np.abs(additivity_error)))

    rows: List[Dict[str, object]] = []
    exact_top3_rows: List[List[str]] = []
    old_top3_rows: List[List[str]] = []
    overlap_counts: List[int] = []
    overlap_jaccards: List[float] = []

    for i in range(X.shape[0]):
        exact_ids, exact_names = _topk_groups(phi[i], groups, k=int(args.top_k), use_abs=True)
        old_ids, old_names = _topk_groups(old_attr[i], groups, k=int(args.top_k), use_abs=False)
        overlap_count = len(set(exact_ids) & set(old_ids))
        overlap_j = _jaccard(exact_ids, old_ids)

        exact_top3_rows.append(exact_names)
        old_top3_rows.append(old_names)
        overlap_counts.append(overlap_count)
        overlap_jaccards.append(overlap_j)

        row: Dict[str, object] = {
            "sample_id": int(selected_idx[i]),
            "test_row_index": int(selected_idx[i]),
            "dataset_index": int(dataset_idx[i]) if dataset_idx is not None else "",
            "true_label": int(y_true[i]) if y_true is not None else "",
            "predicted_label": int(y_pred[i]),
            "model_score_logit": float(scores[i]),
            "exact_top3_group_ids": ";".join(str(x) for x in exact_ids),
            "exact_top3_groups": _format_top(exact_names),
            "old_top3_group_ids": ";".join(str(x) for x in old_ids),
            "old_top3_groups": _format_top(old_names),
            "top3_overlap_count": int(overlap_count),
            "top3_overlap_jaccard": float(overlap_j),
        }
        for j, group in enumerate(groups):
            row[f"exact_shap_{group}"] = float(phi[i, j])
        for j, group in enumerate(groups):
            row[f"old_linear_attr_{group}"] = float(old_attr[i, j])
        rows.append(row)

    df = pd.DataFrame(rows)
    _ensure_parent(out_csv)
    df.to_csv(out_csv, index=False)

    mean_abs_phi = np.mean(np.abs(phi), axis=0)
    mean_old_attr = np.mean(old_attr, axis=0)
    exact_freq = _frequency(exact_top3_rows, groups)
    old_freq = _frequency(old_top3_rows, groups)
    mean_overlap_count = float(np.mean(overlap_counts))
    mean_overlap_jaccard = float(np.mean(overlap_jaccards))

    _write_exact_report(
        out_md=out_report,
        created_utc=created,
        args=args,
        csv_path=out_csv.relative_to(REPO_ROOT) if out_csv.is_absolute() and REPO_ROOT in out_csv.parents else out_csv,
        n_samples=int(X.shape[0]),
        subset_source=subset_source,
        groups=groups,
        group_sizes=group_sizes,
        mean_abs_phi=mean_abs_phi,
        mean_old_attr=mean_old_attr,
        exact_freq=exact_freq,
        old_freq=old_freq,
        mean_overlap_count=mean_overlap_count,
        mean_overlap_jaccard=mean_overlap_jaccard,
        additivity_error_max=additivity_error_max,
        score_diff_max=score_diff_max,
        closed_form_diff_max=closed_form_diff_max,
        reference_artifact_path=out_reference.relative_to(REPO_ROOT) if out_reference.is_absolute() and REPO_ROOT in out_reference.parents else out_reference,
        reference_payload=reference_payload,
    )
    _write_method_report(out_md=out_method_report, created_utc=created)

    print(f"Wrote: {out_csv}")
    print(f"Wrote: {out_report}")
    print(f"Wrote: {out_method_report}")
    print(f"Wrote: {out_reference}")
    print(f"Mean top-{args.top_k} overlap count: {mean_overlap_count:.4f}")
    print(f"Mean top-{args.top_k} Jaccard overlap: {mean_overlap_jaccard:.4f}")
    print(f"Max enumeration-vs-closed-form SHAP difference: {closed_form_diff_max:.6e}")
    print(f"Max SHAP additivity residual: {additivity_error_max:.6e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
