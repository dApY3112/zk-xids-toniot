from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


ROOT = Path(__file__).resolve().parents[1]
EXACT_SHAP_CSV = ROOT / "outputs" / "explainability" / "exact_shap_semantic_groups.csv"
STAGE34_PROOF_JSON = ROOT / "stage3_zk" / "reports" / "STAGE34_PROOF_REPORT.json"
FIG_DIR = ROOT / "reports" / "figures" / "thesis"
REPORT_PATH = ROOT / "reports" / "thesis_figures.md"

GROUPS = ["Protocol", "Application", "ConnectionState", "Ports", "TrafficVolume"]

STAGE_METRICS = [
    {
        "stage": "3.1",
        "label": "Inference",
        "constraints": 3831,
        "wires": 3829,
        "prove_mean_ms": 984,
        "verify_mean_ms": 677,
    },
    {
        "stage": "3.2",
        "label": "Semantic\naggregation",
        "constraints": 17684,
        "wires": 17150,
        "prove_mean_ms": 1406,
        "verify_mean_ms": 520,
    },
    {
        "stage": "3.3",
        "label": "Old proxy\ntop-3",
        "constraints": 18719,
        "wires": 18043,
        "prove_mean_ms": 1385,
        "verify_mean_ms": 577,
    },
    {
        "stage": "3.4",
        "label": "Exact SHAP\ntop-3",
        "constraints": 8358,
        "wires": 8078,
        "prove_mean_ms": 1653,
        "verify_mean_ms": 957,
    },
]


def _update_stage34_metrics_from_report() -> None:
    if not STAGE34_PROOF_JSON.exists():
        return
    with STAGE34_PROOF_JSON.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    stats = payload.get("circuit_stats", {})
    samples = [int(x) for x in payload.get("samples", [])]
    prove: list[int] = []
    verify: list[int] = []
    for sample in payload.get("sample_results", []):
        for step in sample.get("steps", []):
            name = str(step.get("step", ""))
            if name.startswith("prove_sample_"):
                prove.append(int(step.get("duration_ms", 0)))
            elif name.startswith("verify_sample_"):
                verify.append(int(step.get("duration_ms", 0)))
    STAGE_METRICS[-1].update(
        {
            "constraints": int(stats.get("constraints", STAGE_METRICS[-1]["constraints"])),
            "wires": int(stats.get("wires", STAGE_METRICS[-1]["wires"])),
            "prove_mean_ms": int(round(mean(prove))) if prove else STAGE_METRICS[-1]["prove_mean_ms"],
            "verify_mean_ms": int(round(mean(verify))) if verify else STAGE_METRICS[-1]["verify_mean_ms"],
            "sample_label": f"samples {min(samples)}-{max(samples)}"
            if samples and samples == list(range(min(samples), max(samples) + 1))
            else ("samples " + ",".join(str(x) for x in samples) if samples else "reported samples"),
        }
    )


_update_stage34_metrics_from_report()

CASE_STUDIES = [
    {
        "sample": "Sample 1\nTP attack",
        "old": {
            "Protocol": 765_722_624,
            "Application": 2_404_909_056,
            "ConnectionState": 57_540_608,
            "Ports": 58_746_793,
            "TrafficVolume": 88_863_615,
        },
        "exact": {
            "Protocol": 168_539_528,
            "Application": 300_903_907,
            "ConnectionState": 260_335_315,
            "Ports": 44_447_753,
            "TrafficVolume": 23_647_598,
        },
    },
    {
        "sample": "Sample 2\nTN normal",
        "old": {
            "Protocol": 765_722_624,
            "Application": 2_155_282_432,
            "ConnectionState": 1_283_850_240,
            "Ports": 12_256_419,
            "TrafficVolume": 173_535_464,
        },
        "exact": {
            "Protocol": 168_539_528,
            "Application": 51_277_283,
            "ConnectionState": 1_601_726_163,
            "Ports": 12_256_419,
            "TrafficVolume": 72_926_653,
        },
    },
    {
        "sample": "Sample 3\nFN attack",
        "old": {
            "Protocol": 1_462_304_768,
            "Application": 4_262_854_656,
            "ConnectionState": 57_540_608,
            "Ports": 52_314_983,
            "TrafficVolume": 487_883_929,
        },
        "exact": {
            "Protocol": 2_059_487_864,
            "Application": 1_432_654_365,
            "ConnectionState": 260_335_315,
            "Ports": 51_311_239,
            "TrafficVolume": 233_813_764,
        },
    },
]

COLORS = {
    "blue": "#2f6f9f",
    "teal": "#2a9d8f",
    "orange": "#d9822b",
    "red": "#c44536",
    "purple": "#6d5bd0",
    "gray": "#6b7280",
    "light_gray": "#e5e7eb",
    "dark": "#1f2937",
}


def _set_style() -> None:
    plt.rcParams.update(
        {
            "figure.dpi": 130,
            "savefig.dpi": 220,
            "font.size": 10,
            "axes.titlesize": 13,
            "axes.labelsize": 10,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "legend.fontsize": 9,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.alpha": 0.25,
            "grid.linewidth": 0.8,
        }
    )


def _save(fig: plt.Figure, name: str) -> Path:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    path = FIG_DIR / name
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def _box(ax, xy, width, height, text, fc="#ffffff", ec=COLORS["dark"], lw=1.2):
    x, y = xy
    patch = FancyBboxPatch(
        (x, y),
        width,
        height,
        boxstyle="round,pad=0.02,rounding_size=0.025",
        facecolor=fc,
        edgecolor=ec,
        linewidth=lw,
    )
    ax.add_patch(patch)
    ax.text(x + width / 2, y + height / 2, text, ha="center", va="center", color=COLORS["dark"], wrap=True)
    return patch


def _arrow(ax, start, end, color=COLORS["gray"], rad=0.0):
    arrow = FancyArrowPatch(
        start,
        end,
        arrowstyle="-|>",
        mutation_scale=12,
        linewidth=1.3,
        color=color,
        connectionstyle=f"arc3,rad={rad}",
    )
    ax.add_patch(arrow)


def _read_exact_rows() -> list[dict[str, str]]:
    if not EXACT_SHAP_CSV.exists():
        raise FileNotFoundError(f"Missing required CSV: {EXACT_SHAP_CSV}")
    with EXACT_SHAP_CSV.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _split_groups(value: str) -> list[str]:
    return [item.strip() for item in value.split(";") if item.strip()]


def figure_01_framework() -> Path:
    fig, ax = plt.subplots(figsize=(11.5, 5.5))
    ax.set_axis_off()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    _box(ax, (0.04, 0.58), 0.16, 0.18, "Private input\nx_shifted[104]", fc="#eef6ff", ec=COLORS["blue"])
    _box(ax, (0.27, 0.58), 0.17, 0.18, "Public LR\nscore + y_hat", fc="#ecfdf5", ec=COLORS["teal"])
    _box(ax, (0.51, 0.58), 0.18, 0.18, "Semantic-group\nExact SHAP", fc="#fff7ed", ec=COLORS["orange"])
    _box(ax, (0.76, 0.58), 0.17, 0.18, "Groth16 proof\npi", fc="#f5f3ff", ec=COLORS["purple"])
    _box(ax, (0.76, 0.22), 0.17, 0.18, "Verifier accepts\n(y_hat, top3)", fc="#f9fafb", ec=COLORS["dark"])
    _box(ax, (0.30, 0.18), 0.35, 0.18, "Approved public model version\nweights, feature order, groups, x_ref, vkey", fc="#f9fafb", ec=COLORS["gray"])

    _arrow(ax, (0.20, 0.67), (0.27, 0.67), COLORS["blue"])
    _arrow(ax, (0.44, 0.67), (0.51, 0.67), COLORS["teal"])
    _arrow(ax, (0.69, 0.67), (0.76, 0.67), COLORS["orange"])
    _arrow(ax, (0.845, 0.58), (0.845, 0.40), COLORS["purple"])
    _arrow(ax, (0.65, 0.27), (0.76, 0.31), COLORS["gray"])
    _arrow(ax, (0.48, 0.36), (0.36, 0.58), COLORS["gray"])
    _arrow(ax, (0.52, 0.36), (0.60, 0.58), COLORS["gray"])

    ax.text(
        0.5,
        0.93,
        "Zero-knowledge verification of semantic explanations under private inputs",
        ha="center",
        va="center",
        fontsize=15,
        fontweight="bold",
        color=COLORS["dark"],
    )
    ax.text(
        0.5,
        0.08,
        "Public-model/private-input setting: raw features and full SHAP values remain private; y_hat and top-3 group IDs are intentionally disclosed.",
        ha="center",
        va="center",
        color=COLORS["gray"],
    )
    return _save(fig, "thesis_figure_01_framework.png")


def figure_02_semantic_grouping_pipeline() -> Path:
    fig, ax = plt.subplots(figsize=(11.5, 5.3))
    ax.set_axis_off()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    _box(ax, (0.04, 0.55), 0.18, 0.20, "104 processed\nfeatures", fc="#eef6ff", ec=COLORS["blue"])
    _box(ax, (0.30, 0.55), 0.18, 0.20, "Feature-order\nregistry", fc="#f9fafb", ec=COLORS["gray"])
    _box(ax, (0.56, 0.55), 0.18, 0.20, "Semantic group\nmap", fc="#fff7ed", ec=COLORS["orange"])
    _box(ax, (0.80, 0.55), 0.16, 0.20, "5 SHAP\nplayers", fc="#ecfdf5", ec=COLORS["teal"])
    _arrow(ax, (0.22, 0.65), (0.30, 0.65), COLORS["blue"])
    _arrow(ax, (0.48, 0.65), (0.56, 0.65), COLORS["gray"])
    _arrow(ax, (0.74, 0.65), (0.80, 0.65), COLORS["orange"])

    x0 = 0.13
    width = 0.14
    gap = 0.045
    y = 0.19
    palette = ["#e0f2fe", "#dcfce7", "#ffedd5", "#fce7f3", "#ede9fe"]
    for idx, group in enumerate(GROUPS):
        _box(ax, (x0 + idx * (width + gap), y), width, 0.16, group, fc=palette[idx], ec=COLORS["dark"], lw=1.0)
        _arrow(ax, (0.88, 0.55), (x0 + idx * (width + gap) + width / 2, y + 0.16), COLORS["gray"], rad=0.15 - 0.07 * idx)

    ax.text(
        0.5,
        0.92,
        "Semantic grouping turns high-dimensional tabular features into human-readable explanation players",
        ha="center",
        fontsize=14,
        fontweight="bold",
        color=COLORS["dark"],
    )
    return _save(fig, "thesis_figure_02_semantic_grouping_pipeline.png")


def figure_03_stage_progression() -> Path:
    fig, ax = plt.subplots(figsize=(12, 5.4))
    ax.set_axis_off()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    stages = [
        ("Stage 3.1", "LR inference\nonly", "#eef6ff", COLORS["blue"]),
        ("Stage 3.2", "Old semantic\naggregation", "#ecfdf5", COLORS["teal"]),
        ("Stage 3.3", "Old proxy\ntop-3", "#fff7ed", COLORS["orange"]),
        ("Stage 3.4", "Exact SHAP\ntop-3", "#f5f3ff", COLORS["purple"]),
    ]
    x_positions = [0.07, 0.31, 0.55, 0.79]
    for i, (stage, text, fc, ec) in enumerate(stages):
        _box(ax, (x_positions[i], 0.52), 0.16, 0.22, f"{stage}\n{text}", fc=fc, ec=ec)
        if i < len(stages) - 1:
            _arrow(ax, (x_positions[i] + 0.16, 0.63), (x_positions[i + 1], 0.63), COLORS["gray"])

    notes = [
        "Proves prediction",
        "Adds 5 semantic\naggregates",
        "Authenticates old\nattribution top-k",
        "Verifies semantic-group\nExact SHAP top-3",
    ]
    for i, note in enumerate(notes):
        _box(ax, (x_positions[i], 0.22), 0.16, 0.14, note, fc="#ffffff", ec=COLORS["light_gray"], lw=1.0)
        _arrow(ax, (x_positions[i] + 0.08, 0.52), (x_positions[i] + 0.08, 0.36), COLORS["gray"])

    ax.text(
        0.5,
        0.91,
        "Progressive ZK circuit design from inference to verified Exact SHAP explanations",
        ha="center",
        fontsize=14,
        fontweight="bold",
        color=COLORS["dark"],
    )
    return _save(fig, "thesis_figure_03_stage_progression.png")


def figure_04_constraints() -> Path:
    fig, ax = plt.subplots(figsize=(9, 5.2))
    x = range(len(STAGE_METRICS))
    values = [row["constraints"] for row in STAGE_METRICS]
    labels = [f"Stage {row['stage']}\n{row['label']}" for row in STAGE_METRICS]
    bars = ax.bar(x, values, color=[COLORS["blue"], COLORS["teal"], COLORS["orange"], COLORS["purple"]])
    ax.set_title("Constraint comparison across ZK stages")
    ax.set_ylabel("R1CS constraints")
    ax.set_xticks(list(x), labels)
    ax.set_ylim(0, max(values) * 1.18)
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, value + max(values) * 0.025, f"{value:,}", ha="center", va="bottom")
    return _save(fig, "thesis_figure_04_constraints_by_stage.png")


def figure_05_prove_verify() -> Path:
    fig, ax = plt.subplots(figsize=(9.5, 5.2))
    x = list(range(len(STAGE_METRICS)))
    width = 0.34
    prove = [row["prove_mean_ms"] for row in STAGE_METRICS]
    verify = [row["verify_mean_ms"] for row in STAGE_METRICS]
    labels = [f"Stage {row['stage']}\n{row['label']}" for row in STAGE_METRICS]
    bars1 = ax.bar([i - width / 2 for i in x], prove, width, label="Prove mean", color=COLORS["blue"])
    bars2 = ax.bar([i + width / 2 for i in x], verify, width, label="Verify mean", color=COLORS["orange"])
    ax.set_title("Prove and verify time comparison across ZK stages")
    ax.set_ylabel("Time (ms)")
    ax.set_xticks(x, labels)
    ax.legend(frameon=False)
    ymax = max(prove + verify)
    ax.set_ylim(0, ymax * 1.22)
    for bars in (bars1, bars2):
        for bar in bars:
            value = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2, value + ymax * 0.025, f"{int(value):,}", ha="center", va="bottom", fontsize=8)
    return _save(fig, "thesis_figure_05_prove_verify_time_by_stage.png")


def figure_06_frequency(rows: list[dict[str, str]]) -> Path:
    exact_counter = Counter()
    old_counter = Counter()
    for row in rows:
        exact_counter.update(_split_groups(row["exact_top3_groups"]))
        old_counter.update(_split_groups(row["old_top3_groups"]))

    x = list(range(len(GROUPS)))
    width = 0.36
    old_vals = [old_counter[g] for g in GROUPS]
    exact_vals = [exact_counter[g] for g in GROUPS]
    fig, ax = plt.subplots(figsize=(10, 5.4))
    ax.bar([i - width / 2 for i in x], old_vals, width, label="Old proxy", color=COLORS["gray"])
    ax.bar([i + width / 2 for i in x], exact_vals, width, label="Exact SHAP", color=COLORS["teal"])
    ax.set_title("Top-3 semantic group frequency: old proxy vs Exact SHAP")
    ax.set_ylabel("Top-3 membership count")
    ax.set_xticks(x, GROUPS, rotation=18, ha="right")
    ax.legend(frameon=False)
    ymax = max(old_vals + exact_vals)
    ax.set_ylim(0, ymax * 1.20)
    for i, value in enumerate(old_vals):
        ax.text(i - width / 2, value + ymax * 0.02, f"{value}", ha="center", va="bottom", fontsize=8)
    for i, value in enumerate(exact_vals):
        ax.text(i + width / 2, value + ymax * 0.02, f"{value}", ha="center", va="bottom", fontsize=8)
    return _save(fig, "thesis_figure_06_top3_group_frequency_proxy_vs_exact.png")


def figure_07_overlap(rows: list[dict[str, str]]) -> Path:
    overlap_counter = Counter(int(float(row["top3_overlap_count"])) for row in rows)
    x = [0, 1, 2, 3]
    values = [overlap_counter[i] for i in x]
    mean_overlap = sum(int(float(row["top3_overlap_count"])) for row in rows) / len(rows)
    mean_jaccard = sum(float(row["top3_overlap_jaccard"]) for row in rows) / len(rows)

    fig, ax = plt.subplots(figsize=(8.4, 5.2))
    bars = ax.bar(x, values, color=[COLORS["red"], COLORS["orange"], COLORS["teal"], COLORS["blue"]])
    ax.set_title("Old proxy vs Exact SHAP top-3 overlap distribution")
    ax.set_xlabel("Number of shared groups in top-3")
    ax.set_ylabel("Sample count")
    ax.set_xticks(x, [str(i) for i in x])
    ymax = max(values)
    ax.set_ylim(0, ymax * 1.22)
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, value + ymax * 0.025, f"{value}", ha="center", va="bottom")
    ax.text(
        0.03,
        0.94,
        f"Mean overlap = {mean_overlap:.4f} / 3\nMean Jaccard = {mean_jaccard:.4f}",
        transform=ax.transAxes,
        ha="left",
        va="top",
        bbox={"boxstyle": "round,pad=0.3", "facecolor": "#ffffff", "edgecolor": COLORS["light_gray"]},
    )
    return _save(fig, "thesis_figure_07_top3_overlap_distribution.png")


def figure_08_case_study_bars() -> Path:
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.8), sharey=True)
    x = list(range(len(GROUPS)))
    width = 0.36
    for ax, case in zip(axes, CASE_STUDIES):
        old_vals = [case["old"][g] / 1e9 for g in GROUPS]
        exact_vals = [case["exact"][g] / 1e9 for g in GROUPS]
        ax.bar([i - width / 2 for i in x], old_vals, width, label="Old proxy", color=COLORS["gray"])
        ax.bar([i + width / 2 for i in x], exact_vals, width, label="Exact SHAP abs", color=COLORS["purple"])
        ax.set_title(case["sample"])
        ax.set_xticks(x, ["Protocol", "App.", "Conn.", "Ports", "Traffic"], rotation=25, ha="right")
        ax.set_ylim(0, 4.8)
    axes[0].set_ylabel("Group magnitude (billions, integer scale)")
    axes[0].legend(frameon=False, loc="upper left")
    fig.suptitle("Case-study explanation magnitudes for TP, TN, and FN examples", fontsize=14, fontweight="bold")
    return _save(fig, "thesis_figure_08_case_study_group_bars.png")


def write_report(paths: list[Path], rows: list[dict[str, str]]) -> Path:
    n = len(rows)
    mean_overlap = sum(int(float(row["top3_overlap_count"])) for row in rows) / n
    mean_jaccard = sum(float(row["top3_overlap_jaccard"]) for row in rows) / n
    stage34 = STAGE_METRICS[-1]
    lines = [
        "# Thesis Figure Package\n\n",
        f"Generated: {datetime.now(timezone.utc).replace(microsecond=0).isoformat()} (UTC)\n\n",
        "This report lists the thesis-facing figures generated from existing repository artifacts. No circuits, proof logic, ML artifacts, or benchmark values are changed by this script.\n\n",
        "## Data Sources\n\n",
        f"- Exact SHAP comparison CSV: `{EXACT_SHAP_CSV.relative_to(ROOT).as_posix()}` ({n} samples)\n",
        "- Stage metrics: `reports/stage34_thesis_integration.md` and `stage3_zk/reports/STAGE34_PROOF_REPORT.md`\n",
        "- Case-study values: `reports/stage34_case_studies.md`\n\n",
        "## Key Figure Inputs\n\n",
        f"- Mean old-vs-Exact top-3 overlap: `{mean_overlap:.4f} / 3`\n",
        f"- Mean old-vs-Exact Jaccard overlap: `{mean_jaccard:.4f}`\n",
        f"- Stage 3.4 constraints: `{stage34['constraints']}`\n",
        f"- Stage 3.4 mean prove / verify time over {stage34.get('sample_label', 'reported samples')}: `{stage34['prove_mean_ms']} ms` / `{stage34['verify_mean_ms']} ms`\n\n",
        "## Generated Figures\n\n",
    ]
    for idx, path in enumerate(paths, start=1):
        rel = path.relative_to(ROOT).as_posix()
        lines.append(f"{idx}. `{rel}`\n")
    REPORT_PATH.write_text("".join(lines), encoding="utf-8")
    return REPORT_PATH


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate thesis-facing figures for ZK-XIDS.")
    parser.add_argument("--skip-case-study", action="store_true", help="Do not generate the optional case-study bars figure.")
    args = parser.parse_args()

    _set_style()
    rows = _read_exact_rows()
    paths = [
        figure_01_framework(),
        figure_02_semantic_grouping_pipeline(),
        figure_03_stage_progression(),
        figure_04_constraints(),
        figure_05_prove_verify(),
        figure_06_frequency(rows),
        figure_07_overlap(rows),
    ]
    if not args.skip_case_study:
        paths.append(figure_08_case_study_bars())
    report_path = write_report(paths, rows)

    print(f"Wrote {len(paths)} figures to: {FIG_DIR}")
    for path in paths:
        print(f"- {path}")
    print(f"Wrote report: {report_path}")


if __name__ == "__main__":
    main()
