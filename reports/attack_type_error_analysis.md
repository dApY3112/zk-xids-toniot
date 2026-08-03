# Attack-Type Post-hoc Error Analysis
Generated: 2026-05-27T20:00:35+00:00 (UTC)

## Purpose
`type` is not used for binary model training. This report uses `type` only after prediction to identify which attack families contribute most to false negatives under each operating point.

## Alignment checks
- Test rows: `502628`
- Metadata/test label mismatches: `0`
- Minimum attack-type count reported: `100`

## xgboost

### Operating point summary
| Point | Threshold | Attack Recall | Normal Recall (Spec) | FPR | MCC | Confusion tn/fp/fn/tp |
|---|---:|---:|---:|---:|---:|---|
| default_0.5 | 0.500000 | 0.996814 | 0.996838 | 0.003162 | 0.956512 | 17970/57/1544/483057 |
| low_fpr | 0.807750 | 0.992897 | 0.998391 | 0.001609 | 0.912188 | 17998/29/3442/481159 |
| balanced_mcc | 0.489287 | 0.996865 | 0.996727 | 0.003273 | 0.957090 | 17968/59/1519/483082 |
| high_recall | 0.984017 | 0.946216 | 0.999834 | 0.000166 | 0.621897 | 18024/3/26064/458537 |

### Highest false-negative rates by attack type
Rows are sorted by false-negative rate, then support size. Only true attack rows are included.

#### default_0.5

| Attack type | n | FN | TP | Attack recall | FN rate |
|---|---:|---:|---:|---:|---:|
| ransomware | 1620 | 173 | 1447 | 0.893210 | 0.106790 |
| ddos | 138896 | 648 | 138248 | 0.995335 | 0.004665 |
| injection | 10216 | 44 | 10172 | 0.995693 | 0.004307 |
| scanning | 160659 | 438 | 160221 | 0.997274 | 0.002726 |
| xss | 47543 | 77 | 47466 | 0.998380 | 0.001620 |
| dos | 75666 | 122 | 75544 | 0.998388 | 0.001612 |
| password | 38581 | 27 | 38554 | 0.999300 | 0.000700 |
| backdoor | 11396 | 3 | 11393 | 0.999737 | 0.000263 |

#### balanced_mcc

| Attack type | n | FN | TP | Attack recall | FN rate |
|---|---:|---:|---:|---:|---:|
| ransomware | 1620 | 168 | 1452 | 0.896296 | 0.103704 |
| ddos | 138896 | 637 | 138259 | 0.995414 | 0.004586 |
| injection | 10216 | 44 | 10172 | 0.995693 | 0.004307 |
| scanning | 160659 | 433 | 160226 | 0.997305 | 0.002695 |
| xss | 47543 | 77 | 47466 | 0.998380 | 0.001620 |
| dos | 75666 | 120 | 75546 | 0.998414 | 0.001586 |
| password | 38581 | 25 | 38556 | 0.999352 | 0.000648 |
| backdoor | 11396 | 3 | 11393 | 0.999737 | 0.000263 |

#### low_fpr

| Attack type | n | FN | TP | Attack recall | FN rate |
|---|---:|---:|---:|---:|---:|
| ransomware | 1620 | 344 | 1276 | 0.787654 | 0.212346 |
| injection | 10216 | 158 | 10058 | 0.984534 | 0.015466 |
| ddos | 138896 | 1294 | 137602 | 0.990684 | 0.009316 |
| xss | 47543 | 288 | 47255 | 0.993942 | 0.006058 |
| scanning | 160659 | 972 | 159687 | 0.993950 | 0.006050 |
| dos | 75666 | 282 | 75384 | 0.996273 | 0.003727 |
| password | 38581 | 79 | 38502 | 0.997952 | 0.002048 |
| backdoor | 11396 | 9 | 11387 | 0.999210 | 0.000790 |

#### high_recall

| Attack type | n | FN | TP | Attack recall | FN rate |
|---|---:|---:|---:|---:|---:|
| ransomware | 1620 | 1541 | 79 | 0.048765 | 0.951235 |
| injection | 10216 | 1143 | 9073 | 0.888117 | 0.111883 |
| scanning | 160659 | 10403 | 150256 | 0.935248 | 0.064752 |
| password | 38581 | 2164 | 36417 | 0.943910 | 0.056090 |
| ddos | 138896 | 7369 | 131527 | 0.946946 | 0.053054 |
| xss | 47543 | 1430 | 46113 | 0.969922 | 0.030078 |
| dos | 75666 | 1982 | 73684 | 0.973806 | 0.026194 |
| backdoor | 11396 | 10 | 11386 | 0.999122 | 0.000878 |

### Normal false alarms
- Normal rows: `18027`, false positives at default 0.5: `57`, FPR: `0.003162`.

## logistic_regression

### Operating point summary
| Point | Threshold | Attack Recall | Normal Recall (Spec) | FPR | MCC | Confusion tn/fp/fn/tp |
|---|---:|---:|---:|---:|---:|---|
| default_0.5 | 0.500000 | 0.935017 | 0.911189 | 0.088811 | 0.535818 | 16426/1601/31491/453110 |
| low_fpr | 0.938810 | 0.504396 | 0.990015 | 0.009985 | 0.183942 | 17847/180/240170/244431 |
| balanced_mcc | 0.088104 | 0.994600 | 0.711766 | 0.288234 | 0.761031 | 12831/5196/2617/481984 |
| high_recall | 0.081597 | 0.994903 | 0.681755 | 0.318245 | 0.745296 | 12290/5737/2470/482131 |

### Highest false-negative rates by attack type
Rows are sorted by false-negative rate, then support size. Only true attack rows are included.

#### default_0.5

| Attack type | n | FN | TP | Attack recall | FN rate |
|---|---:|---:|---:|---:|---:|
| ransomware | 1620 | 1495 | 125 | 0.077160 | 0.922840 |
| injection | 10216 | 2343 | 7873 | 0.770654 | 0.229346 |
| ddos | 138896 | 16554 | 122342 | 0.880817 | 0.119183 |
| scanning | 160659 | 7710 | 152949 | 0.952010 | 0.047990 |
| xss | 47543 | 1468 | 46075 | 0.969123 | 0.030877 |
| dos | 75666 | 1833 | 73833 | 0.975775 | 0.024225 |
| password | 38581 | 75 | 38506 | 0.998056 | 0.001944 |
| backdoor | 11396 | 5 | 11391 | 0.999561 | 0.000439 |

#### balanced_mcc

| Attack type | n | FN | TP | Attack recall | FN rate |
|---|---:|---:|---:|---:|---:|
| ransomware | 1620 | 773 | 847 | 0.522840 | 0.477160 |
| injection | 10216 | 115 | 10101 | 0.988743 | 0.011257 |
| xss | 47543 | 459 | 47084 | 0.990346 | 0.009654 |
| dos | 75666 | 425 | 75241 | 0.994383 | 0.005617 |
| ddos | 138896 | 528 | 138368 | 0.996199 | 0.003801 |
| scanning | 160659 | 290 | 160369 | 0.998195 | 0.001805 |
| password | 38581 | 19 | 38562 | 0.999508 | 0.000492 |
| backdoor | 11396 | 4 | 11392 | 0.999649 | 0.000351 |

#### low_fpr

| Attack type | n | FN | TP | Attack recall | FN rate |
|---|---:|---:|---:|---:|---:|
| ransomware | 1620 | 1616 | 4 | 0.002469 | 0.997531 |
| injection | 10216 | 9845 | 371 | 0.036316 | 0.963684 |
| xss | 47543 | 45182 | 2361 | 0.049660 | 0.950340 |
| password | 38581 | 35835 | 2746 | 0.071175 | 0.928825 |
| scanning | 160659 | 112835 | 47824 | 0.297674 | 0.702326 |
| ddos | 138896 | 31237 | 107659 | 0.775105 | 0.224895 |
| dos | 75666 | 3590 | 72076 | 0.952555 | 0.047445 |
| backdoor | 11396 | 7 | 11389 | 0.999386 | 0.000614 |

#### high_recall

| Attack type | n | FN | TP | Attack recall | FN rate |
|---|---:|---:|---:|---:|---:|
| ransomware | 1620 | 700 | 920 | 0.567901 | 0.432099 |
| injection | 10216 | 115 | 10101 | 0.988743 | 0.011257 |
| xss | 47543 | 454 | 47089 | 0.990451 | 0.009549 |
| dos | 75666 | 425 | 75241 | 0.994383 | 0.005617 |
| ddos | 138896 | 464 | 138432 | 0.996659 | 0.003341 |
| scanning | 160659 | 286 | 160373 | 0.998220 | 0.001780 |
| password | 38581 | 18 | 38563 | 0.999533 | 0.000467 |
| backdoor | 11396 | 4 | 11392 | 0.999649 | 0.000351 |

### Normal false alarms
- Normal rows: `18027`, false positives at default 0.5: `1601`, FPR: `0.088811`.

## Interpretation
- This analysis strengthens the IDS evaluation because it shows which attack families are missed, rather than only reporting aggregate binary metrics.
- Since `type` is excluded from training and used only post hoc, the report does not introduce target leakage into the binary model.
