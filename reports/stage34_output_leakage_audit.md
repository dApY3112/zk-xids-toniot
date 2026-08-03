# Stage 3.4 Output Leakage Audit

Generated: 2026-05-22T15:25:29+00:00 (UTC)

Stage 3.4 intentionally reveals the public prediction `y_hat` and the top-3 semantic group IDs. It does not reveal processed input feature values or exact semantic-group SHAP magnitudes. This audit summarizes the information carried by those public explanation outputs on the Exact SHAP evaluation subset.

- Samples audited: `1100`
- Predicted-label entropy: `0.4395` bits
- Exact top-3 sequence entropy: `2.9615` bits
- Unique Exact SHAP top-3 sequences: `22` out of 60 possible ordered sequences

## Public Prediction Distribution

| Predicted label | Count | Rate |
|---:|---:|---:|
| 0 | 100 | 9.09% |
| 1 | 1000 | 90.91% |

## Top-3 Group Membership

| Group | Count in top-3 | Rate |
|---|---:|---:|
| Protocol | 1044 | 94.91% |
| Application | 415 | 37.73% |
| ConnectionState | 1061 | 96.45% |
| Ports | 250 | 22.73% |
| TrafficVolume | 530 | 48.18% |

## Most Frequent Ordered Top-3 Explanations

| Rank | Ordered top-3 groups | Count | Rate |
|---:|---|---:|---:|
| 1 | ConnectionState;Protocol;TrafficVolume | 417 | 37.91% |
| 2 | ConnectionState;Protocol;Application | 145 | 13.18% |
| 3 | ConnectionState;Protocol;Ports | 140 | 12.73% |
| 4 | Application;ConnectionState;Protocol | 114 | 10.36% |
| 5 | Protocol;Application;ConnectionState | 81 | 7.36% |
| 6 | ConnectionState;Ports;Protocol | 63 | 5.73% |
| 7 | Application;ConnectionState;TrafficVolume | 25 | 2.27% |
| 8 | Ports;ConnectionState;Protocol | 22 | 2.00% |
| 9 | Ports;Protocol;TrafficVolume | 17 | 1.55% |
| 10 | Protocol;TrafficVolume;Application | 15 | 1.36% |

## Thesis Interpretation

The public explanation is deliberately low-dimensional: a binary prediction plus three semantic group IDs. This is useful for SOC auditability, but it is still output leakage. The correct privacy claim is therefore input-feature privacy with intentional disclosure of the certified decision and semantic explanation summary, not complete behavioral secrecy.
