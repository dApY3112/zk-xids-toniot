# Stage 3.4 Diverse Test Vectors

Generated: 2026-05-27T20:12:26+00:00 (UTC)

These vectors extend the original TP/TN/FN proof cases with edge cases for IDS behavior and explanation stability. They are selected from the processed test split and use the same public quantized Logistic Regression artifact as Stage 3.4.

Circuit score bound used during selection: `abs(score_int) <= 68719476736`.

| Stage 3.4 sample | Label | Test row | Dataset index | y_true | y_hat | score_int | abs(score) | top-3 groups | rank3-rank4 margin |
|---:|---|---:|---:|---:|---:|---:|---:|---|---:|
| 4 | FP_normal | 206297 | 2037930 | 0 | 1 | 23752516133 | 23752516133 | TrafficVolume, Protocol, ConnectionState | 291043568 |
| 5 | HighConf_attack | 199211 | 497442 | 1 | 1 | 46656741774 | 46656741774 | TrafficVolume, ConnectionState, Protocol | 117262245 |
| 6 | HighConf_normal | 497400 | 1714021 | 0 | 0 | -67272542694 | 67272542694 | TrafficVolume, ConnectionState, Application | 132364379 |
| 7 | Borderline_score | 19818 | 583370 | 1 | 0 | -133791 | 133791 | Application, TrafficVolume, ConnectionState | 29012299 |
| 8 | SmallTop3Margin | 266195 | 1406019 | 1 | 1 | 755662630 | 755662630 | ConnectionState, Protocol, Ports | 342 |

## Interpretation

- `FP_normal` tests that the proof verifies the model's actual attack prediction even when the ground truth is Normal.
- `HighConf_attack` and `HighConf_normal` exercise large positive and negative score margins.
- `Borderline_score` exercises a prediction close to the LR decision boundary.
- `SmallTop3Margin` exercises a near-tie between the third and fourth Exact SHAP semantic groups.
- These vectors are correctness/stress evidence for the proof relation; they are not additional training data.
