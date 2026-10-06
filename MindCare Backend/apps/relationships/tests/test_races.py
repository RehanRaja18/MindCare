"""Concurrency: row locks make conflicting actions mutually exclusive."""

import importlib
import threading

from django.db import connection
from django.http import Http404
from django.test import TransactionTestCase

from apps.relationships import services
from apps.relationships.models import RelationshipStatus
from core.exceptions import DomainValidationError
from core.testing import make_patient, make_psychologist


def _reseed_reference_data():
    """A TransactionTestCase flushes every table after it runs, including the
    migration-seeded reference data make_psychologist needs, so a second one
    starts with no countries. Re-run the seed migrations if that happened.
    (serialized_rollback clashes with the content types post_migrate recreates.)"""
    from django.apps import apps

    from apps.reference.models import Country

    if Country.objects.exists():
        return
    seed = importlib.import_module("apps.reference.migrations.0002_seed_reference_data")
    verify = importlib.import_module(
        "apps.reference.migrations.0003_city_is_verified_and_turkiye"
    )
    seed.seed(apps, None)
    verify.verify_seeded_cities_and_rename_turkiye(apps, None)


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
    def setUp(self):
        _reseed_reference_data()

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
        expected = (
            RelationshipStatus.ACCEPTED
            if results[0] == "ok"
            else RelationshipStatus.CANCELLED
        )
        self.assertEqual(rel.status, expected)


class PatientEndVsPsychologistEndRaceTests(TransactionTestCase):
    def setUp(self):
        _reseed_reference_data()

    def test_exactly_one_ends_it(self):
        patient = make_patient()
        psych = make_psychologist()
        rel = services.request_psychologist(
            patient_user=patient.user, psychologist_id=psych.pk
        )
        services.accept_request(psychologist_user=psych.user, relationship_id=rel.pk)
        results = _run_concurrently(
            lambda: services.patient_end_relationship(
                patient_user=patient.user, confirm=True
            ),
            lambda: services.psychologist_end_relationship(
                psychologist_user=psych.user, relationship_id=rel.pk, reason="other"
            ),
        )
        self.assertEqual(sorted(results), ["ok", "rejected"])
        rel.refresh_from_db()
        self.assertEqual(rel.status, RelationshipStatus.ENDED)
        expected_by = "patient" if results[0] == "ok" else "psychologist"
        self.assertEqual(rel.ended_by, expected_by)
