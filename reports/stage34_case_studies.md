# Stage 3.4 Exact SHAP Case Studies

Generated: 2026-05-22T15:27:41+00:00 (UTC)

These case studies use the three existing ZK test vectors. Stage 3.3 reports the old grouped linear attribution proxy, while Stage 3.4 verifies semantic-group Exact SHAP top-3 by absolute SHAP magnitude. Exact SHAP values are shown as signed integer score contributions at scale `Sx*Sw`.

| Sample | Label | y_true | y_hat | Stage 3.3 old top-3 | Stage 3.4 Exact SHAP top-3 | Proof |
|---:|---|---:|---:|---|---|---|
| 1 | TP_attack | 1 | 1 | Application, Protocol, TrafficVolume | Application, ConnectionState, Protocol | PASS |
| 2 | TN_normal | 0 | 0 | Application, ConnectionState, Protocol | ConnectionState, Protocol, TrafficVolume | PASS |
| 3 | FN_attack | 1 | 0 | Application, Protocol, TrafficVolume | Protocol, Application, ConnectionState | PASS |

## Sample 1: TP_attack

- Ground truth: `1`
- LR prediction / public `y_hat`: `1`
- LR integer score: `390,139,428`
- Stage 3.3 old proxy top-3: Application, Protocol, TrafficVolume
- Stage 3.4 Exact SHAP top-3: Application, ConnectionState, Protocol
- Stage 3.4 proof status: `PASS` (witness 80 ms, prove 1090 ms, verify 672 ms)

### Group Values

| Group | Old grouped attribution | Exact SHAP phi_int | abs(phi_int) | In old top-3 | In Exact top-3 |
|---|---:|---:|---:|---|---|
| Protocol | 765,722,624 | 168,539,528 | 168,539,528 | yes | yes |
| Application | 2,404,909,056 | -300,903,907 | 300,903,907 | yes | yes |
| ConnectionState | 57,540,608 | -260,335,315 | 260,335,315 | no | yes |
| Ports | 58,746,793 | 44,447,753 | 44,447,753 | no | no |
| TrafficVolume | 88,863,615 | -23,647,598 | 23,647,598 | yes | no |

### Interpretation

This true-positive attack is verified as an attack by both the LR prediction proof and the Exact SHAP top-3 proof. The two explanation methods agree on Application, Protocol; Exact SHAP additionally emphasizes ConnectionState as a marginal semantic driver relative to the training-mean reference.

## Sample 2: TN_normal

- Ground truth: `0`
- LR prediction / public `y_hat`: `0`
- LR integer score: `-661,754,717`
- Stage 3.3 old proxy top-3: Application, ConnectionState, Protocol
- Stage 3.4 Exact SHAP top-3: ConnectionState, Protocol, TrafficVolume
- Stage 3.4 proof status: `PASS` (witness 63 ms, prove 1083 ms, verify 605 ms)

### Group Values

| Group | Old grouped attribution | Exact SHAP phi_int | abs(phi_int) | In old top-3 | In Exact top-3 |
|---|---:|---:|---:|---|---|
| Protocol | 765,722,624 | 168,539,528 | 168,539,528 | yes | yes |
| Application | 2,155,282,432 | -51,277,283 | 51,277,283 | yes | no |
| ConnectionState | 1,283,850,240 | -1,601,726,163 | 1,601,726,163 | yes | yes |
| Ports | 12,256,419 | -12,256,419 | 12,256,419 | no | no |
| TrafficVolume | 173,535,464 | 72,926,653 | 72,926,653 | no | yes |

### Interpretation

This true-negative normal sample shows why signed-reference explanations are useful: the old proxy remains dominated by large absolute feature terms, while Exact SHAP ranks the groups by marginal deviation from the reference input. The verified Exact SHAP top-3 is therefore a more principled semantic explanation of the LR score.

## Sample 3: FN_attack

- Ground truth: `1`
- LR prediction / public `y_hat`: `0`
- LR integer score: `-307,632,372`
- Stage 3.3 old proxy top-3: Application, Protocol, TrafficVolume
- Stage 3.4 Exact SHAP top-3: Protocol, Application, ConnectionState
- Stage 3.4 proof status: `PASS` (witness 61 ms, prove 1006 ms, verify 605 ms)

### Group Values

| Group | Old grouped attribution | Exact SHAP phi_int | abs(phi_int) | In old top-3 | In Exact top-3 |
|---|---:|---:|---:|---|---|
| Protocol | 1,462,304,768 | -2,059,487,864 | 2,059,487,864 | yes | yes |
| Application | 4,262,854,656 | 1,432,654,365 | 1,432,654,365 | yes | yes |
| ConnectionState | 57,540,608 | -260,335,315 | 260,335,315 | no | yes |
| Ports | 52,314,983 | 51,311,239 | 51,311,239 | no | no |
| TrafficVolume | 487,883,929 | -233,813,764 | 233,813,764 | yes | no |

### Interpretation

This false-negative attack is useful for self-assessment: the proof verifies the model's actual normal prediction and its Exact SHAP explanation, not the ground-truth label. The case separates cryptographic correctness from IDS accuracy and is important for the limitations discussion.
