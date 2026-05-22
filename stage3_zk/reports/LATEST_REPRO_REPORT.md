# Reproducibility Run Report

- Started (UTC): 2026-02-12T19:02:43+00:00
- Finished (UTC): 2026-02-12T19:04:20+00:00
- Duration (ms): 97000
- Git commit: f5416a6096577a87368753df32901620c81cfcc3

## Command

- Args: `{'stage': 'all', 'samples': [1, 2, 3], 'build': True, 'clean': True, 'no_witness_smoke': False, 'prove': True, 'verify': True, 'validate_proofs': True}`

## Environment

- OS: Windows-11-10.0.26100-SP0
- Python: 3.12.3 (C:\Anaconda\python.exe)
- Node: v20.12.2 (npm 10.8.3)
- snarkjs: snarkjs@0.7.5

## Complexity & Communication

| Stage | #Constraints | #Wires | Public Inputs | Private Inputs | R1CS (bytes) | WASM (bytes) | ZKey (bytes) | Proof (bytes) | Public (bytes) | #Public Signals |
|------:|------------:|------:|-------------:|--------------:|------------:|------------:|------------:|------------:|-------------:|---------------:|
| 31 | 3831 | 3829 | 106 | 104 | 597816 | 56283 | 1938424 | 805 | 3509 | 106 |
| 32 | 17684 | 17150 | 111 | 104 | 2770124 | 124524 | 9683997 | 805 | 1228 | 111 |
| 33 | 18719 | 18043 | 109 | 106 | 2927208 | 137026 | 10088775 | 803 | 1178 | 109 |

## Results

| Step | Status | Duration (ms) |
|------|--------|--------------:|
| clean_stage31 | PASS |  |
| clean_stage32 | PASS |  |
| clean_stage33 | PASS |  |
| build_stage31 | PASS | 28281 |
| build_stage32 | PASS | 22875 |
| build_stage33 | PASS | 23468 |
| prepare_input_stage31_sample1 | PASS | 1469 |
| prepare_input_stage31_sample2 | PASS | 421 |
| prepare_input_stage31_sample3 | PASS | 405 |
| prepare_input_stage32_sample1 | PASS | 125 |
| prepare_input_stage32_sample2 | PASS | 109 |
| prepare_input_stage32_sample3 | PASS | 93 |
| prepare_input_stage33_sample1 | PASS | 94 |
| prepare_input_stage33_sample2 | PASS | 93 |
| prepare_input_stage33_sample3 | PASS | 108 |
| witness_smoke_stage31_sample1 | PASS | 94 |
| witness_smoke_stage31_sample2 | PASS | 78 |
| witness_smoke_stage31_sample3 | PASS | 77 |
| witness_smoke_stage32_sample1 | PASS | 94 |
| witness_smoke_stage32_sample2 | PASS | 108 |
| witness_smoke_stage32_sample3 | PASS | 94 |
| witness_smoke_stage33_sample1 | PASS | 93 |
| witness_smoke_stage33_sample2 | PASS | 93 |
| witness_smoke_stage33_sample3 | PASS | 93 |
| prove_stage31_sample1 | PASS | 968 |
| verify_stage31_sample1 | PASS | 656 |
| prove_stage31_sample2 | PASS | 953 |
| verify_stage31_sample2 | PASS | 733 |
| prove_stage31_sample3 | PASS | 1030 |
| verify_stage31_sample3 | PASS | 641 |
| prove_stage32_sample1 | PASS | 1546 |
| verify_stage32_sample1 | PASS | 514 |
| prove_stage32_sample2 | PASS | 1343 |
| verify_stage32_sample2 | PASS | 531 |
| prove_stage32_sample3 | PASS | 1328 |
| verify_stage32_sample3 | PASS | 515 |
| prove_stage33_sample1 | PASS | 1266 |
| verify_stage33_sample1 | PASS | 531 |
| prove_stage33_sample2 | PASS | 1468 |
| verify_stage33_sample2 | PASS | 593 |
| prove_stage33_sample3 | PASS | 1422 |
| verify_stage33_sample3 | PASS | 608 |
| stage33_wrong_explanation_sample1 | PASS | 218 |
| stage33_malicious_other2_sample1 | PASS | 328 |
| stage33_validate_public_top3_sample1 | PASS | 109 |
| stage33_wrong_explanation_sample2 | PASS | 235 |
| stage33_malicious_other2_sample2 | PASS | 327 |
| stage33_validate_public_top3_sample2 | PASS | 94 |
| stage33_wrong_explanation_sample3 | PASS | 171 |
| stage33_malicious_other2_sample3 | PASS | 328 |
| stage33_validate_public_top3_sample3 | PASS | 78 |

