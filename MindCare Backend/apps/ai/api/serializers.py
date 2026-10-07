"""Serializers for the AI gateway.

The request keys are exactly the AI service's own `POST /predict` keys (column
names with spaces, see "MindCare AI/docs/api_usage.md"), so the body can be
forwarded unchanged. Bounds mirror the AI's Pydantic schema; the AI's own
plausibility and 18-49 age rules stay on its side and come back as a 400.
"""

from rest_framework import serializers

from core.serializers import RejectUnknownFieldsMixin

OCCUPATIONS = [
    "Artist",
    "Athlete",
    "Chef",
    "Doctor",
    "Engineer",
    "Freelancer",
    "Lawyer",
    "Musician",
    "Nurse",
    "Other",
    "Scientist",
    "Student",
    "Teacher",
]
MAX_SERVINGS = 20
PSS_MIN, PSS_MAX = 0, 4


def _servings():
    return serializers.IntegerField(min_value=0, max_value=MAX_SERVINGS)


def _pss():
    return serializers.IntegerField(min_value=PSS_MIN, max_value=PSS_MAX)


class AnxietyPredictionRequestSerializer(
    RejectUnknownFieldsMixin, serializers.Serializer
):
    """Keys contain spaces, so fields are declared in get_fields()."""

    def get_fields(self):
        return {
            "Age": serializers.IntegerField(min_value=0, max_value=120),
            "Sleep Hours": serializers.FloatField(),
            "Physical Activity (hrs/week)": serializers.FloatField(),
            "cups_of_coffee": _servings(),
            "cups_of_tea": _servings(),
            "energy_drinks": _servings(),
            "cans_of_soda": _servings(),
            "pss_uncontrollable": _pss(),
            "pss_confident": _pss(),
            "pss_going_your_way": _pss(),
            "pss_difficulties_piling_up": _pss(),
            "Heart Rate (bpm)": serializers.FloatField(),
            "Breathing Rate (breaths/min)": serializers.FloatField(),
            "Therapy Sessions (per month)": serializers.FloatField(),
            "Diet Quality (1-10)": serializers.FloatField(),
            "Occupation": serializers.ChoiceField(choices=OCCUPATIONS),
            "Family History of Anxiety": serializers.ChoiceField(choices=["Yes", "No"]),
        }


class _Probabilities(serializers.Serializer):
    Low = serializers.FloatField()
    Medium = serializers.FloatField()
    High = serializers.FloatField()


class AnxietyPredictionResponseSerializer(serializers.Serializer):
    """Documents the AI service's response, which is returned unchanged."""

    predicted_class = serializers.ChoiceField(choices=["Low", "Medium", "High"])
    probabilities = _Probabilities()
    uncertainty_flag = serializers.BooleanField(
        help_text="P(High) >= 0.025: recommend priority review."
    )
    warnings = serializers.ListField(child=serializers.CharField())
    estimated_caffeine_mg = serializers.FloatField()
    estimated_stress_level = serializers.IntegerField()
    confidence = serializers.FloatField()
    confidence_label = serializers.ChoiceField(choices=["confident", "borderline"])
    borderline_reasons = serializers.ListField(child=serializers.CharField())
    borderline_between = serializers.ListField(
        child=serializers.CharField(), allow_null=True
    )


class DetailSerializer(serializers.Serializer):
    detail = serializers.CharField()
