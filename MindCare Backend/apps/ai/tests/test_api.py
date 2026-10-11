"""API tests for POST /api/v1/ai/anxiety-prediction/ (HTTP mocked; no network)."""

from unittest import mock

from django.conf import settings
from django.core.cache import cache
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import ApprovalStatus
from apps.ai.tests.helpers import (
    AI_RESPONSE,
    URLOPEN,
    VALID_FEATURES,
    FakeResponse,
    http_error,
)
from core.testing import make_patient, make_psychologist

URL = "/api/v1/ai/anxiety-prediction/"
WAKING = "The AI service is waking up. Please try again in a minute."


@override_settings(AI_SERVICE_URL="http://ai.invalid")
class AnxietyPredictionAPITests(APITestCase):
    def setUp(self):
        cache.clear()
        self.psych = make_psychologist()
        self.client.force_authenticate(self.psych.user)

    def tearDown(self):
        cache.clear()

    def post(self, body):
        return self.client.post(URL, body, format="json")

    def test_approved_psychologist_gets_the_ai_response(self):
        with mock.patch(URLOPEN, return_value=FakeResponse(AI_RESPONSE)):
            r = self.post(VALID_FEATURES)
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.json(), AI_RESPONSE)

    def test_patient_pending_and_anonymous_are_refused_without_a_call(self):
        pending = make_psychologist(approval_status=ApprovalStatus.PENDING)
        cases = [
            ("patient", make_patient().user, status.HTTP_403_FORBIDDEN),
            ("pending psychologist", pending.user, status.HTTP_403_FORBIDDEN),
            ("anonymous", None, status.HTTP_401_UNAUTHORIZED),
        ]
        for label, user, expected in cases:
            with self.subTest(label):
                self.client.force_authenticate(user)
                with mock.patch(URLOPEN) as urlopen:
                    self.assertEqual(self.post(VALID_FEATURES).status_code, expected)
                urlopen.assert_not_called()

    def test_invalid_body_is_400_without_a_call(self):
        missing = {k: v for k, v in VALID_FEATURES.items() if k != "Sleep Hours"}
        cases = {
            "Sleep Hours": missing,
            "Occupation": {**VALID_FEATURES, "Occupation": "Pilot"},
            "pss_confident": {**VALID_FEATURES, "pss_confident": 5},
            "cups_of_coffee": {**VALID_FEATURES, "cups_of_coffee": 21},
            "Family History of Anxiety": {
                **VALID_FEATURES,
                "Family History of Anxiety": "Maybe",
            },
            "patient_name": {**VALID_FEATURES, "patient_name": "x"},
        }
        for key, body in cases.items():
            with self.subTest(key):
                with mock.patch(URLOPEN) as urlopen:
                    r = self.post(body)
                self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn(key, r.json())
                urlopen.assert_not_called()

    def test_ai_rejection_is_a_clean_400(self):
        # Only the AI can judge the computed caffeine total (15 cups = 1425 mg).
        msg = (
            "Caffeine Intake (mg/day)=1425.0 is outside the physically plausible range"
        )
        with mock.patch(URLOPEN, side_effect=http_error(422, {"detail": msg})):
            r = self.post({**VALID_FEATURES, "cups_of_coffee": 15})
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(r.json(), {"detail": msg})

    def test_out_of_range_inputs_rejected_before_the_ai_is_called(self):
        cases = {
            "Age": (55, "Age must be a whole number between 18 and 49."),
            "Sleep Hours": (25, "Sleep hours must be a number between 0 and 24."),
            "Heart Rate (bpm)": (
                9000,
                "Heart rate must be a number between 30 and 220.",
            ),
            "Breathing Rate (breaths/min)": (
                -1,
                "Breathing rate must be a number between 5 and 60.",
            ),
            "Diet Quality (1-10)": (
                0,
                "Diet quality must be a number between 1 and 10.",
            ),
            "Therapy Sessions (per month)": (
                "lots",
                "Therapy sessions must be a number between 0 and 31.",
            ),
        }
        with mock.patch(URLOPEN) as urlopen:
            for key, (value, message) in cases.items():
                with self.subTest(key=key):
                    r = self.post({**VALID_FEATURES, key: value})
                    self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
                    self.assertEqual(r.json(), {key: [message]})
        urlopen.assert_not_called()

    def test_ai_unavailable_is_503_with_waking_message(self):
        with mock.patch(URLOPEN, side_effect=TimeoutError()):
            r = self.post(VALID_FEATURES)
        self.assertEqual(r.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertEqual(r.json(), {"detail": WAKING})

    def test_throttled_per_user_at_configured_rate(self):
        rate = settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["ai_prediction"]
        self.assertEqual(rate, "20/min")
        with mock.patch(URLOPEN, side_effect=lambda *a, **k: FakeResponse(AI_RESPONSE)):
            codes = [self.post(VALID_FEATURES).status_code for _ in range(21)]
        self.assertEqual(codes[:20], [status.HTTP_200_OK] * 20)
        self.assertEqual(codes[20], status.HTTP_429_TOO_MANY_REQUESTS)

    def test_documented_in_openapi_schema(self):
        self.client.force_authenticate(None)
        schema = self.client.get("/api/schema/?format=json").json()
        op = schema["paths"][URL]["post"]
        ref = op["requestBody"]["content"]["application/json"]["schema"]["$ref"]
        props = schema["components"]["schemas"][ref.rsplit("/", 1)[-1]]["properties"]
        self.assertEqual(set(props), set(VALID_FEATURES))
        self.assertTrue({"200", "400", "403", "503"} <= set(op["responses"]))
