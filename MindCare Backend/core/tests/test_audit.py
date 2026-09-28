"""Tests for core/audit.py's identity_reveal event."""

import json

from django.test import SimpleTestCase

from core.audit import log_identity_reveal


class LogIdentityRevealTests(SimpleTestCase):
    def test_emits_ids_only(self):
        with self.assertLogs("mindcare.audit", level="INFO") as captured:
            log_identity_reveal(viewer_id=7, patient_id=42)
        self.assertEqual(len(captured.records), 1)
        payload = json.loads(captured.records[0].getMessage())
        self.assertEqual(
            set(payload), {"event_type", "timestamp", "viewer_id", "patient_id"}
        )
        self.assertEqual(payload["event_type"], "identity_reveal")
        self.assertEqual(payload["viewer_id"], 7)
        self.assertEqual(payload["patient_id"], 42)
