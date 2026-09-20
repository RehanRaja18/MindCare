"""FastAPI service exposing the tuned Random Forest (3-class Anxiety Level
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
from pydantic import BaseModel, ConfigDict, Field

from src.inference.input_validation import ALL_FEATURES, InputValidationError, validate_patient


ROOT = Path(__file__).resolve().parents[2]
PREPROCESSOR_PATH = ROOT / "data" / "processed" / "mindcare_preprocessor.pkl"
MODEL_PATH = ROOT / "data" / "processed" / "mindcare_final_model.pkl"
LABEL_ENCODER_PATH = ROOT / "data" / "processed" / "mindcare_label_encoder_3class.pkl"

HIGH_PROBA_THRESHOLD = 0.10  # production uncertainty-flagging rule (src/models/uncertainty_flagging.py)

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
    description="Decision-support inference for the tuned Random Forest (3-class Anxiety Level "
    "target). All predictions require psychologist review before reaching a patient.",
    version="1.0.0",
    lifespan=lifespan,
)


OccupationValue = Literal[
    "Artist", "Athlete", "Chef", "Doctor", "Engineer", "Freelancer", "Lawyer",
    "Musician", "Nurse", "Other", "Scientist", "Student", "Teacher",
]
YesNoValue = Literal["Yes", "No"]


class PatientFeatures(BaseModel):
    """All 17 raw feature values, using the exact column names from CLAUDE.md
    as the JSON keys (via Field aliases)."""

    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
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
                "Recent Major Life Event": "No",
            }
        },
    )

    age: float = Field(alias="Age")
    sleep_hours: float = Field(alias="Sleep Hours")
    physical_activity_hrs_week: float = Field(alias="Physical Activity (hrs/week)")
    caffeine_intake_mg_day: float = Field(alias="Caffeine Intake (mg/day)")
    alcohol_consumption_drinks_week: float = Field(alias="Alcohol Consumption (drinks/week)")
    stress_level: float = Field(alias="Stress Level (1-10)")
    heart_rate_bpm: float = Field(alias="Heart Rate (bpm)")
    breathing_rate_breaths_min: float = Field(alias="Breathing Rate (breaths/min)")
    sweating_level: float = Field(alias="Sweating Level (1-5)")
    therapy_sessions_per_month: float = Field(alias="Therapy Sessions (per month)")
    diet_quality: float = Field(alias="Diet Quality (1-10)")
    occupation: OccupationValue = Field(alias="Occupation")
    smoking: YesNoValue = Field(alias="Smoking")
    family_history_of_anxiety: YesNoValue = Field(alias="Family History of Anxiety")
    dizziness: YesNoValue = Field(alias="Dizziness")
    medication: YesNoValue = Field(alias="Medication")
    recent_major_life_event: YesNoValue = Field(alias="Recent Major Life Event")


class PredictionResponse(BaseModel):
    predicted_class: Literal["Low", "Medium", "High"]
    probabilities: dict[str, float]
    uncertainty_flag: bool
    warnings: list[str]


class HealthResponse(BaseModel):
    status: Literal["ok", "not_ready"]
    model_loaded: bool
    preprocessor_loaded: bool
    label_encoder_loaded: bool


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
    )
