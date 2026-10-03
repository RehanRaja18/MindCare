"""FastAPI service exposing the canonical XGBoost model (3-class Anxiety Level
target) for single-patient inference.

Decision-support only — per CLAUDE.md's critical workflow constraint, no
prediction from this service may reach a patient without psychologist
review. This service does not enforce that constraint itself (it has no
concept of a patient-facing UI); the calling system is responsible for
routing predictions through psychologist review before any patient sees
them.

Run with: uvicorn src.api.main:app --reload
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field

from src.inference.input_validation import ALL_FEATURES, InputValidationError, validate_patient
from src.inference.stress_scale import PSS_FIELDS, PSS_ITEM_MAX, PSS_ITEM_MIN, estimate_stress_level
from src.inference.template_advice import CAVEAT as SUMMARY_CAVEAT
from src.inference.template_advice import estimate_tier, render


ROOT = Path(__file__).resolve().parents[2]
MANUAL_TEST_FORM_PATH = Path(__file__).resolve().parent / "static" / "manual_test_form.html"
# Canonical model: 11-feature "v2" XGBoost since 2026-10-02 - the 12-feature XGBoost with Sweating
# Level removed (reports/feature_reduction_sweatlevel_3class.md; built by
# src/models/adopt_11feature_v2_model.py). "v2" because *_11feature.* is the superseded 2026-09-22
# Random Forest set (no Age, with Sweating Level). The 12-feature artifacts are kept for history.
PREPROCESSOR_PATH = ROOT / "data" / "processed" / "mindcare_preprocessor_11feature_v2.pkl"
MODEL_PATH = ROOT / "data" / "processed" / "mindcare_final_model_11feature_v2_xgb.pkl"
LABEL_ENCODER_PATH = ROOT / "data" / "processed" / "mindcare_label_encoder_3class.pkl"

# Priority-review flag on P(High). 0.025 for XGBoost (was 0.10 for the Random Forest): the level at
# which XGBoost matches the Random Forest's validation coverage - 158/165 true-High rows and 10/17
# true-High rows predicted Medium (src/models/adopt_xgboost_12feature_model.py). Unchanged for the
# 11-feature v2 model, which catches the same 158/165 at 0.025 (411 flagged instead of 410).
HIGH_PROBA_THRESHOLD = 0.025

# Average caffeine content per serving (mg) - commonly-cited USDA/Mayo-Clinic-style figures.
# These are population averages, not measurements: actual caffeine content varies substantially
# by brand, brew strength, and serving size. Used only to convert a patient-friendly serving
# count into the mg/day figure the model was actually trained on.
COFFEE_MG_PER_CUP = 95
TEA_MG_PER_CUP = 47
ENERGY_DRINK_MG_PER_CAN = 80
SODA_MG_PER_CAN = 35


def estimate_caffeine_mg(cups_of_coffee: int, cups_of_tea: int, energy_drinks: int, cans_of_soda: int) -> float:
    """Estimate total daily caffeine intake (mg) from serving counts.

    Uses fixed average mg-per-serving figures (see module-level constants above,
    stated explicitly since this is an approximation, not a measurement):
    coffee ~95mg/cup, tea ~47mg/cup, energy drink ~80mg/can, soda ~35mg/can.
    The result is fed through the same "Caffeine Intake (mg/day)" validation
    bounds and preprocessing as before - only how the mg figure is obtained
    from the patient has changed, not what the model receives.
    """
    return (
        cups_of_coffee * COFFEE_MG_PER_CUP
        + cups_of_tea * TEA_MG_PER_CUP
        + energy_drinks * ENERGY_DRINK_MG_PER_CAN
        + cans_of_soda * SODA_MG_PER_CAN
    )

# Populated once at startup (see `lifespan` below) - never reloaded per-request.
ml_artifacts: dict[str, object] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    ml_artifacts["preprocessor"] = joblib.load(PREPROCESSOR_PATH)
    ml_artifacts["model"] = joblib.load(MODEL_PATH)
    ml_artifacts["label_encoder"] = joblib.load(LABEL_ENCODER_PATH)
    class_names = list(ml_artifacts["label_encoder"].classes_)
    ml_artifacts["class_names"] = class_names
    ml_artifacts["high_index"] = class_names.index("High")
    yield
    ml_artifacts.clear()


app = FastAPI(
    title="MindCare Anxiety Level API",
    description="Decision-support inference for the XGBoost model (3-class Anxiety Level "
    "target). All predictions require psychologist review before reaching a patient.",
    version="1.0.0",
    lifespan=lifespan,
)


OccupationValue = Literal[
    "Artist", "Athlete", "Chef", "Doctor", "Engineer", "Freelancer", "Lawyer",
    "Musician", "Nurse", "Other", "Scientist", "Student", "Teacher",
]
YesNoValue = Literal["Yes", "No"]

# Sane upper bound on each caffeine serving count - catches obvious data-entry errors (e.g. a
# stray extra digit) at the schema level. Values within this range but still unusually high
# (see estimate_caffeine_mg()) are NOT rejected here - they flow through to the same warn/reject
# two-tier check as every other feature, applied to the computed mg total.
MAX_SERVINGS = 20


class PatientFeatures(BaseModel):
    """The 11 raw feature values the canonical model uses, using the exact
    column names from CLAUDE.md as JSON keys (via Field aliases) - except
    caffeine, which is collected as four patient-friendly serving counts
    instead of a raw mg/day figure (see estimate_caffeine_mg()), and Stress
    Level, which is collected as the 4 PSS-4 items instead of a raw 1-10
    rating (see src/inference/stress_scale.py's estimate_stress_level()).

    Age was re-added on 2026-09-22 (clinical/UX decision, see
    reports/feature_addition_age_3class.md). Alcohol Consumption
    (drinks/week), Dizziness, Smoking, Recent Major Life Event, and
    Medication remain dropped (reports/feature_reduction_3class.md), and
    Sweating Level (1-5) was dropped on 2026-10-02
    (reports/feature_reduction_sweatlevel_3class.md). None are part of this
    schema; if a caller still sends one, it is silently ignored.

    Age's schema bound (0-120) only catches impossible values. The supported
    range for a prediction is narrower, 18-49 (decided 2026-09-27), and is
    enforced by validate_patient(), with a 422 whose message differs by side
    (decided 2026-09-28): under 18 = not eligible for MindCare at all
    (registration should have blocked them); 50+ = refer the person directly
    to a psychologist."""

    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
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
                "Family History of Anxiety": "No",
            }
        },
    )

    age: int = Field(alias="Age", ge=0, le=120)
    sleep_hours: float = Field(alias="Sleep Hours")
    physical_activity_hrs_week: float = Field(alias="Physical Activity (hrs/week)")
    cups_of_coffee: int = Field(ge=0, le=MAX_SERVINGS)
    cups_of_tea: int = Field(ge=0, le=MAX_SERVINGS)
    energy_drinks: int = Field(ge=0, le=MAX_SERVINGS)
    cans_of_soda: int = Field(ge=0, le=MAX_SERVINGS)
    # PSS-4 items, each 0=Never ... 4=Very often, "in the last month". pss_confident and
    # pss_going_your_way are positively worded and reverse-scored in estimate_stress_level().
    pss_uncontrollable: int = Field(ge=PSS_ITEM_MIN, le=PSS_ITEM_MAX)
    pss_confident: int = Field(ge=PSS_ITEM_MIN, le=PSS_ITEM_MAX)
    pss_going_your_way: int = Field(ge=PSS_ITEM_MIN, le=PSS_ITEM_MAX)
    pss_difficulties_piling_up: int = Field(ge=PSS_ITEM_MIN, le=PSS_ITEM_MAX)
    heart_rate_bpm: float = Field(alias="Heart Rate (bpm)")
    breathing_rate_breaths_min: float = Field(alias="Breathing Rate (breaths/min)")
    therapy_sessions_per_month: float = Field(alias="Therapy Sessions (per month)")
    diet_quality: float = Field(alias="Diet Quality (1-10)")
    occupation: OccupationValue = Field(alias="Occupation")
    family_history_of_anxiety: YesNoValue = Field(alias="Family History of Anxiety")


class PredictionResponse(BaseModel):
    predicted_class: Literal["Low", "Medium", "High"]
    probabilities: dict[str, float]
    uncertainty_flag: bool
    warnings: list[str]
    estimated_caffeine_mg: float
    estimated_stress_level: int


class HealthResponse(BaseModel):
    status: Literal["ok", "not_ready"]
    model_loaded: bool
    preprocessor_loaded: bool
    label_encoder_loaded: bool


@app.get("/form", include_in_schema=False)
def manual_test_form() -> FileResponse:
    """A plain HTML page for manually exercising POST /predict from a browser.

    Local dev/manual-testing convenience only - not part of the documented,
    deployed API contract (docs/api_usage.md), and not shown in the OpenAPI
    schema (/docs, /redoc)."""
    return FileResponse(MANUAL_TEST_FORM_PATH)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    model_loaded = "model" in ml_artifacts
    preprocessor_loaded = "preprocessor" in ml_artifacts
    label_encoder_loaded = "label_encoder" in ml_artifacts
    return HealthResponse(
        status="ok" if (model_loaded and preprocessor_loaded and label_encoder_loaded) else "not_ready",
        model_loaded=model_loaded,
        preprocessor_loaded=preprocessor_loaded,
        label_encoder_loaded=label_encoder_loaded,
    )


@app.post("/predict", response_model=PredictionResponse)
def predict(patient: PatientFeatures) -> PredictionResponse:
    patient_dict = patient.model_dump(by_alias=True)

    # Convert the 4 patient-friendly serving counts into the single mg/day figure the
    # model actually expects, then drop the serving-count keys so the rest of the
    # pipeline (validation, preprocessing) is unchanged from before this feature existed.
    caffeine_mg = estimate_caffeine_mg(
        patient.cups_of_coffee, patient.cups_of_tea, patient.energy_drinks, patient.cans_of_soda
    )
    for serving_field in ("cups_of_coffee", "cups_of_tea", "energy_drinks", "cans_of_soda"):
        patient_dict.pop(serving_field, None)
    patient_dict["Caffeine Intake (mg/day)"] = caffeine_mg

    # Same pattern for stress: the 4 PSS-4 answers become the single 1-10 Stress Level the
    # model was trained on. The computed value (not anything user-submitted) is what
    # validate_patient() below checks against the Stress Level (1-10) bounds.
    stress_level = estimate_stress_level(
        patient.pss_uncontrollable, patient.pss_confident,
        patient.pss_going_your_way, patient.pss_difficulties_piling_up,
    )
    for pss_field in PSS_FIELDS:
        patient_dict.pop(pss_field, None)
    patient_dict["Stress Level (1-10)"] = stress_level

    try:
        warnings = validate_patient(patient_dict)
    except InputValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    preprocessor = ml_artifacts["preprocessor"]
    model = ml_artifacts["model"]
    class_names = ml_artifacts["class_names"]
    high_index = ml_artifacts["high_index"]

    row = pd.DataFrame([{feature: patient_dict[feature] for feature in ALL_FEATURES}])
    x = preprocessor.transform(row)
    probabilities = model.predict_proba(x)[0]
    predicted_index = int(np.argmax(probabilities))
    p_high = float(probabilities[high_index])

    return PredictionResponse(
        predicted_class=class_names[predicted_index],
        probabilities={name: float(p) for name, p in zip(class_names, probabilities)},
        uncertainty_flag=p_high >= HIGH_PROBA_THRESHOLD,
        warnings=warnings,
        estimated_caffeine_mg=caffeine_mg,
        estimated_stress_level=stress_level,
    )


class PatientSummaryRequest(PatientFeatures):
    """/predict's fields plus two OPTIONAL fields the model never uses. They only fill slots in
    the recommendation bundle; when omitted (or null), those slots say "not provided"."""

    gender: Literal["Female", "Male", "Other"] | None = Field(default=None, alias="Gender")
    alcohol_consumption: float | None = Field(default=None, alias="Alcohol Consumption (drinks/week)", ge=0, le=100)


class SeverityTierBasis(BaseModel):
    method: str
    share_of_matching_patients: float | None
    matching_patients: int


class RecommendationBundle(BaseModel):
    exercises: str
    sleep_schedule: str
    nutrition: str


class PatientSummaryResponse(BaseModel):
    # First field on purpose, so the caveat is the first thing a reader of the JSON sees.
    caveat: str
    predicted_class: Literal["Low", "Medium", "High"]
    probabilities: dict[str, float]
    uncertainty_flag: bool
    warnings: list[str]
    estimated_caffeine_mg: float
    estimated_stress_level: int
    estimated_severity_tier: Literal["Minimal (1-2)", "Mild (3-4)", "Moderate (5-6)", "High (7-8)", "Severe (9-10)"]
    severity_tier_basis: SeverityTierBasis
    recommendation_bundle: RecommendationBundle


@app.post("/patient-summary", response_model=PatientSummaryResponse)
def patient_summary(request: PatientSummaryRequest) -> PatientSummaryResponse:
    """Psychologist-facing summary: /predict's result, plus an ESTIMATED Severity tier and the
    dataset's recommendation bundle for it, always with SUMMARY_CAVEAT. Decision support for
    clinician review only.

    - The prediction fields come from predict() unchanged (same validation and age rules).
    - estimated_severity_tier is a best guess from the predicted 3-class label plus the
      PSS-derived Stress Level: the most common tier for that pair among the 9,350 train +
      validation rows (reports/recommendation_mapping_investigation.md; ~88% ceiling given the
      TRUE label, lower with the model's own errors). It is not the model's prediction.
    - POST, not GET: the input is patient health data, which would otherwise be written to the
      server's access logs as query parameters."""
    patient = PatientFeatures(**request.model_dump(by_alias=True, exclude={"gender", "alcohol_consumption"}))
    prediction = predict(patient)
    tier = estimate_tier(prediction.predicted_class, prediction.estimated_stress_level)
    bundle = render(tier["tier"], request.gender, request.sleep_hours,
                    int(round(prediction.estimated_caffeine_mg)), request.alcohol_consumption)
    return PatientSummaryResponse(
        caveat=SUMMARY_CAVEAT,
        **prediction.model_dump(),
        estimated_severity_tier=tier["tier"],
        severity_tier_basis=SeverityTierBasis(
            method=tier["basis"], share_of_matching_patients=tier["share"], matching_patients=tier["n"]),
        recommendation_bundle=RecommendationBundle(**bundle),
    )
