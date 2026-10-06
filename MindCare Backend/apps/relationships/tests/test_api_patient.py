"""Patient-facing relationship API."""

from django.conf import settings
from django.core.cache import cache
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.test import APITestCase

from apps.accounts.models import ApprovalStatus, Role
from apps.psychologists.api.serializers import DIRECTORY_CARD_FIELDS
from apps.psychologists.models import PsychologistProfile
from apps.relationships import services
from core.pagination import StandardPagination
from core.permissions import IsPatient
from core.serializers import StrictTrueField
from core.testing import make_admin, make_patient, make_psychologist, make_user

DIRECTORY = "/api/v1/psychologists/directory/"
REQUESTS = "/api/v1/relationships/requests/"
CURRENT = "/api/v1/relationships/current/"
END = "/api/v1/relationships/current/end/"
RECENT = "/api/v1/relationships/recent/"

EXPECTED_CARD_KEYS = {
    "id",
    "full_name",
    "gender",
    "bio",
    "qualifications",
    "license_issuing_country",
    "license_issuing_authority",
    "specializations",
    "languages",
    "years_of_experience",
    "country",
    "city",
    "timezone",
    "is_accepting_patients",
    "last_active",
}


class PatientAPITests(APITestCase):
    def setUp(self):
        cache.clear()
        self.patient = make_patient()
        self.psych = make_psychologist(full_name="Dr Sana")
        self.client.force_authenticate(self.patient.user)

    def test_directory_card_has_exact_keys(self):
        r = self.client.get(DIRECTORY)
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        card = r.data["results"][0]
        self.assertEqual(set(card), set(DIRECTORY_CARD_FIELDS))
        for forbidden in (
            "license_number",
            "last_active_at",
            "not_accepting_reason",
            "email",
            "approval_status",
        ):
            self.assertNotIn(forbidden, card)
        self.assertEqual(card["last_active"], "never")

    def test_directory_card_fields_constant_is_the_literal_list(self):
        self.assertEqual(set(DIRECTORY_CARD_FIELDS), EXPECTED_CARD_KEYS)
        self.assertEqual(len(DIRECTORY_CARD_FIELDS), len(EXPECTED_CARD_KEYS))

    def test_directory_patients_only(self):
        self.client.force_authenticate(self.psych.user)
        self.assertEqual(
            self.client.get(DIRECTORY).status_code, status.HTTP_403_FORBIDDEN
        )
        self.client.force_authenticate(None)
        self.assertEqual(
            self.client.get(DIRECTORY).status_code, status.HTTP_401_UNAUTHORIZED
        )

    def test_directory_detail_404_for_unapproved(self):
        hidden = make_psychologist(approval_status=ApprovalStatus.PENDING)
        self.assertEqual(
            self.client.get(f"{DIRECTORY}{hidden.pk}/").status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_directory_detail_returns_card(self):
        r = self.client.get(f"{DIRECTORY}{self.psych.pk}/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(set(r.data), EXPECTED_CARD_KEYS)

    def test_request_then_current_shows_card_and_expiry(self):
        r = self.client.post(REQUESTS, {"psychologist": self.psych.pk}, format="json")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)
        current = self.client.get(CURRENT).data["relationship"]
        self.assertEqual(current["status"], "pending")
        self.assertIn("expires_at", current)
        self.assertEqual(current["psychologist"]["last_active"], "never")

    def test_request_without_dob_returns_exact_error(self):
        patient = make_patient(date_of_birth=False)
        self.client.force_authenticate(patient.user)
        r = self.client.post(REQUESTS, {"psychologist": self.psych.pk}, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            r.data,
            {
                "date_of_birth": [
                    "Add your date of birth to your profile before requesting a psychologist."
                ]
            },
        )

    def test_current_empty(self):
        self.assertEqual(self.client.get(CURRENT).data, {"relationship": None})

    def test_cancel_and_other_patients_404(self):
        rel_id = self.client.post(
            REQUESTS, {"psychologist": self.psych.pk}, format="json"
        ).data["id"]
        self.client.force_authenticate(make_patient().user)
        self.assertEqual(
            self.client.post(f"{REQUESTS}{rel_id}/cancel/").status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.client.force_authenticate(self.patient.user)
        self.assertEqual(
            self.client.post(f"{REQUESTS}{rel_id}/cancel/").data["status"], "cancelled"
        )

    def test_end_requires_strict_true(self):
        rel = services.request_psychologist(
            patient_user=self.patient.user, psychologist_id=self.psych.pk
        )
        services.accept_request(
            psychologist_user=self.psych.user, relationship_id=rel.pk
        )
        for body in (
            {"confirm": "true"},
            {"confirm": 1},
            {"confirm": False},
            {"confirm": None},
            {},
        ):
            with self.subTest(body=body):
                r = self.client.post(END, body, format="json")
                self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertEqual(
                    r.data,
                    {"confirm": ["Confirm that you want to end this relationship."]},
                )
        r = self.client.post(END, {"confirm": True}, format="json")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["status"], "ended")

    def test_end_confirm_field_is_strict_true(self):
        from apps.relationships.api.serializers import PatientEndSerializer

        self.assertIsInstance(PatientEndSerializer().fields["confirm"], StrictTrueField)

    def test_minimal_card_when_psychologist_not_visible(self):
        rel = services.request_psychologist(
            patient_user=self.patient.user, psychologist_id=self.psych.pk
        )
        services.accept_request(
            psychologist_user=self.psych.user, relationship_id=rel.pk
        )
        self.psych.user.approval_status = ApprovalStatus.PENDING  # paused
        self.psych.user.save()
        card = self.client.get(CURRENT).data["relationship"]["psychologist"]
        self.assertEqual(set(card), {"id", "full_name"})
        history_card = self.client.get(REQUESTS).data["results"][0]["psychologist"]
        self.assertEqual(set(history_card), {"id", "full_name"})

    def test_recent_lists_past_psychologist(self):
        rel = services.request_psychologist(
            patient_user=self.patient.user, psychologist_id=self.psych.pk
        )
        services.accept_request(
            psychologist_user=self.psych.user, relationship_id=rel.pk
        )
        services.patient_end_relationship(patient_user=self.patient.user, confirm=True)
        r = self.client.get(RECENT)
        self.assertEqual([c["id"] for c in r.data], [self.psych.pk])

    def test_license_number_absent_from_every_card(self):
        def check(card, where):
            with self.subTest(where=where):
                self.assertNotIn("license_number", card)
                self.assertEqual(set(card), EXPECTED_CARD_KEYS)

        check(self.client.get(DIRECTORY).data["results"][0], "directory list")
        check(self.client.get(f"{DIRECTORY}{self.psych.pk}/").data, "directory detail")
        rel = services.request_psychologist(
            patient_user=self.patient.user, psychologist_id=self.psych.pk
        )
        services.accept_request(
            psychologist_user=self.psych.user, relationship_id=rel.pk
        )
        check(self.client.get(CURRENT).data["relationship"]["psychologist"], "current")
        check(self.client.get(REQUESTS).data["results"][0]["psychologist"], "requests")
        services.patient_end_relationship(patient_user=self.patient.user, confirm=True)
        check(self.client.get(RECENT).data[0], "recent")

    def test_throttle_scopes(self):
        from apps.psychologists.api.views import DirectoryListView
        from apps.relationships.api.views import RequestListCreateView

        self.assertEqual(DirectoryListView.throttle_classes[0].scope, "directory")
        view = RequestListCreateView()
        view.request = type("R", (), {"method": "POST"})()
        self.assertEqual(view.get_throttles()[0].scope, "relationship_requests")
        view.request = type("R", (), {"method": "GET"})()
        self.assertEqual(view.get_throttles(), [])

    def test_throttle_rates_configured(self):
        rates = settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]
        self.assertEqual(rates["directory"], "60/min")
        self.assertEqual(rates["relationship_requests"], "10/hour")


class PatientEndpointAccessTests(APITestCase):
    """Every patient endpoint: login required (401), and IsPatient (403 for others)."""

    ENDPOINTS = [
        ("get", DIRECTORY),
        ("get", f"{DIRECTORY}1/"),
        ("get", REQUESTS),
        ("post", REQUESTS),
        ("post", f"{REQUESTS}1/cancel/"),
        ("get", CURRENT),
        ("post", END),
        ("get", RECENT),
    ]

    def setUp(self):
        cache.clear()

    def test_anonymous_gets_401_and_other_roles_403(self):
        others = {
            "psychologist": make_psychologist().user,
            "ngo": make_user(role=Role.NGO),
            "admin": make_admin(),
        }
        for method, url in self.ENDPOINTS:
            with self.subTest(method=method, url=url, who="anonymous"):
                self.client.force_authenticate(None)
                r = getattr(self.client, method)(url, {}, format="json")
                self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)
            for who, user in others.items():
                with self.subTest(method=method, url=url, who=who):
                    self.client.force_authenticate(user)
                    r = getattr(self.client, method)(url, {}, format="json")
                    self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_every_patient_view_declares_both_permissions(self):
        from apps.psychologists.api.views import DirectoryDetailView, DirectoryListView
        from apps.relationships.api.views import (
            CancelRequestView,
            CurrentRelationshipView,
            EndCurrentRelationshipView,
            RecentPsychologistsView,
            RequestListCreateView,
        )

        for view in (
            DirectoryListView,
            DirectoryDetailView,
            RequestListCreateView,
            CancelRequestView,
            CurrentRelationshipView,
            EndCurrentRelationshipView,
            RecentPsychologistsView,
        ):
            with self.subTest(view=view.__name__):
                self.assertIn(IsAuthenticated, view.permission_classes)
                self.assertIn(IsPatient, view.permission_classes)


class BadInputTests(APITestCase):
    """Malformed input is a 400, never a 500."""

    def setUp(self):
        cache.clear()
        self.patient = make_patient()
        self.accepting = make_psychologist()
        self.not_accepting = make_psychologist()
        PsychologistProfile.objects.filter(pk=self.not_accepting.pk).update(
            is_accepting_patients=False, not_accepting_reason="away"
        )
        self.client.force_authenticate(self.patient.user)

    def test_bad_directory_query_params_400(self):
        for params in (
            {"city": "abc"},
            {"city": "0"},
            {"city": "-3"},
            {"accepting": "maybe"},
            {"gender": "xyz"},
        ):
            with self.subTest(params=params):
                r = self.client.get(DIRECTORY, params)
                self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_accepting_filter_false_and_true(self):
        ids = lambda r: {c["id"] for c in r.data["results"]}  # noqa: E731
        r = self.client.get(DIRECTORY, {"accepting": "false"})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(ids(r), {self.not_accepting.pk})
        r = self.client.get(DIRECTORY, {"accepting": "true"})
        self.assertEqual(ids(r), {self.accepting.pk})
        r = self.client.get(DIRECTORY)
        self.assertEqual(ids(r), {self.accepting.pk, self.not_accepting.pk})

    def test_lowercase_country_filter(self):
        r = self.client.get(DIRECTORY, {"country": "pk"})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(len(r.data["results"]), 2)

    def test_whitespace_search_means_no_filter(self):
        r = self.client.get(DIRECTORY, {"search": "   "})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(len(r.data["results"]), 2)

    def test_bad_request_bodies_400(self):
        for body in (
            {"psychologist": "abc"},
            {"psychologist": 0},
            {"psychologist": -1},
            {"psychologist": None},
            {},
            {"psychologist": self.accepting.pk, "note": "hello"},
        ):
            with self.subTest(body=body):
                r = self.client.post(REQUESTS, body, format="json")
                self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unknown_and_pending_psychologist_same_generic_400(self):
        pending = make_psychologist(approval_status=ApprovalStatus.PENDING)
        missing = self.client.post(REQUESTS, {"psychologist": 999999}, format="json")
        hidden = self.client.post(REQUESTS, {"psychologist": pending.pk}, format="json")
        self.assertEqual(missing.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(hidden.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            missing.data, {"psychologist": ["This psychologist isn't available."]}
        )
        self.assertEqual(missing.data, hidden.data)


class DirectoryPaginationTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.patient = make_patient()
        for _ in range(51):
            make_psychologist()

    def setUp(self):
        cache.clear()
        self.client.force_authenticate(self.patient.user)

    def test_page_size_capped_at_50(self):
        r = self.client.get(DIRECTORY, {"page_size": 500})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(len(r.data["results"]), 50)
        self.assertEqual(r.data["count"], 51)

    def test_default_page_size_20(self):
        r = self.client.get(DIRECTORY)
        self.assertEqual(len(r.data["results"]), 20)

    def test_max_page_size_constant(self):
        self.assertEqual(StandardPagination.max_page_size, 50)
        self.assertEqual(StandardPagination.page_size, 20)
