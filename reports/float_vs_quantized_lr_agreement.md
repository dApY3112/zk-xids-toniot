# Float LR vs Quantized LR Agreement

Generated: 2026-05-27T19:40:17+00:00 (UTC)

## Purpose

This report checks whether the integer Logistic Regression relation used by the ZK circuits faithfully matches the floating-point scikit-learn Logistic Regression model on the validation and test splits. The comparison uses the same public quantization artifacts as Stage 3: `Sx = 65536`, `Sw = 4096`, `w_int = round(w * Sw)`, `x_int = round(x * Sx)`, and `b_int = round(b * Sx * Sw)`.

## Prediction Agreement

| Split | n | Agreement | Mismatches | Mismatch rate | Float attack rate | Quantized attack rate |
|---|---:|---:|---:|---:|---:|---:|
| val | 502628 | 99.991246% | 44 | 0.008754% | 90.498142% | 90.499335% |
| test | 502628 | 99.994230% | 29 | 0.005770% | 90.466707% | 90.465314% |

## Score Approximation Error

The quantized integer score is rescaled by `Sx * Sw` before comparison with the float LR logit.

| Split | mean abs error | p95 abs error | max abs error |
|---|---:|---:|---:|
| val | 0.040946 | 0.116889 | 161.208082 |
| test | 0.041297 | 0.116913 | 154.911022 |

## Exact SHAP Top-3 Agreement

Float Exact SHAP uses `phi_g = sum_{i in G_g} w_i * (x_i - x_ref_i)`. Quantized Exact SHAP uses the Stage 3.4 integer relation `phi_g_int = sum_{i in G_g} w_int[i] * (x_int[i] - x_ref_int[i])`.

| Split | Ordered top-3 match | Ordered mismatches | Mean overlap / 3 | Mean Jaccard |
|---|---:|---:|---:|---:|
| val | 93.855694% | 30883 | 2.945248 | 0.972624 |
| test | 93.817495% | 31075 | 2.944878 | 0.972439 |

## Examples

Representative mismatch examples are written to `outputs/reports/float_vs_quantized_lr_examples.csv`. The table below shows the first few.

| Split | Kind | row | dataset_idx | y_true | float_score | quant_score | float_pred | quant_pred | float_top3 | quant_top3 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| val | prediction_mismatch | 29571 | 1444443 | 1 | 0.002326 | -0.173927 | 1 | 0 | 2,3,1 | 2,3,1 |
| val | prediction_mismatch | 39614 | 595986 | 1 | -0.005027 | 0.031867 | 0 | 1 | 2,5,3 | 2,5,3 |
| val | top3_order_mismatch | 30 | 1997892 | 1 | 2.556995 | 2.519092 | 1 | 1 | 2,5,3 | 2,3,5 |
| val | top3_order_mismatch | 52 | 658304 | 1 | 2.898599 | 2.883272 | 1 | 1 | 3,1,4 | 3,1,2 |
| val | top3_order_mismatch | 83 | 577172 | 1 | 6.334984 | 6.216746 | 1 | 1 | 3,1,4 | 3,1,2 |
| val | top3_order_mismatch | 93 | 638488 | 1 | 6.338683 | 6.219157 | 1 | 1 | 3,1,4 | 3,1,2 |
| val | top3_order_mismatch | 100 | 1362763 | 1 | 6.330746 | 6.214828 | 1 | 1 | 3,1,4 | 3,1,2 |
| val | top3_order_mismatch | 126 | 1498057 | 1 | 2.550240 | 2.491642 | 1 | 1 | 3,1,4 | 3,1,2 |
| val | top3_order_mismatch | 135 | 1734394 | 1 | 2.980946 | 3.010343 | 1 | 1 | 1,4,5 | 4,1,5 |
| val | top3_order_mismatch | 145 | 994590 | 1 | 2.902708 | 2.888716 | 1 | 1 | 3,1,4 | 3,1,2 |

## Thesis Interpretation

The evaluated splits contain float-vs-quantized prediction mismatches. These cases should be treated as quantization boundary effects: the ZK proof remains correct for the integer circuit relation, but the thesis should report that the quantized relation can differ from the floating-point sklearn model near the decision boundary.

This is an empirical agreement check, not a cryptographic proof of equivalence for all possible inputs. The formal ZK claim remains the integer relation encoded in the circuit and bound by the public artifacts.
