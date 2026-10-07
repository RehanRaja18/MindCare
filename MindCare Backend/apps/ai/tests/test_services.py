"""Service-layer tests for the AI gateway (HTTP mocked; no network)."""

import json
import logging
import socket
from unittest import mock
from urllib.error import URLError

from django.test import SimpleTestCase, override_settings

from apps.ai import services
from apps.ai.services import AIPredictionRejected, AIServiceUnavailable
from apps.ai.tests.helpers import (
    AI_RESPONSE,
    URLOPEN,
    VALID_FEATURES,
    FakeResponse,
    http_error,
)


@override_settings(AI_SERVICE_URL="http://ai.invalid/")
class PredictAnxietyRiskTests(SimpleTestCase):
    def test_forwards_features_to_predict_with_60s_timeout(self):
        with mock.patch(URLOPEN, return_value=FakeResponse(AI_RESPONSE)) as urlopen:
            result = services.predict_anxiety_risk(features=VALID_FEATURES)

        self.assertEqual(result, AI_RESPONSE)
        req = urlopen.call_args.args[0]
        self.assertEqual(req.full_url, "http://ai.invalid/predict")
        self.assertEqual(req.get_method(), "POST")
        self.assertEqual(req.get_header("Content-type"), "application/json")
        self.assertEqual(json.loads(req.data), VALID_FEATURES)
        self.assertEqual(urlopen.call_args.kwargs["timeout"], 60)

    def test_ai_422_string_detail_becomes_rejection_with_message(self):
        msg = "Age=55 is outside the supported range [18, 49]"
        with mock.patch(URLOPEN, side_effect=http_error(422, {"detail": msg})):
            with self.assertRaises(AIPredictionRejected) as ctx:
                services.predict_anxiety_risk(features=VALID_FEATURES)
        self.assertEqual(ctx.exception.message, msg)

    def test_ai_422_list_detail_is_flattened(self):
        detail = [{"loc": ["body", "pss_confident"], "msg": "Input should be <= 4"}]
        with mock.patch(URLOPEN, side_effect=http_error(422, {"detail": detail})):
            with self.assertRaises(AIPredictionRejected) as ctx:
                services.predict_anxiety_risk(features=VALID_FEATURES)
        self.assertEqual(ctx.exception.message, "pss_confident: Input should be <= 4")

    def test_timeout_connection_error_and_5xx_are_unavailable(self):
        for side_effect in (
            socket.timeout("timed out"),
            TimeoutError(),
            URLError("connection refused"),
            http_error(502, {"detail": "Bad gateway"}),
            http_error(404, {"detail": "Not Found"}),  # wrong URL / no service
        ):
            with self.subTest(side_effect=type(side_effect).__name__):
                with mock.patch(URLOPEN, side_effect=side_effect):
                    with self.assertRaises(AIServiceUnavailable):
                        services.predict_anxiety_risk(features=VALID_FEATURES)

    def test_non_json_answer_is_unavailable(self):
        bad = FakeResponse({})
        bad._body = b"<html>waking up</html>"
        with mock.patch(URLOPEN, return_value=bad):
            with self.assertRaises(AIServiceUnavailable):
                services.predict_anxiety_risk(features=VALID_FEATURES)

    @override_settings(AI_SERVICE_URL="")
    def test_missing_url_is_unavailable_without_a_call(self):
        with mock.patch(URLOPEN) as urlopen:
            with self.assertRaises(AIServiceUnavailable):
                services.predict_anxiety_risk(features=VALID_FEATURES)
        urlopen.assert_not_called()

    def test_failures_never_log_the_health_data(self):
        with self.assertLogs("mindcare", level=logging.DEBUG) as logs:
            logging.getLogger("mindcare").debug("start")  # assertLogs needs a line
            for side_effect in (
                URLError("refused"),
                http_error(422, {"detail": "Heart Rate (bpm)=9000 is invalid"}),
            ):
                with mock.patch(URLOPEN, side_effect=side_effect):
                    with self.assertRaises(Exception):
                        services.predict_anxiety_risk(features=VALID_FEATURES)
        joined = "\n".join(logs.output)
        for value in ("Teacher", "8.2", "Heart Rate", "Sleep Hours", "9000"):
            self.assertNotIn(value, joined)
