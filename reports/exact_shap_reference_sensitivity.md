# Exact SHAP Reference Sensitivity

Generated: 2026-05-22T15:26:10+00:00 (UTC)

This offline analysis tests how semantic-group Exact SHAP top-3 explanations change when the reference vector changes. The implemented Stage 3.4 circuit still verifies the training-mean reference only; alternative references are sensitivity checks, not additional ZK claims.

- Samples: `1100`
- Baseline reference: `training_mean`
- Alternative references: `zero_vector`, `normal_train_mean`

## Top-3 Stability vs Training Mean

| Reference | Mean overlap / 3 | Mean Jaccard | Ordered top-3 changed | Changed rate |
|---|---:|---:|---:|---:|
| zero_vector | 2.2736 | 0.6399 | 1012 | 92.00% |
| normal_train_mean | 2.3945 | 0.6973 | 865 | 78.64% |

## Group Frequency by Reference

| Reference | Protocol | Application | ConnectionState | Ports | TrafficVolume |
|---|---:|---:|---:|---:|---:|
| training_mean | 1044 | 415 | 1061 | 250 | 530 |
| zero_vector | 1099 | 1070 | 765 | 97 | 269 |
| normal_train_mean | 1100 | 97 | 1017 | 1 | 1085 |

## Thesis Interpretation

Exact SHAP explanations depend on the reference vector used to replace masked groups. The training-set mean remains the implemented and verified reference because it is deterministic, public, and exported into the Stage 3.4 circuit. Sensitivity results should be used for critical self-assessment rather than as additional verified relations.
