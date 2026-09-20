# MindCare Anxiety Level API — Usage Guide

FastAPI service exposing the tuned Random Forest (3-class Anxiety Level target) for
single-patient inference. Source: [`src/api/main.py`](../src/api/main.py).

**Decision-support only.** Per `CLAUDE.md`'s critical workflow constraint, no prediction from
this service may reach a patient without psychologist review. The service itself has no concept
of a patient-facing UI or a review workflow — the calling backend is responsible for routing
every prediction through psychologist review before any patient sees it.

## Running the service

```bash
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

Model, preprocessor, and label encoder are loaded **once at startup**, not per-request. Startup
takes a moment (model artifacts are loaded from `data/processed/`); wait for a healthy `/health`
response before sending real traffic.

## `GET /health`

Returns whether the service's ML artifacts loaded successfully. Call this before sending
prediction traffic, and optionally poll it as a liveness/readiness check.

**Response — 200:**
```json
{
  "status": "ok",
  "model_loaded": true,
  "preprocessor_loaded": true,
  "label_encoder_loaded": true
}
```

`status` is `"not_ready"` if any artifact failed to load (all three booleans would then not all
be `true`). This endpoint never returns a non-200 status — check the body, not just the status
code.

## `POST /predict`

### Request body

All **17 raw feature values**, one patient per request. JSON keys are the **exact column names**
used throughout this project (matching `CLAUDE.md`'s feature list and the raw CSV) — not
snake_case, not abbreviated.

| JSON key | Type | Valid values |
|---|---|---|
| `Age` | number | any value; physically implausible values (e.g. negative) are rejected — see below |
| `Sleep Hours` | number | — |
| `Physical Activity (hrs/week)` | number | — |
| `Caffeine Intake (mg/day)` | number | — |
| `Alcohol Consumption (drinks/week)` | number | — |
| `Stress Level (1-10)` | number | intended range 1-10 |
| `Heart Rate (bpm)` | number | — |
| `Breathing Rate (breaths/min)` | number | — |
| `Sweating Level (1-5)` | number | intended range 1-5 |
| `Therapy Sessions (per month)` | number | — |
| `Diet Quality (1-10)` | number | intended range 1-10 |
| `Occupation` | string | one of: `Artist`, `Athlete`, `Chef`, `Doctor`, `Engineer`, `Freelancer`, `Lawyer`, `Musician`, `Nurse`, `Other`, `Scientist`, `Student`, `Teacher` |
| `Smoking` | string | `"Yes"` or `"No"` |
| `Family History of Anxiety` | string | `"Yes"` or `"No"` |
| `Dizziness` | string | `"Yes"` or `"No"` |
| `Medication` | string | `"Yes"` or `"No"` |
| `Recent Major Life Event` | string | `"Yes"` or `"No"` |

All 17 fields are required. Numbers may be sent as JSON integers or floats (both are accepted).

### Validation behavior (runs before any prediction)

Every request is checked against physically-plausible bounds
(`src/inference/input_validation.py`) before the model is touched:

- **Physically impossible** (e.g. `Age: -5`, `Stress Level (1-10): 250`, an unrecognized
  `Occupation`, a missing field): the request is **rejected**. No prediction is attempted.
  Response is **HTTP 422** with a `detail` string listing every violation found.
- **Valid, but outside what the training data ever contained** (e.g. `Stress Level (1-10): 10.5`,
  a half-point reading): the request **proceeds normally**, but the response's `warnings` array
  is non-empty, flagging exactly which field(s) are in untested territory.
- **Malformed JSON, wrong type, or an `Occupation`/`Yes`-`No` value not in the allowed list**:
  also rejected with **HTTP 422**, via standard FastAPI/Pydantic request validation (a different
  code path than the physical-plausibility check above, but the same HTTP status).

### Response body — 200 (success)

```json
{
  "predicted_class": "Low",
  "probabilities": {
    "Low": 0.8905,
    "Medium": 0.1081,
    "High": 0.0014
  },
  "uncertainty_flag": false,
  "warnings": []
}
```

- `predicted_class`: one of `"Low"`, `"Medium"`, `"High"` — the model's top prediction.
- `probabilities`: full 3-class probability distribution, keys always `Low`/`Medium`/`High`,
  values sum to 1.0.
- `uncertainty_flag`: `true` if `probabilities.High >= 0.10` — the production
  uncertainty-flagging rule (`src/models/uncertainty_flagging.py`). This means **"recommend
  priority review"**, not "reject this prediction" — every prediction should go through
  psychologist review regardless of this flag; it only reprioritizes attention.
- `warnings`: list of human-readable strings for any field that was valid but outside the
  training data's observed range. Empty list if none.

### Response body — 422 (rejected)

```json
{
  "detail": "Input validation failed with 1 error(s):\n  - Age=-5.0 is outside the physically plausible range [0, 120] (0-120: outer bound of recorded human lifespan.)"
}
```

`detail` is a single string (may contain multiple `\n`-separated bullet points if more than one
field failed validation). There is no prediction in a 422 response.

## Full worked example

**Request:**
```http
POST /predict HTTP/1.1
Content-Type: application/json

{
  "Age": 29,
  "Sleep Hours": 8.2,
  "Physical Activity (hrs/week)": 5.5,
  "Caffeine Intake (mg/day)": 80,
  "Alcohol Consumption (drinks/week)": 1,
  "Stress Level (1-10)": 2,
  "Heart Rate (bpm)": 68,
  "Breathing Rate (breaths/min)": 14,
  "Sweating Level (1-5)": 1,
  "Therapy Sessions (per month)": 0,
  "Diet Quality (1-10)": 9,
  "Occupation": "Teacher",
  "Smoking": "No",
  "Family History of Anxiety": "No",
  "Dizziness": "No",
  "Medication": "No",
  "Recent Major Life Event": "No"
}
```

**Response (200):**
```json
{
  "predicted_class": "Low",
  "probabilities": {
    "Low": 0.8905276322113964,
    "Medium": 0.10805914450531594,
    "High": 0.001413223283288162
  },
  "uncertainty_flag": false,
  "warnings": []
}
```

This exact request/response pair was captured from a live run of the service (see
`tests/test_api.py`) — not hand-written.

## Known limitations to be aware of when integrating

This model has documented weaknesses that matter for how a caller should treat its output — see
[`docs/model_card.md`](model_card.md) for the full picture, in particular:
- The model is fragile to missing/corrupted values in `Stress Level (1-10)` and
  `Therapy Sessions (per month)` specifically (Phase 19 robustness findings).
- Raw probabilities are not well-calibrated — don't present `probabilities` to an end user as a
  literal confidence percentage.
- This is a prototype/research model on a very likely synthetic dataset — never represent its
  output as clinically validated, and never let it bypass psychologist review.
