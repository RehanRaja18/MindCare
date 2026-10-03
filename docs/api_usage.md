# MindCare Anxiety Level API — Usage Guide

FastAPI service exposing the canonical XGBoost model (3-class Anxiety Level target; XGBoost
since 2026-09-28, see [`reports/model_comparison_12feature.md`](../reports/model_comparison_12feature.md);
11 features since 2026-10-02, see
[`reports/feature_reduction_sweatlevel_3class.md`](../reports/feature_reduction_sweatlevel_3class.md))
for single-patient inference. Source: [`src/api/main.py`](../src/api/main.py).

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

**11 model features**, one patient per request — the canonical model was reduced from 17 to 11
features (`Age`, `Alcohol Consumption (drinks/week)`, `Dizziness`, `Smoking`,
`Recent Major Life Event`, and `Medication` were dropped: they were the 6 lowest-ranked features
by SHAP importance and removing them cost no measurable accuracy — see
[`reports/feature_reduction_3class.md`](../reports/feature_reduction_3class.md)), then `Age` was
restored as a clinical/UX decision
([`reports/feature_addition_age_3class.md`](../reports/feature_addition_age_3class.md)). On
2026-10-02 `Sweating Level (1-5)` was removed as well: it was the least important of the 12 inputs,
and dropping it changed nothing measurable for High patients
([`reports/feature_reduction_sweatlevel_3class.md`](../reports/feature_reduction_sweatlevel_3class.md)).
**The dropped fields (those 5 and `Sweating Level (1-5)`) are no longer part of the request schema
at all** — if you send them anyway, they are silently ignored (not an error), since old
integrations that haven't been updated yet will still get a prediction rather than a hard failure.

JSON keys are the **exact column names** used throughout this project (matching `CLAUDE.md`'s
feature list and the raw CSV) — not snake_case, not abbreviated — **except caffeine and stress**:
caffeine is collected as four everyday serving counts instead of a raw milligram figure, and
Stress Level is collected as the four PSS-4 questionnaire answers instead of a raw 1-10 rating
(see both sections below).

| JSON key | Type | Valid values |
|---|---|---|
| `Age` | integer | **18–49 supported** (0–120 accepted by the schema; anything outside 18–49 is rejected — see "Supported age range" below) |
| `Sleep Hours` | number | — |
| `Physical Activity (hrs/week)` | number | — |
| `cups_of_coffee` | integer | 0–20 |
| `cups_of_tea` | integer | 0–20 |
| `energy_drinks` | integer | 0–20 |
| `cans_of_soda` | integer | 0–20 |
| `pss_uncontrollable` | integer | 0–4 |
| `pss_confident` | integer | 0–4 (**reverse-scored**) |
| `pss_going_your_way` | integer | 0–4 (**reverse-scored**) |
| `pss_difficulties_piling_up` | integer | 0–4 |
| `Heart Rate (bpm)` | number | — |
| `Breathing Rate (breaths/min)` | number | — |
| `Therapy Sessions (per month)` | number | — |
| `Diet Quality (1-10)` | number | intended range 1-10 |
| `Occupation` | string | one of: `Artist`, `Athlete`, `Chef`, `Doctor`, `Engineer`, `Freelancer`, `Lawyer`, `Musician`, `Nurse`, `Other`, `Scientist`, `Student`, `Teacher` |
| `Family History of Anxiety` | string | `"Yes"` or `"No"` |

All 17 fields above are required. Numeric fields may be sent as JSON integers or floats (both
accepted); `Age`, the 4 caffeine fields, and the 4 PSS fields must be whole numbers. A raw
`Stress Level (1-10)` key is **no longer accepted as input** — if an older integration still
sends it, it is silently ignored and the value computed from the PSS answers is used instead.

#### Supported age range: 18–49

The model only makes a prediction for ages **18 to 49 inclusive**. Any other age returns
**HTTP 422**, but the two sides mean different things for the platform (decided 2026-09-28):

| Age | Platform rule | 422 `detail` says | What the calling system should do |
|---|---|---|---|
| Under 18 | **Cannot register for MindCare at all** | `Age=… is under 18 - not eligible for MindCare (adults only; registration should have blocked this user)` | Nothing to route — this should never happen. It means the web app's registration age check failed; treat it as a bug to fix there. |
| 18–49 | Normal use | — (HTTP 200, prediction returned) | Send the prediction to psychologist review as usual. |
| 50 and over | **Can register**, but gets no AI pre-assessment | `Age=… is outside the supported range for AI pre-assessment [18, 49] - … refer this person directly to a psychologist` | Redirect the user straight to a psychologist. |

The **under-18 block belongs in the web app's registration**. This API only has a backstop
check, and it deliberately does *not* suggest a psychologist referral for minors, because they
shouldn't be on the platform at all.

- **Why under 18:** the training data contains no one under 18, and physiological norms (heart
  rate, breathing rate) and consent rules differ for minors.
- **Why 50 and over:** these ages are in the training data, but the share of High-anxiety cases
  drops from 12–15% below age 50 to about 1% from 50 on. That's almost certainly an artifact of
  a very likely synthetic dataset. With so few High examples at these ages, there is almost no
  evidence the model can recognise High anxiety in older users. The Random Forest that preceded
  XGBoost clearly learned the artifact: for otherwise identical people, its mean P(High) fell
  from 0.90 at age 49 to 0.63 at 55. XGBoost barely does (0.885 → 0.863), but a model ignoring a
  data gap doesn't fill it. Missing High anxiety is the most dangerous error, so the model is
  not used for these ages.

This is a scope limit set by the training data, not a clinical rule. It could be revisited with
real data that covers these ages.

#### Caffeine: serving counts, not milligrams

The underlying model was trained on `Caffeine Intake (mg/day)`, but asking a patient-facing form
for an exact milligram figure isn't realistic — nobody knows that number. Instead, the API takes
four everyday serving counts and converts them internally
(`src/api/main.py`, `estimate_caffeine_mg()`), using fixed **average** mg-per-serving figures
(commonly-cited USDA/Mayo-Clinic-style averages — **an approximation, not a measurement**; actual
caffeine content varies by brand, brew strength, and serving size):

| Serving | Assumed mg |
|---|---:|
| 1 cup of coffee | 95 |
| 1 cup of tea | 47 |
| 1 energy drink | 80 |
| 1 can of soda | 35 |

The computed total is what actually reaches the model, is checked against the same
`Caffeine Intake (mg/day)` plausibility bounds as before (0–1200mg hard range, 0–599mg observed
training range — see below), and is returned in the response as `estimated_caffeine_mg` so a
caller can see/display/log exactly what was assumed.

#### Stress Level: PSS-4 answers, not a raw 1-10 rating

> **Read this before relying on `estimated_stress_level`.**
> - **The questionnaire is validated.** The four questions are the 4-item Perceived Stress Scale
>   (PSS-4), a published, widely used instrument: Cohen, S., Kamarck, T., & Mermelstein, R.
>   (1983). *A global measure of perceived stress.* Journal of Health and Social Behavior,
>   24(4), 385–396. Scoring the answers to a 0–16 PSS-4 total follows that standard.
> - **The mapping to 1–10 is not validated.** Converting the 0–16 total into the model's 1–10
>   Stress Level scale is **this project's own invented convention** — a straight linear
>   rescale. It has not been independently validated, and there is no evidence that a
>   PSS-derived "6" means the same thing as a "6" in the training data. The dataset's
>   `Stress Level (1-10)` column was a self-rating with no defined anchors and was never
>   measured with the PSS; the two only share a low-to-high direction and a range.

The model was trained on `Stress Level (1-10)`, an unanchored self-rating. Instead of asking for
that number directly, the API asks the four PSS-4 questions — *"In the last month, how often
have you…"* — each answered `0` = Never, `1` = Almost never, `2` = Sometimes, `3` = Fairly
often, `4` = Very often:

| JSON key | Question ("…in the last month, how often have you…") | Scoring |
|---|---|---|
| `pss_uncontrollable` | felt that you were unable to control the important things in your life? | as answered |
| `pss_confident` | felt confident about your ability to handle your personal problems? | **reversed: `4 − answer`** |
| `pss_going_your_way` | felt that things were going your way? | **reversed: `4 − answer`** |
| `pss_difficulties_piling_up` | felt difficulties were piling up so high that you could not overcome them? | as answered |

`pss_confident` and `pss_going_your_way` are positively worded — answering "Very often" (4) to
them means *less* stress — so they are reverse-scored before summing. A consequence worth
knowing: **all-0 answers and all-4 answers both land mid-scale** (total 8 → Stress Level 6), not
at the extremes. The least-stressed answer pattern is `0, 4, 4, 0` (→ 1); the most-stressed is
`4, 0, 0, 4` (→ 10).

The conversion (`src/inference/stress_scale.py`, `estimate_stress_level()`):

```
total        = pss_uncontrollable + (4 − pss_confident) + (4 − pss_going_your_way) + pss_difficulties_piling_up   # 0–16
stress_level = clamp(round_half_up(1 + total × 9/16), 1, 10)
```

The result is rounded to a whole number because the training data's Stress Level only ever holds
integers 1–10. Rounding is half-up, so a total of 8 (1 + 4.5 = 5.5) becomes 6. The computed
value is what reaches the model, is checked against the same `Stress Level (1-10)` bounds as
before, and is returned in the response as `estimated_stress_level`.

### Validation behavior (runs before any prediction)

Every request is checked against physically-plausible bounds
(`src/inference/input_validation.py`) before the model is touched — applied to the *computed*
caffeine mg value and the *computed* Stress Level, not the raw serving counts or PSS answers:

- **Physically impossible** (e.g. `Heart Rate (bpm): 9000`, `Age: -5`, a missing field, or a
  computed caffeine total over 1200mg — e.g. **15 cups of coffee = 1425mg** really does get
  rejected, it's not just a theoretical edge case): the request is **rejected**. No prediction
  is attempted. Response is **HTTP 422** with a `detail` string listing every violation found.
  (A PSS-derived Stress Level is always 1–10 by construction, so it can never trip this check;
  the check stays in place as a guard.)
- **Outside the supported age range**: **rejected with HTTP 422** as well, with a different
  message per side. `Age: 16` → "not eligible for MindCare", with no referral (registration
  should have blocked them). `Age: 55` → "refer this person directly to a psychologist". See
  "Supported age range" above.
- **Valid, but outside what the training data ever contained** (e.g. **8 cups of coffee =
  760mg**, above the observed 0-599mg training range but below the 1200mg hard cutoff): the
  request **proceeds normally**, but the
  response's `warnings` array is non-empty, flagging exactly which field(s) are in untested
  territory.
- **Malformed JSON, wrong type, an `Occupation`/`Yes`-`No` value not in the allowed list, a
  serving count outside 0–20, or a PSS answer outside 0–4**: also rejected with **HTTP 422**,
  via standard FastAPI/Pydantic request validation (a different code path than the
  physical-plausibility check above, but the same HTTP status — and `detail` is a structured
  list rather than a string; see the 422 examples below). The 0–20 serving cap only catches
  obvious data-entry typos — a value inside that range but still unusually high (like the 8-or-15-cups examples above) is *not* rejected
  here; it flows through to the mg-value warn/reject check instead.

### Response body — 200 (success)

```json
{
  "predicted_class": "Low",
  "probabilities": {
    "Low": 0.9660,
    "Medium": 0.0333,
    "High": 0.0007
  },
  "uncertainty_flag": false,
  "warnings": [],
  "estimated_caffeine_mg": 95.0,
  "estimated_stress_level": 2
}
```

- `predicted_class`: one of `"Low"`, `"Medium"`, `"High"` — the model's top prediction.
- `probabilities`: full 3-class probability distribution, keys always `Low`/`Medium`/`High`,
  values sum to 1.0.
- `uncertainty_flag`: `true` if `probabilities.High >= 0.025` — the priority-review rule
  (`HIGH_PROBA_THRESHOLD` in `src/api/main.py`). It was 0.10 for the earlier Random Forest.
  XGBoost's probabilities are better calibrated, so it uses 0.025: the level at which it catches
  as many High cases as the old rule did on validation data (158 of 165). This means
  **"recommend priority review"**, not "reject this prediction" — every prediction should go through
  psychologist review regardless of this flag; it only reprioritizes attention.
- `warnings`: list of human-readable strings for any field that was valid but outside the
  training data's observed range. Empty list if none.
- `estimated_caffeine_mg`: the computed daily caffeine total (mg) the model actually used,
  derived from the 4 serving-count fields — shown so a caller can display/log exactly what was
  assumed rather than treating the conversion as a black box.
- `estimated_stress_level`: the integer 1–10 Stress Level the model actually used, computed
  from the 4 PSS answers (see "Stress Level: PSS-4 answers" above). Remember that the PSS-to-1–10
  mapping is this project's own unvalidated convention; display it as "the value the model
  used", not as a clinical stress score.

### Response body — 422 (rejected)

Physical-plausibility failure (`detail` is a string):

```json
{
  "detail": "Input validation failed with 1 error(s):\n  - Heart Rate (bpm)=9000.0 is outside the physically plausible range [30, 220] (30-220 bpm: standard clinical outer range, severe bradycardia to extreme tachycardia/maximal exertion.)"
}
```

`detail` is a single string (may contain multiple `\n`-separated bullet points if more than one
field failed validation). There is no prediction in a 422 response.

Schema failure, e.g. `pss_confident: 5` (`detail` is FastAPI/Pydantic's structured list):

```json
{
  "detail": [
    {
      "type": "less_than_equal",
      "loc": ["body", "pss_confident"],
      "msg": "Input should be less than or equal to 4",
      "input": 5,
      "ctx": {"le": 4}
    }
  ]
}
```

## Full worked example

**Request:**
```http
POST /predict HTTP/1.1
Content-Type: application/json

{
  "Age": 34,
  "Sleep Hours": 8.2,
  "Physical Activity (hrs/week)": 5.5,
  "cups_of_coffee": 1,
  "cups_of_tea": 0,
  "energy_drinks": 0,
  "cans_of_soda": 0,
  "pss_uncontrollable": 0,
  "pss_confident": 3,
  "pss_going_your_way": 4,
  "pss_difficulties_piling_up": 0,
  "Heart Rate (bpm)": 68,
  "Breathing Rate (breaths/min)": 14,
  "Therapy Sessions (per month)": 0,
  "Diet Quality (1-10)": 9,
  "Occupation": "Teacher",
  "Family History of Anxiety": "No"
}
```

**Response (200):**
```json
{
  "predicted_class": "Low",
  "probabilities": {
    "Low": 0.9660267233848572,
    "Medium": 0.03331087529659271,
    "High": 0.0006624316447414458
  },
  "uncertainty_flag": false,
  "warnings": [],
  "estimated_caffeine_mg": 95.0,
  "estimated_stress_level": 2
}
```

The PSS answers here give a total of 0 + (4−3) + (4−4) + 0 = 1, so 1 + 1 × 9/16 = 1.56, which
rounds to Stress Level 2. This exact request/response pair was captured from a live run of the
service (`uvicorn src.api.main:app`, 11-feature XGBoost model, 2026-10-02) — not hand-written.

## `POST /patient-summary`

A **psychologist-facing summary** for clinician review, **never to be shown to a patient directly**.
It returns everything `POST /predict` returns, plus an **estimated Severity tier** and the dataset's
**recommendation bundle** for that tier. A fixed `caveat` comes first in every response.

> **Caveat (the `caveat` field, the first key of every 200 response):** "Estimated severity and
> recommendation are a best-guess reconstruction (~88% accurate at best, lower given this model's own
> prediction error) from synthetic dataset templates. This is decision support for clinician review,
> not a recommendation to show a patient directly and not validated clinical advice."

### Request body

The same 17 fields as `POST /predict` (same validation, same 18-49 age rules, same 422 responses),
plus two **optional** fields. The model never uses them; they only fill slots in the bundle:

| JSON key | Type | Valid values | If omitted or `null` |
|---|---|---|---|
| `Gender` | string | `"Female"`, `"Male"`, `"Other"` | Protein slot reads `Protein: not provided (needs Gender)` |
| `Alcohol Consumption (drinks/week)` | number | 0–100 | Alcohol slot reads `Alcohol: not provided (needs Alcohol Consumption)` |

POST, not GET: the input is patient health data, which would otherwise be written to the server's
access logs as query parameters.

### Response body — 200

| Field | Meaning |
|---|---|
| `caveat` | The fixed caveat above. Always present. |
| `predicted_class`, `probabilities`, `uncertainty_flag`, `warnings`, `estimated_caffeine_mg`, `estimated_stress_level` | Identical to `/predict` for identical input. `predicted_class` is the **model's actual prediction**. |
| `estimated_severity_tier` | One of `Minimal (1-2)`, `Mild (3-4)`, `Moderate (5-6)`, `High (7-8)`, `Severe (9-10)`. **An estimate, not a model prediction** (see below). |
| `severity_tier_basis` | How the tier was chosen: `method`, `share_of_matching_patients` (how often this tier was right for dataset patients with the same predicted level and stress level; `null` if there were none) and `matching_patients`. |
| `recommendation_bundle` | `exercises`, `sleep_schedule`, `nutrition`: the dataset's fixed template text for the estimated tier, with the patient's Sleep Hours, caffeine (over/under 200 mg), alcohol (0 or not) and protein (by Gender) filled in. |

**How the tier is estimated.** The dataset's Severity is a band of (Anxiety Level + Stress Level) / 2.
The model never sees Anxiety Level, so the tier is the **most common tier among the 9,350 train +
validation patients with the same predicted 3-class level and the same PSS-derived Stress Level**.
Evidence and limits (`reports/recommendation_mapping_investigation.md`; `tests/test_api.py`):

- **Ceiling, with the true 3-class label:** 88.0% on the 9,350 rows the table is built from, and
  88.7% on a held-out 20% when rebuilt on the other 80%.
- **With this model's own predictions** (table built on the training rows only, scored on the
  validation rows): **78.3%** overall and 79.1% for ages 18-49. Expect about 4 in 5 tiers to be right.
- The bundle text comes from a very likely synthetic dataset and was never clinically validated.

**Response (200)**, captured from a live run (2026-10-02). The patient is `ambiguous_moderate` with PSS
answers 3/1/1/3, plus `"Gender": "Female"` and `"Alcohol Consumption (drinks/week)": 6`:
```json
{
  "caveat": "Estimated severity and recommendation are a best-guess reconstruction (~88% accurate at best, lower given this model's own prediction error) from synthetic dataset templates. This is decision support for clinician review, not a recommendation to show a patient directly and not validated clinical advice.",
  "predicted_class": "Medium",
  "probabilities": {"Low": 0.16264456510543823, "Medium": 0.8181824088096619, "High": 0.019173085689544678},
  "uncertainty_flag": false,
  "warnings": [],
  "estimated_caffeine_mg": 284.0,
  "estimated_stress_level": 8,
  "estimated_severity_tier": "Moderate (5-6)",
  "severity_tier_basis": {
    "method": "most common tier for this predicted level and stress level in the data",
    "share_of_matching_patients": 0.8493,
    "matching_patients": 657
  },
  "recommendation_bundle": {
    "exercises": "4-7-8 Breathing 3x/day 5 min each; Alternate Nostril Breathing 10 min/day; Walking/Swimming 30 min/day 5x/week; Yoga or Tai Chi 3x/week 45 min; PMR 20 min/day; Mindfulness Meditation 15 min/day",
    "sleep_schedule": "Target: 8 hrs/night; Fixed wake time daily; No screens 1 hr before bed; Blue-light filter from 20:00; No caffeine after 13:00; Magnesium 200 mg before bed (consult physician); Current: 6.5 hrs; Increase by 1.5 hrs",
    "nutrition": "Protein: 50 g/day; Omega-3: 1000 mg EPA+DHA/day; Magnesium: 400-420 mg/day; Zinc: 8-11 mg/day; Probiotics daily (yogurt/kefir); Free sugar <5% total energy; Eliminate ultra-processed foods; Reduce caffeine to <200 mg/day (current: 284 mg); Eliminate alcohol (current: 6 drinks/week)"
  }
}
```

Without `Gender` and `Alcohol Consumption`, the same request returns the same fields, and `nutrition`
reads `Protein: not provided (needs Gender); ... Alcohol: not provided (needs Alcohol Consumption)`.

## Known limitations to be aware of when integrating

This model has documented weaknesses that matter for how a caller should treat its output — see
[`docs/model_card.md`](model_card.md) for the full picture, in particular:
- The model is fragile to missing/corrupted values in `Stress Level (1-10)` and
  `Therapy Sessions (per month)` specifically (Phase 19 robustness findings).
- Raw probabilities are not well-calibrated — don't present `probabilities` to an end user as a
  literal confidence percentage.
- **Caffeine intake is an estimate, not a measured value.** The mg-per-serving figures are fixed
  population averages; a caller relying on precise caffeine dosing (rather than a rough
  low/moderate/high signal) should not treat `estimated_caffeine_mg` as accurate for any
  individual patient.
- **The PSS-4 → 1–10 Stress Level mapping is unvalidated.** The PSS-4 questionnaire is a
  validated instrument (Cohen, Kamarck & Mermelstein, 1983), but the linear rescale from its
  0–16 total to the model's 1–10 scale is this project's own convention, and the model was
  trained on an unanchored 1–10 self-rating, not PSS scores. Since Stress Level is the model's
  single most important feature, any mismatch between the two scales feeds directly into
  predictions.
- **The `/patient-summary` severity tier and recommendation bundle are estimates** (about 78% of tiers
  right with this model's predictions) built from synthetic dataset templates. They are for clinician
  review, never to be shown to a patient directly.
- **Ages 18–49 only.** Requests for anyone else are rejected (see "Supported age range"). The web
  app must block under-18s at registration, and send users 50+ straight to a psychologist.
- This is a prototype/research model on a very likely synthetic dataset — never represent its
  output as clinically validated, and never let it bypass psychologist review.
