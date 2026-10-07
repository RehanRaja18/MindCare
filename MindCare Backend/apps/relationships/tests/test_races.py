"""Concurrency: row locks make conflicting actions mutually exclusive."""

import threading

from django.db import connection
from django.http import Http404
from django.test import TestCase, TransactionTestCase

from apps.relationships import services
from apps.relationships.models import RelationshipStatus
from core.exceptions import DomainValidationError
from core.testing import (
    ReferenceDataTransactionTestCase,
    make_patient,
    make_psychologist,
    reseed_reference_data,
)


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


class AcceptVsCancelRaceTests(ReferenceDataTransactionTestCase):
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


class PatientEndVsPsychologistEndRaceTests(ReferenceDataTransactionTestCase):
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


class ReseedReferenceDataTests(TestCase):
    def test_reseeds_empty_tables_and_is_a_no_op_otherwise(self):
        from apps.reference.models import City, Country, Language, Specialization

        # Mirror a post-flush state: the seed recreates all four tables.
        City.objects.all().delete()
        Country.objects.all().delete()
        Language.objects.all().delete()
        Specialization.objects.all().delete()

        reseed_reference_data()
        self.assertTrue(Country.objects.filter(code="PK").exists())
        self.assertTrue(
            City.objects.filter(country__code="PK", is_verified=True).exists()
        )

        counts = [m.objects.count() for m in (Country, City, Language, Specialization)]
        reseed_reference_data()
        self.assertEqual(
            [m.objects.count() for m in (Country, City, Language, Specialization)],
            counts,
        )


# Must stay LAST in this file. pytest-django runs transactional tests after plain
# TestCases but keeps file order among them, so this runs after the race classes
# above. It does no reseeding before its assertion: it proves their teardown
# restored the migration-seeded reference data that their flush wiped. It still
# uses the base class so its own flush is followed by a reseed, leaving nothing
# for later tests to depend on.
class ZZReferenceDataSurvivesRaceTestsTests(ReferenceDataTransactionTestCase):
    def setUp(self):
        # Skip the base class's reseed on purpose (bypass its setUp); a reseed
        # here would hide a missing restore by the race classes' teardown.
        TransactionTestCase.setUp(self)

    def test_reference_data_is_present_after_race_tests(self):
        from apps.reference.models import City, Country

        self.assertTrue(Country.objects.filter(code="PK").exists())
        self.assertTrue(City.objects.filter(is_verified=True).exists())
