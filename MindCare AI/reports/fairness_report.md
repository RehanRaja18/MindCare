# Occupation Fairness Report

## Scope

- Model: tuned Random Forest from `reports/tuning_results.json`.
- Training: existing `X_train`/`y_train` only; no refitting of preprocessing.
- Evaluation: existing `X_val`/`y_val` only.
- Occupation: original unencoded CSV column joined by reproduced validation row index.
- Validation rows: 1650; seed: 42.
- Meaningful recall gap: subgroup recall at least 0.10 below overall validation recall.

## Overall Validation Precision and Recall

| Class | Support | Precision | Recall |
|---|---:|---:|---:|
| High | 292 | 0.7432 | 0.7432 |
| Mild | 440 | 0.8715 | 0.6318 |
| Minimal | 367 | 0.8105 | 0.9673 |
| Moderate | 448 | 0.7588 | 0.7723 |
| Severe | 103 | 0.6966 | 0.9806 |

## Occupation Subgroup Metrics

### Artist

| Class | Support | Precision | Recall |
|---|---:|---:|---:|
| High | 19 | 0.7368 | 0.7368 |
| Mild | 35 | 0.8125 | 0.7429 |
| Minimal | 30 | 0.9032 | 0.9333 |
| Moderate | 38 | 0.7838 | 0.7632 |
| Severe | 6 | 0.6667 | 1.0000 |

### Athlete

| Class | Support | Precision | Recall |
|---|---:|---:|---:|
| High | 16 | 0.6000 | 0.7500 |
| Mild | 16 | 0.9091 | 0.6250 |
| Minimal | 24 | 0.8889 | 1.0000 |
| Moderate | 34 | 0.8065 | 0.7353 |
| Severe | 10 | 0.9091 | 1.0000 |

### Chef

| Class | Support | Precision | Recall |
|---|---:|---:|---:|
| High | 25 | 0.8261 | 0.7600 |
| Mild | 42 | 0.9259 | 0.5952 |
| Minimal | 25 | 0.7273 | 0.9600 |
| Moderate | 27 | 0.6765 | 0.8519 |
| Severe | 12 | 0.7857 | 0.9167 |

### Doctor

| Class | Support | Precision | Recall |
|---|---:|---:|---:|
| High | 32 | 0.8889 | 0.7500 |
| Mild | 32 | 0.9000 | 0.5625 |
| Minimal | 31 | 0.7750 | 1.0000 |
| Moderate | 37 | 0.7805 | 0.8649 |
| Severe | 8 | 0.6667 | 1.0000 |

### Engineer

| Class | Support | Precision | Recall |
|---|---:|---:|---:|
| High | 18 | 0.6667 | 0.7778 |
| Mild | 35 | 0.8571 | 0.6857 |
| Minimal | 23 | 0.7667 | 1.0000 |
| Moderate | 33 | 0.7857 | 0.6667 |
| Severe | 8 | 0.8000 | 1.0000 |

### Freelancer

| Class | Support | Precision | Recall |
|---|---:|---:|---:|
| High | 22 | 0.7391 | 0.7727 |
| Mild | 36 | 0.8929 | 0.6944 |
| Minimal | 37 | 0.8780 | 0.9730 |
| Moderate | 33 | 0.7812 | 0.7576 |
| Severe | 4 | 0.5000 | 1.0000 |

### Lawyer

| Class | Support | Precision | Recall |
|---|---:|---:|---:|
| High | 14 | 0.6875 | 0.7857 |
| Mild | 34 | 0.8571 | 0.7059 |
| Minimal | 29 | 0.7941 | 0.9310 |
| Moderate | 29 | 0.8462 | 0.7586 |
| Severe | 9 | 0.8182 | 1.0000 |

### Musician

| Class | Support | Precision | Recall |
|---|---:|---:|---:|
| High | 17 | 0.6667 | 0.7059 |
| Mild | 32 | 0.9091 | 0.6250 |
| Minimal | 31 | 0.8108 | 0.9677 |
| Moderate | 36 | 0.8286 | 0.8056 |
| Severe | 6 | 0.6000 | 1.0000 |

### Nurse

| Class | Support | Precision | Recall |
|---|---:|---:|---:|
| High | 26 | 0.7667 | 0.8846 |
| Mild | 33 | 0.7619 | 0.4848 |
| Minimal | 29 | 0.8000 | 0.9655 |
| Moderate | 49 | 0.7755 | 0.7755 |
| Severe | 8 | 0.8000 | 1.0000 |

### Other

| Class | Support | Precision | Recall |
|---|---:|---:|---:|
| High | 25 | 0.8095 | 0.6800 |
| Mild | 38 | 0.8636 | 0.5000 |
| Minimal | 25 | 0.7500 | 0.9600 |
| Moderate | 36 | 0.6977 | 0.8333 |
| Severe | 11 | 0.6471 | 1.0000 |

### Scientist

| Class | Support | Precision | Recall |
|---|---:|---:|---:|
| High | 31 | 0.8333 | 0.6452 |
| Mild | 33 | 0.8333 | 0.6061 |
| Minimal | 32 | 0.8611 | 0.9688 |
| Moderate | 28 | 0.6111 | 0.7857 |
| Severe | 8 | 0.5833 | 0.8750 |

### Student

| Class | Support | Precision | Recall |
|---|---:|---:|---:|
| High | 17 | 0.6111 | 0.6471 |
| Mild | 36 | 0.9310 | 0.7500 |
| Minimal | 30 | 0.8824 | 1.0000 |
| Moderate | 27 | 0.7200 | 0.6667 |
| Severe | 8 | 0.6667 | 1.0000 |

### Teacher

| Class | Support | Precision | Recall |
|---|---:|---:|---:|
| High | 30 | 0.7188 | 0.7667 |
| Mild | 38 | 0.8889 | 0.6316 |
| Minimal | 21 | 0.6786 | 0.9048 |
| Moderate | 41 | 0.7949 | 0.7561 |
| Severe | 5 | 0.5556 | 1.0000 |

## Clinically Important Recall Flags

The following occupation/class combinations meet the predefined meaningful-gap rule:

| Occupation | Class | Subgroup Recall | Overall Recall | Gap |
|---|---|---:|---:|---:|
| Scientist | Severe | 0.8750 | 0.9806 | 0.1056 |

## Interpretation

These are prototype subgroup estimates on a synthetic dataset and should not be interpreted as clinical validation.
Low subgroup support, especially for Severe, can make recall estimates unstable and should be considered before drawing conclusions.
