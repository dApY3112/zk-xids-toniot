# File-wise Holdout Robustness Check
Generated: 2026-05-27T19:54:32+00:00 (UTC)

## Purpose
The main thesis benchmark uses a stratified random split over the sampled union of 23 TON_IoT processed CSV files. This supplementary robustness check trains a Logistic Regression model on earlier-numbered files and evaluates it on a held-out block of later-numbered files. It is a file-wise holdout experiment, not a timestamp-ordered temporal deployment simulation.

## File split
- Training/validation files: `Network_dataset_1.csv, Network_dataset_2.csv, Network_dataset_3.csv, Network_dataset_4.csv, Network_dataset_5.csv, Network_dataset_6.csv, Network_dataset_7.csv, Network_dataset_8.csv, Network_dataset_9.csv, Network_dataset_10.csv, Network_dataset_11.csv, Network_dataset_12.csv, Network_dataset_13.csv, Network_dataset_14.csv, Network_dataset_15.csv, Network_dataset_16.csv, Network_dataset_17.csv, Network_dataset_18.csv, Network_dataset_19.csv`
- Held-out files: `Network_dataset_20.csv, Network_dataset_21.csv, Network_dataset_22.csv, Network_dataset_23.csv`
- Per-file sample fraction: `0.05`
- Training cap before validation split: `400000` rows

## Data summary
| Split | n | Normal | Attack | Attack % |
|---|---:|---:|---:|---:|
| train_model | 300000 | 7845 | 292155 | 97.3850% |
| validation | 100000 | 2615 | 97385 | 97.3850% |
| holdout | 166951 | 15081 | 151870 | 90.9668% |

## Operating points
Thresholds are selected on the validation part of the training-file sample and evaluated on the held-out files.

| Point | Threshold | Attack Recall | Normal Recall (Spec) | FPR | MCC | Confusion (tn/fp/fn/tp) |
|---|---:|---:|---:|---:|---:|---|
| default_0.5 | 0.500000 | 0.764417 | 0.904913 | 0.095087 | 0.420292 | 13647/1434/35778/116092 |
| low_fpr | 0.934938 | 0.214914 | 0.991181 | 0.008819 | 0.148739 | 14948/133/119231/32639 |
| balanced_mcc | 0.085572 | 0.979199 | 0.567403 | 0.432597 | 0.613392 | 8557/6524/3159/148711 |
| high_recall | 0.090232 | 0.977573 | 0.568596 | 0.431404 | 0.606608 | 8575/6506/3406/148464 |

## Interpretation
- This experiment directly addresses the limitation that the main split is random and can mix records from every processed CSV file across train, validation, and test.
- Because file numbering is only a proxy for source-file grouping, the result should be cited as file-wise robustness rather than true chronological validation.
- Large degradation relative to the main random split would indicate non-stationarity across files; stable performance would strengthen the generalization claim.

## Environment
- Python: `3.12.3`
- NumPy: `1.26.4`
- pandas: `2.3.3`
- scikit-learn: `1.5.1`

## Reproduce
`python tools/reproduce.py file-holdout --sample-frac 0.05 --holdout-count 4 --max-train-rows 400000`

Validation thresholds: `{"balanced_mcc": 0.08557165213509346, "default_0.5": 0.5, "high_recall": 0.09023188658943303, "low_fpr": 0.9349380386446884}`
