# Semantic Group Ablation: Sum vs Mean (Size-Normalized)
Generated: 2026-02-12T20:39:13+00:00 (UTC)
## What this measures
Stage 2 counts how often each **semantic group** appears in the per-sample Top-k explanation. Because groups contain different numbers of features, raw frequency can be biased toward larger groups.
We compare two scoring rules:
- **Sum (raw):** % of samples where the group appears at least once in Top-k
- **Mean (normalized):** (raw %) / (group_size)
## logistic_regression
### Group sizes and frequencies
| Group | Size (#features) | Raw presence (% samples) | Normalized (raw/size) |
|---|---:|---:|---:|
| Protocol | 3 | 99.91 | 33.3030 |
| Application | 76 | 100.00 | 1.3158 |
| ConnectionState | 13 | 45.55 | 3.5035 |
| Ports | 2 | 6.36 | 3.1818 |
| TrafficVolume | 10 | 6.18 | 0.6182 |

### Top-3 groups
- Sum (raw): Application (100.00), Protocol (99.91), ConnectionState (45.55)
- Mean (normalized): Protocol (33.3030), ConnectionState (3.5035), Ports (3.1818)

### Figure
- `reports/figures/semantic_group_ablation_logistic_regression.png`
## xgboost
### Group sizes and frequencies
| Group | Size (#features) | Raw presence (% samples) | Normalized (raw/size) |
|---|---:|---:|---:|
| Protocol | 3 | 74.82 | 24.9394 |
| Application | 76 | 7.00 | 0.0921 |
| ConnectionState | 13 | 66.64 | 5.1259 |
| Ports | 2 | 95.91 | 47.9545 |
| TrafficVolume | 10 | 99.55 | 9.9545 |

### Top-3 groups
- Sum (raw): TrafficVolume (99.55), Ports (95.91), Protocol (74.82)
- Mean (normalized): Ports (47.9545), Protocol (24.9394), TrafficVolume (9.9545)

### Figure
- `reports/figures/semantic_group_ablation_xgboost.png`
