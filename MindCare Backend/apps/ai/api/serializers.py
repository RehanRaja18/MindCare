"""Serializers for the AI gateway.

The request keys are exactly the AI service's own `POST /predict` keys (column
names with spaces, see "MindCare AI/docs/api_usage.md"), so the body can be
forwarded unchanged. Bounds mirror the AI's Pydantic schema; the AI's own
plausibility and 18-49 age rules stay on its side and come back as a 400.
"""

from rest_framework import serializers

from core.serializers import RejectUnknownFieldsMixin, number_field, whole_number_field

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


# The AI's supported age range: other ages get a 422 there anyway
# (MindCare AI/docs/api_usage.md), so they're refused here with a clear message.
AGE_MIN, AGE_MAX = 18, 49


def _servings(label):
    return whole_number_field(label, 0, MAX_SERVINGS)


def _pss(label):
    return whole_number_field(label, PSS_MIN, PSS_MAX)


class AnxietyPredictionRequestSerializer(
    RejectUnknownFieldsMixin, serializers.Serializer
):
    """Keys contain spaces, so fields are declared in get_fields()."""

    def get_fields(self):
        return {
            # Physical bounds mirror the AI's hard limits
            # (MindCare AI/src/inference/input_validation.py); docs/validation-rules.md.
            "Age": whole_number_field("Age", AGE_MIN, AGE_MAX),
            "Sleep Hours": number_field("Sleep hours", 0, 24),
            "Physical Activity (hrs/week)": number_field("Physical activity", 0, 168),
            "cups_of_coffee": _servings("Cups of coffee"),
            "cups_of_tea": _servings("Cups of tea"),
            "energy_drinks": _servings("Energy drinks"),
            "cans_of_soda": _servings("Cans of soda"),
            "pss_uncontrollable": _pss("Stress question 1"),
            "pss_confident": _pss("Stress question 2"),
            "pss_going_your_way": _pss("Stress question 3"),
            "pss_difficulties_piling_up": _pss("Stress question 4"),
            "Heart Rate (bpm)": number_field("Heart rate", 30, 220),
            "Breathing Rate (breaths/min)": number_field("Breathing rate", 5, 60),
            "Therapy Sessions (per month)": number_field("Therapy sessions", 0, 31),
            "Diet Quality (1-10)": number_field("Diet quality", 1, 10),
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
