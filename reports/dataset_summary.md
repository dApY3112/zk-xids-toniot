# TON_IoT Processed Network Dataset — Summary (Stage 1)
- **Loaded mode:** `processed_stratified_sample_23files_frac0.15`
- **Sample fraction:** `15%` from each of 23 files
- **Total samples:** `3,350,853`
- **Total columns:** `47`

## Label distribution
| label | count | percentage |
|---:|---:|---:|
| 0 (Normal) | 119,481 | 3.57% |
| 1 (Attack) | 3,231,372 | 96.43% |

- **Attack/Normal ratio:** `27.04` (highly imbalanced)

## Data splits (stratified 70/15/15)
| Split | Samples | Attack % |
|---|---:|---:|
| Train | 2,345,597 | 96.43% |
| Validation | 502,628 | 96.43% |
| Test | 502,628 | 96.43% |

**Note:** Stratified split preserves class imbalance across all splits.

## Missing values
- Dataset contains significant missing values (NaN)
- `"-"` placeholders used extensively in categorical/string columns (replaced with "NONE" during preprocessing)

## Duplicated rows
- Duplicate detection performed on sampled data
- Duplicates retained for training (removal may lose attack patterns)

## Leakage-prone columns to drop before training
- `src_ip`, `dst_ip`, `type`, `ts`

## Notes
- Stage 1 uses **only** `label` as the training target (binary classification: 0=normal, 1=attack)
- `type` (attack name) is kept **only** for analysis/future work, not for training
- IP addresses are identifiers and can introduce label leakage; they are removed in preprocessing
- **No class balancing applied**: Imbalance handled via `class_weight="balanced"` in models and appropriate metrics (PR-AUC, Recall)
- **Random state:** 42 for reproducibility
- **Memory optimization:** Sample 15% per file with chunked loading to avoid OOM
