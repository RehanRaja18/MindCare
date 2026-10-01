"""Selector tests for the public stats."""

from django.core.cache import cache
from django.test import TestCase

from apps.accounts.models import ApprovalStatus, Role
from apps.ngo.services import create_ngo_profile
from apps.patients.services import create_patient_profile, update_patient_profile
from apps.psychologists.services import create_psychologist_profile
from apps.reference.models import Country
from apps.stats.selectors import CACHE_KEY, get_public_platform_stats
from core.testing import make_user, ngo_profile_data, psychologist_profile_data


class PublicStatsTests(TestCase):
    def setUp(self):
        cache.clear()
        pk = Country.objects.get(code="PK")
        # Patients: 2 active (one in Lahore), 1 deactivated.
        p1 = create_patient_profile(user=make_user(role=Role.PATIENT), timezone="UTC")
        update_patient_profile(profile=p1, country=pk, city="Lahore")
        create_patient_profile(user=make_user(role=Role.PATIENT), timezone="UTC")
        create_patient_profile(
            user=make_user(role=Role.PATIENT, is_active=False), timezone="UTC"
        )
        # Psychologists: 1 approved (Lahore), 1 pending (Islamabad).
        create_psychologist_profile(
            user=make_user(role=Role.PSYCHOLOGIST), **psychologist_profile_data()
        )
        create_psychologist_profile(
            user=make_user(
                role=Role.PSYCHOLOGIST, approval_status=ApprovalStatus.PENDING
            ),
            **psychologist_profile_data(license_number="OTHER-1", city="Islamabad"),
        )
        # Deactivated approved psychologist in Faisalabad: doesn't count.
        create_psychologist_profile(
            user=make_user(role=Role.PSYCHOLOGIST, is_active=False),
            **psychologist_profile_data(license_number="OTHER-2", city="Faisalabad"),
        )
        # Pending NGO in Multan: doesn't count.
        create_ngo_profile(
            user=make_user(role=Role.NGO, approval_status=ApprovalStatus.PENDING),
            **ngo_profile_data(registration_number="SECP-0002", city="Multan"),
        )
        # NGO HQ in Karachi, nationwide + Quetta service areas (not counted).
        create_ngo_profile(
            user=make_user(role=Role.NGO),
            **ngo_profile_data(service_areas=[{"country": pk, "city": "Quetta"}]),
        )

    def test_counts(self):
        stats = get_public_platform_stats()
        # TEMPORARY definition: active patients (Phase 3 switches to accepted patients).
        self.assertEqual(stats["people_in_care"], 2)
        self.assertEqual(stats["verified_therapists"], 1)
        # Lahore (patient + approved psychologist, counted once) and Karachi (approved
        # NGO). Not Islamabad (pending psychologist), Faisalabad (deactivated
        # psychologist), Multan (pending NGO) or Quetta (service area).
        self.assertEqual(stats["cities"], 2)

    def test_result_is_cached(self):
        get_public_platform_stats()
        self.assertIsNotNone(cache.get(CACHE_KEY))
        create_patient_profile(user=make_user(role=Role.PATIENT), timezone="UTC")
        self.assertEqual(get_public_platform_stats()["people_in_care"], 2)
