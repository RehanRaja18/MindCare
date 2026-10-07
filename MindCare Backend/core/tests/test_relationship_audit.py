"""log_relationship_event writes IDs only, never both patient and psychologist ids."""

import json

from django.test import SimpleTestCase

from core.audit import log_relationship_event


class LogRelationshipEventTests(SimpleTestCase):
    def test_payload_keys(self):
        with self.assertLogs("mindcare.audit", level="INFO") as captured:
            log_relationship_event(
                event="ended",
                relationship_id=5,
                actor_id=9,
                actor_role="psychologist",
                reason="treatment_completed",
            )
        payload = json.loads(captured.records[0].getMessage())
        self.assertEqual(
            set(payload),
            {
                "event_type",
                "event",
                "relationship_id",
                "reason",
                "actor_id",
                "actor_role",
                "timestamp",
            },
        )
        self.assertEqual(payload["event_type"], "relationship")
        self.assertNotIn("patient_id", payload)
        self.assertNotIn("psychologist_id", payload)

    def test_unknown_event_rejected(self):
        with self.assertRaises(ValueError):
            log_relationship_event(
                event="viewed", relationship_id=1, actor_id=1, actor_role="patient"
            )
