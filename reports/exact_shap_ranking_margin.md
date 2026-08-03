# Exact SHAP Top-3 Ranking Margin Analysis

Generated: 2026-05-27T19:43:21+00:00 (UTC)

## Purpose

Stage 3.4 proves that the public top-3 semantic group IDs are a valid non-increasing ranking by absolute quantized Exact SHAP value. This report measures the empirical gap between rank 3 and rank 4. A small gap means the certified ranking is correct for the current input, but may be fragile under small input, reference, or quantization changes.

## Margin Definition

```text
margin = abs(phi_rank3_int) - abs(phi_rank4_int)
margin_scaled = margin / (Sx * Sw)
relative_margin = margin / max(abs(phi_rank3_int), 1)
```

## Margin Distribution

| Split | n | min | p1 | p5 | p10 | median | mean | p95 | max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| val | 502628 | 1.274049e-06 | 0.000411 | 0.000411 | 0.000411 | 0.044013 | 0.166426 | 0.774113 | 1.907891 |
| test | 502628 | 1.274049e-06 | 0.000411 | 0.000411 | 0.000411 | 0.044013 | 0.167759 | 0.774113 | 5.073528 |

## Small-Margin Counts

| Split | <=0 | <=0.001 | <=0.01 | <=0.1 | <=1.0 |
|---|---:|---:|---:|---:|---:|
| val | 0 (0.0000%) | 56155 (11.1723%) | 134680 (26.7952%) | 340658 (67.7754%) | 500513 (99.5792%) |
| test | 0 (0.0000%) | 55692 (11.0802%) | 134761 (26.8113%) | 339205 (67.4863%) | 500522 (99.5810%) |

## Smallest-Margin Examples

Full examples are written to `outputs/reports/exact_shap_ranking_margin_examples.csv`.

| Split | row | dataset_idx | y_true | margin_scaled | top3 | rank4 | ordered groups |
|---|---:|---:|---:|---:|---|---:|---|
| test | 266195 | 1406019 | 1 | 1.274049e-06 | 3,1,4 | 2 | ConnectionState;Protocol;Ports;Application;TrafficVolume |
| test | 422141 | 1049448 | 1 | 1.274049e-06 | 3,1,4 | 2 | ConnectionState;Protocol;Ports;Application;TrafficVolume |
| val | 111091 | 1090567 | 1 | 1.274049e-06 | 3,1,4 | 2 | ConnectionState;Protocol;Ports;Application;TrafficVolume |
| val | 229066 | 798398 | 1 | 1.274049e-06 | 3,1,4 | 2 | ConnectionState;Protocol;Ports;Application;TrafficVolume |
| val | 302863 | 1538363 | 1 | 1.274049e-06 | 3,1,4 | 2 | ConnectionState;Protocol;Ports;Application;TrafficVolume |
| val | 373697 | 1405629 | 1 | 1.274049e-06 | 3,1,4 | 2 | ConnectionState;Protocol;Ports;Application;TrafficVolume |
| val | 401318 | 704386 | 1 | 1.274049e-06 | 3,1,4 | 2 | ConnectionState;Protocol;Ports;Application;TrafficVolume |
| val | 398477 | 2534282 | 1 | 1.527369e-06 | 3,1,4 | 5 | ConnectionState;Protocol;Ports;TrafficVolume;Application |
| test | 207511 | 1628988 | 1 | 1.631677e-06 | 3,1,5 | 4 | ConnectionState;Protocol;TrafficVolume;Ports;Application |
| test | 10540 | 644987 | 1 | 1.646578e-06 | 3,1,2 | 4 | ConnectionState;Protocol;Application;Ports;TrafficVolume |
| test | 52811 | 677927 | 1 | 1.646578e-06 | 3,1,2 | 4 | ConnectionState;Protocol;Application;Ports;TrafficVolume |
| test | 89429 | 1095451 | 1 | 1.646578e-06 | 3,1,2 | 4 | ConnectionState;Protocol;Application;Ports;TrafficVolume |

## Thesis Interpretation

The current circuit correctly certifies a top-3 ranking for the supplied private input, but it does not certify robustness of that ranking. Report this margin analysis as empirical self-assessment: large margins support stable explanations, while near-zero margins identify cases where the third and fourth groups are nearly tied and the explanation should be interpreted cautiously.
