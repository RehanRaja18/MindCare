"""Concurrency: row locks make conflicting actions mutually exclusive."""

import threading

from django.db import connection
from django.http import Http404
from django.test import TransactionTestCase

from apps.relationships import services
from apps.relationships.models import RelationshipStatus
from core.exceptions import DomainValidationError
from core.testing import make_patient, make_psychologist


def _run_concurrently(*funcs):
    barrier = threading.Barrier(len(funcs))
    results = [None] * len(funcs)

    def runner(i, fn):
        try:
            barrier.wait()
            fn()
            results[i] = "ok"
        except (DomainValidationError, Http404):  # the loser sees the new state
            results[i] = "rejected"
        finally:
            connection.close()

    threads = [
        threading.Thread(target=runner, args=(i, f)) for i, f in enumerate(funcs)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return results


class AcceptVsCancelRaceTests(TransactionTestCase):
    def test_exactly_one_wins(self):
        patient = make_patient()
        psych = make_psychologist()
        rel = services.request_psychologist(
            patient_user=patient.user, psychologist_id=psych.pk
        )
        results = _run_concurrently(
            lambda: services.accept_request(
                psychologist_user=psych.user, relationship_id=rel.pk
            ),
            lambda: services.cancel_request(
                patient_user=patient.user, relationship_id=rel.pk
            ),
        )
        self.assertEqual(sorted(results), ["ok", "rejected"])
        rel.refresh_from_db()
        self.assertIn(
            rel.status, {RelationshipStatus.ACCEPTED, RelationshipStatus.CANCELLED}
        )
