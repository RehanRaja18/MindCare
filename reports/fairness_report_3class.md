# Occupation Fairness Report — 3-Class Anxiety Level Target

## Scope

- Model: tuned Random Forest from `reports/tuning_results_3class.json`.
- Training: existing `X_train`/`y_train` only; no refitting of preprocessing.
- Evaluation: existing `X_val`/`y_val` only.
- Occupation: original unencoded CSV column joined via `val_original_idx` (saved directly by `rebuild_preprocessor.py` — no reconstruction needed).
- Validation rows: 1650; seed: 42.
- Meaningful recall gap: subgroup recall at least 0.10 below overall validation recall, for the High class only.
- Low-confidence flag: fewer than 15 validation rows for that occupation/class cell (same convention as the 5-class fairness report).

## Overall Validation Precision and Recall

| Class | Support | Precision | Recall |
|---|---:|---:|---:|
| Low | 778 | 0.7806 | 0.7545 |
| Medium | 707 | 0.7223 | 0.7652 |
| High | 165 | 0.9933 | 0.8970 |

## Occupation Subgroup Metrics

### Artist

| Class | Support | Precision | Recall |
|---|---:|---:|---:|
| Low | 63 | 0.7460 | 0.7460 |
| Medium | 55 | 0.7091 | 0.7091 |
| High | 10 | 1.0000 | 1.0000 |

### Athlete

| Class | Support | Precision | Recall |
|---|---:|---:|---:|
| Low | 42 | 0.8205 | 0.7619 |
| Medium | 46 | 0.7959 | 0.8478 |
| High | 12 | 1.0000 | 1.0000 |

### Chef

| Class | Support | Precision | Recall |
|---|---:|---:|---:|
| Low | 66 | 0.8136 | 0.7273 |
| Medium | 49 | 0.6552 | 0.7755 |
| High | 16 | 1.0000 | 0.8750 |

### Doctor

| Class | Support | Precision | Recall |
|---|---:|---:|---:|
| Low | 55 | 0.7414 | 0.7818 |
| Medium | 73 | 0.8143 | 0.7808 |
| High | 12 | 0.9167 | 0.9167 |

### Engineer

| Class | Support | Precision | Recall |
|---|---:|---:|---:|
| Low | 50 | 0.7736 | 0.8200 |
| Medium | 53 | 0.7736 | 0.7736 |
| High | 14 | 1.0000 | 0.7857 |

### Freelancer

| Class | Support | Precision | Recall |
|---|---:|---:|---:|
| Low | 67 | 0.7826 | 0.8060 |
| Medium | 56 | 0.7455 | 0.7321 |
| High | 9 | 1.0000 | 0.8889 |

### Lawyer

| Class | Support | Precision | Recall |
|---|---:|---:|---:|
| Low | 50 | 0.6964 | 0.7800 |
| Medium | 54 | 0.7708 | 0.6852 |
| High | 11 | 1.0000 | 1.0000 |

### Musician

| Class | Support | Precision | Recall |
|---|---:|---:|---:|
| Low | 70 | 0.8197 | 0.7143 |
| Medium | 42 | 0.6078 | 0.7381 |
| High | 10 | 1.0000 | 1.0000 |

### Nurse

| Class | Support | Precision | Recall |
|---|---:|---:|---:|
| Low | 67 | 0.7667 | 0.6866 |
| Medium | 65 | 0.6892 | 0.7846 |
| High | 13 | 1.0000 | 0.8462 |

### Other

| Class | Support | Precision | Recall |
|---|---:|---:|---:|
| Low | 68 | 0.8246 | 0.6912 |
| Medium | 49 | 0.6393 | 0.7959 |
| High | 18 | 1.0000 | 0.9444 |

### Scientist

| Class | Support | Precision | Recall |
|---|---:|---:|---:|
| Low | 55 | 0.7414 | 0.7818 |
| Medium | 61 | 0.7419 | 0.7541 |
| High | 16 | 1.0000 | 0.7500 |

### Student

| Class | Support | Precision | Recall |
|---|---:|---:|---:|
| Low | 63 | 0.8281 | 0.8413 |
| Medium | 41 | 0.7143 | 0.7317 |
| High | 14 | 1.0000 | 0.8571 |

### Teacher

| Class | Support | Precision | Recall |
|---|---:|---:|---:|
| Low | 62 | 0.8000 | 0.7097 |
| Medium | 63 | 0.7324 | 0.8254 |
| High | 10 | 1.0000 | 0.9000 |

## Clinically Important Recall Flags (High class)

The following occupations meet the predefined meaningful-gap rule for the High class:

| Occupation | Support (High) | Subgroup Recall | Overall Recall | Gap | Low confidence (<15 rows)? |
|---|---:|---:|---:|---:|---|
| Scientist | 16 | 0.7500 | 0.8970 | 0.1470 | no |
| Engineer | 14 | 0.7857 | 0.8970 | 0.1113 | YES — low confidence |

## Interpretation

These are prototype subgroup estimates on a synthetic dataset and should not be interpreted as clinical validation.
High-class support per occupation is small (~10% of an already-small per-occupation validation sample), so any flagged cell with fewer than 15 rows is explicitly marked low-confidence: a single misclassified row can swing recall by a large margin at that sample size, and these should not be treated as reliable evidence of a real subgroup gap without a larger sample.
