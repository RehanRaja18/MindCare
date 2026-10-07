"""Psychologist-facing relationship API, including two-psychologist privacy."""

from datetime import date, timedelta

from django.core.cache import cache
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.test import APITestCase

from apps.accounts.models import ApprovalStatus, Role
from apps.psychologists.api.views import AvailabilityView
from apps.relationships import services
from apps.relationships.api.serializers import ASSIGNED_PATIENT_FIELDS
from apps.relationships.api.views import (
    AcceptRequestView,
    DeclineRequestView,
    HistoryView,
    InboxView,
    PatientDetailView,
    PatientEndView,
    PatientListView,
)
from apps.relationships.models import CareRelationship, RelationshipStatus
from core.permissions import IsApprovedPsychologist, IsPsychologist
from core.testing import make_admin, make_patient, make_psychologist, make_user

BASE = "/api/v1/relationships"
AVAILABILITY = "/api/v1/psychologists/me/availability/"


def _accept(patient, psych):
    rel = services.request_psychologist(
        patient_user=patient.user, psychologist_id=psych.pk
    )
    return services.accept_request(psychologist_user=psych.user, relationship_id=rel.pk)


def _ended(patient, psych):
    rel = _accept(patient, psych)
    services.patient_end_relationship(patient_user=patient.user, confirm=True)
    rel.refresh_from_db()
    return rel


def _all_keys(data):
    """Every dict key anywhere in a JSON-like structure."""
    keys = set()
    if isinstance(data, dict):
        for key, value in data.items():
            keys.add(key)
            keys |= _all_keys(value)
    elif isinstance(data, list):
        for item in data:
            keys |= _all_keys(item)
    return keys


class InboxAndAnswerTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.psych = make_psychologist()
        self.patient = make_patient(full_name="Bilal Hassan")
        self.rel = services.request_psychologist(
            patient_user=self.patient.user, psychologist_id=self.psych.pk
        )
        self.client.force_authenticate(self.psych.user)

    def test_inbox_item_shape_no_identity(self):
        item = self.client.get(f"{BASE}/inbox/").data[0]
        self.assertEqual(set(item), {"id", "requested_at", "expires_at", "requester"})
        self.assertEqual(
            set(item["requester"]),
            {"pseudonym", "preferred_language", "timezone", "country", "gender", "age"},
        )
        self.assertNotIn("Bilal Hassan", str(item))

    def test_accept_and_decline(self):
        r = self.client.post(f"{BASE}/requests/{self.rel.pk}/accept/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data, {"id": self.rel.pk, "status": "accepted"})
        other = make_patient()
        rel2 = services.request_psychologist(
            patient_user=other.user, psychologist_id=self.psych.pk
        )
        r = self.client.post(
            f"{BASE}/requests/{rel2.pk}/decline/", {"reason": "other"}, format="json"
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data, {"id": rel2.pk, "status": "declined"})

    def test_decline_rejects_unknown_reason_and_unknown_keys(self):
        url = f"{BASE}/requests/{self.rel.pk}/decline/"
        r = self.client.post(url, {"reason": "nope"}, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        r = self.client.post(url, {"note": "hi"}, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.rel.refresh_from_db()
        self.assertEqual(self.rel.status, RelationshipStatus.PENDING)

    def test_decline_without_reason_is_allowed(self):
        r = self.client.post(
            f"{BASE}/requests/{self.rel.pk}/decline/", {}, format="json"
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_patient_role_forbidden(self):
        self.client.force_authenticate(self.patient.user)
        self.assertEqual(
            self.client.get(f"{BASE}/inbox/").status_code, status.HTTP_403_FORBIDDEN
        )


class AssignedPatientTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.psych = make_psychologist()
        self.patient = make_patient(full_name="Bilal Hassan")
        self.rel = _accept(self.patient, self.psych)
        self.client.force_authenticate(self.psych.user)

    def test_patient_detail_has_age_never_date_of_birth(self):
        data = self.client.get(f"{BASE}/patients/{self.rel.pk}/").data
        self.assertEqual(set(data), set(ASSIGNED_PATIENT_FIELDS))
        self.assertNotIn("date_of_birth", data)
        self.assertEqual(data["full_name"], "Bilal Hassan")
        self.assertIsInstance(data["age"], int)

    def test_end_requires_reason_and_rejects_patient_unresponsive(self):
        url = f"{BASE}/patients/{self.rel.pk}/end/"
        r = self.client.post(url, {}, format="json")
        self.assertEqual(r.data, {"reason": ["Choose a reason."]})
        r = self.client.post(url, {"reason": "patient_unresponsive"}, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        r = self.client.post(url, {"reason": "treatment_completed"}, format="json")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["end_reason"], "treatment_completed")
        self.assertEqual(r.data["ended_by"], "psychologist")

    def test_end_with_empty_or_missing_reason_gets_one_message(self):
        url = f"{BASE}/patients/{self.rel.pk}/end/"
        before = CareRelationship.objects.get(pk=self.rel.pk).updated_at
        for label, body in (
            ("missing", {}),
            ("null", {"reason": None}),
            ("empty", {"reason": ""}),
            ("whitespace", {"reason": "   "}),
        ):
            with self.subTest(body=label):
                r = self.client.post(url, body, format="json")
                self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertEqual(r.json(), {"reason": ["Choose a reason."]})
        self.rel.refresh_from_db()
        self.assertEqual(self.rel.status, RelationshipStatus.ACCEPTED)
        self.assertEqual(self.rel.updated_at, before)

    def test_end_with_unknown_reason_is_400_and_row_unchanged(self):
        url = f"{BASE}/patients/{self.rel.pk}/end/"
        for code in ("nope", "patient_unresponsive"):
            with self.subTest(code=code):
                r = self.client.post(url, {"reason": code}, format="json")
                self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn("reason", r.json())
        self.rel.refresh_from_db()
        self.assertEqual(self.rel.status, RelationshipStatus.ACCEPTED)

    def test_history_is_pseudonym_only(self):
        services.patient_end_relationship(patient_user=self.patient.user, confirm=True)
        item = self.client.get(f"{BASE}/history/").data[0]
        self.assertEqual(
            set(item),
            {
                "relationship_id",
                "pseudonym",
                "accepted_at",
                "ended_at",
                "ended_by",
                "end_reason",
            },
        )
        self.assertNotIn("Bilal Hassan", str(item))
        self.assertEqual(item["pseudonym"], self.patient.pseudonym)


class TwoPsychologistPrivacyTests(APITestCase):
    """A and B each have accepted patients, pending requests and ended
    relationships, all created through the real services; neither sees the
    other's rows."""

    def setUp(self):
        cache.clear()
        self.a, self.b = make_psychologist(), make_psychologist()
        self.pa = make_patient(full_name="Patient Of A")
        self.pb = make_patient(full_name="Patient Of B")
        self.rel_a = _accept(self.pa, self.a)
        self.rel_b = _accept(self.pb, self.b)
        self.pend_a = services.request_psychologist(
            patient_user=make_patient(full_name="Pending For A").user,
            psychologist_id=self.a.pk,
        )
        self.pend_b = services.request_psychologist(
            patient_user=make_patient(full_name="Pending For B").user,
            psychologist_id=self.b.pk,
        )
        self.ended_a = _ended(make_patient(full_name="Former Of A"), self.a)
        self.ended_b = _ended(make_patient(full_name="Former Of B"), self.b)

    def _lists(self, psych):
        self.client.force_authenticate(psych.user)
        inbox = self.client.get(f"{BASE}/inbox/").data
        patients = self.client.get(f"{BASE}/patients/").data
        history = self.client.get(f"{BASE}/history/").data
        return inbox, patients, history

    def test_each_sees_only_their_own(self):
        for psych, rel, pend, ended, name in (
            (self.a, self.rel_a, self.pend_a, self.ended_a, "Patient Of A"),
            (self.b, self.rel_b, self.pend_b, self.ended_b, "Patient Of B"),
        ):
            inbox, patients, history = self._lists(psych)
            self.assertEqual([i["id"] for i in inbox], [pend.pk])
            self.assertEqual(
                [i["requester"]["pseudonym"] for i in inbox], [pend.patient.pseudonym]
            )
            self.assertEqual([p["relationship_id"] for p in patients], [rel.pk])
            self.assertEqual([p["full_name"] for p in patients], [name])
            self.assertEqual([h["relationship_id"] for h in history], [ended.pk])
            self.assertEqual(
                [h["pseudonym"] for h in history], [ended.patient.pseudonym]
            )

    def test_b_cannot_touch_a_rows_404_and_rows_unchanged(self):
        before = {
            r.pk: (r.status, r.updated_at)
            for r in CareRelationship.objects.filter(
                pk__in=[self.rel_a.pk, self.pend_a.pk, self.ended_a.pk]
            )
        }
        self.client.force_authenticate(self.b.user)
        attempts = [
            ("post", f"{BASE}/requests/{self.pend_a.pk}/accept/", None),
            ("post", f"{BASE}/requests/{self.pend_a.pk}/decline/", {"reason": "other"}),
            ("get", f"{BASE}/patients/{self.rel_a.pk}/", None),
            ("post", f"{BASE}/patients/{self.rel_a.pk}/end/", {"reason": "other"}),
            ("get", f"{BASE}/patients/{self.ended_a.pk}/", None),
            ("post", f"{BASE}/patients/{self.ended_a.pk}/end/", {"reason": "other"}),
        ]
        for method, url, body in attempts:
            with self.subTest(method=method, url=url):
                r = getattr(self.client, method)(url, body, format="json")
                self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)
                self.assertNotIn(b"Patient Of A", r.content)
        after = {
            r.pk: (r.status, r.updated_at)
            for r in CareRelationship.objects.filter(pk__in=list(before))
        }
        self.assertEqual(before, after)
        self.assertEqual(before[self.pend_a.pk][0], RelationshipStatus.PENDING)
        self.assertEqual(before[self.rel_a.pk][0], RelationshipStatus.ACCEPTED)

    def test_access_disappears_immediately_when_patient_ends(self):
        self.client.force_authenticate(self.a.user)
        self.assertEqual(
            self.client.get(f"{BASE}/patients/{self.rel_a.pk}/").status_code,
            status.HTTP_200_OK,
        )
        services.patient_end_relationship(patient_user=self.pa.user, confirm=True)
        self.assertEqual(
            self.client.get(f"{BASE}/patients/{self.rel_a.pk}/").status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(self.client.get(f"{BASE}/patients/").data, [])
        history = self.client.get(f"{BASE}/history/").data
        self.assertIn(self.rel_a.pk, [h["relationship_id"] for h in history])
        self.assertNotIn("Patient Of A", str(history))


class AvailabilityAPITests(APITestCase):
    def setUp(self):
        self.psych = make_psychologist()
        self.client.force_authenticate(self.psych.user)

    def test_get_and_put(self):
        self.assertEqual(
            self.client.get(AVAILABILITY).data, {"accepting": True, "reason": None}
        )
        r = self.client.put(AVAILABILITY, {"accepting": False}, format="json")
        self.assertEqual(
            r.data,
            {"reason": ["Choose a reason when you're not accepting new patients."]},
        )
        r = self.client.put(
            AVAILABILITY, {"accepting": False, "reason": "away"}, format="json"
        )
        self.assertEqual(r.data, {"accepting": False, "reason": "away"})
        r = self.client.put(AVAILABILITY, {"accepting": True}, format="json")
        self.assertEqual(r.data, {"accepting": True, "reason": None})

    def _profile_state(self):
        self.psych.refresh_from_db()
        return (
            self.psych.is_accepting_patients,
            self.psych.not_accepting_reason,
            self.psych.updated_at,
        )

    def test_not_accepting_with_empty_or_missing_reason_gets_one_message(self):
        before = self._profile_state()
        for label, body in (
            ("missing", {"accepting": False}),
            ("null", {"accepting": False, "reason": None}),
            ("empty", {"accepting": False, "reason": ""}),
            ("whitespace", {"accepting": False, "reason": "   "}),
        ):
            with self.subTest(body=label):
                r = self.client.put(AVAILABILITY, body, format="json")
                self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertEqual(
                    r.json(),
                    {
                        "reason": [
                            "Choose a reason when you're not accepting new patients."
                        ]
                    },
                )
        self.assertEqual(self._profile_state(), before)

    def test_not_accepting_with_unknown_reason_is_400_and_profile_unchanged(self):
        before = self._profile_state()
        r = self.client.put(
            AVAILABILITY, {"accepting": False, "reason": "nope"}, format="json"
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("reason", r.json())
        self.assertEqual(self._profile_state(), before)

    def test_accepting_with_blank_or_null_reason_succeeds_and_clears_it(self):
        for label, reason in (("null", None), ("empty", ""), ("whitespace", "   ")):
            with self.subTest(reason=label):
                self.client.put(
                    AVAILABILITY, {"accepting": False, "reason": "away"}, format="json"
                )
                r = self.client.put(
                    AVAILABILITY, {"accepting": True, "reason": reason}, format="json"
                )
                self.assertEqual(r.status_code, status.HTTP_200_OK)
                self.assertEqual(r.json(), {"accepting": True, "reason": None})
                self.psych.refresh_from_db()
                self.assertTrue(self.psych.is_accepting_patients)
                self.assertIsNone(self.psych.not_accepting_reason)

    def test_put_rejects_unknown_keys(self):
        r = self.client.put(
            AVAILABILITY, {"accepting": True, "pseudonym": "x"}, format="json"
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)


PSYCHOLOGIST_VIEWS = [
    InboxView,
    AcceptRequestView,
    DeclineRequestView,
    PatientListView,
    PatientDetailView,
    PatientEndView,
    HistoryView,
    AvailabilityView,
]


class PsychologistEndpointAccessTests(APITestCase):
    """Every Phase 3 psychologist endpoint: login + psychologist role + approved,
    active account. (With a real JWT, an inactive user is already rejected at
    authentication with 401; force_authenticate skips that, so the permission
    layer must answer 403 on its own.)"""

    def setUp(self):
        cache.clear()
        self.psych = make_psychologist()
        self.rel = _accept(make_patient(), self.psych)
        self.pending = services.request_psychologist(
            patient_user=make_patient().user, psychologist_id=self.psych.pk
        )

    def _endpoints(self):
        return [
            ("get", f"{BASE}/inbox/", None),
            ("post", f"{BASE}/requests/{self.pending.pk}/accept/", None),
            ("post", f"{BASE}/requests/{self.pending.pk}/decline/", {}),
            ("get", f"{BASE}/patients/", None),
            ("get", f"{BASE}/patients/{self.rel.pk}/", None),
            ("post", f"{BASE}/patients/{self.rel.pk}/end/", {"reason": "other"}),
            ("get", f"{BASE}/history/", None),
            ("get", AVAILABILITY, None),
            ("put", AVAILABILITY, {"accepting": False, "reason": "away"}),
        ]

    def _call(self, method, url, body):
        return getattr(self.client, method)(url, body, format="json")

    def test_views_declare_all_three_permission_classes(self):
        for view in PSYCHOLOGIST_VIEWS:
            with self.subTest(view=view.__name__):
                for cls in (IsAuthenticated, IsPsychologist, IsApprovedPsychologist):
                    self.assertIn(cls, view.permission_classes)

    def test_anonymous_gets_401(self):
        for method, url, body in self._endpoints():
            with self.subTest(method=method, url=url):
                self.assertEqual(
                    self._call(method, url, body).status_code,
                    status.HTTP_401_UNAUTHORIZED,
                )

    def test_wrong_role_or_unapproved_or_inactive_gets_403(self):
        actors = {
            "patient": make_patient().user,
            "ngo": make_user(role=Role.NGO),
            "admin": make_admin(),
            "pending psychologist": make_psychologist(
                approval_status=ApprovalStatus.PENDING
            ).user,
            "rejected psychologist": make_psychologist(
                approval_status=ApprovalStatus.REJECTED
            ).user,
            "inactive psychologist": make_psychologist(is_active=False).user,
        }
        for label, user in actors.items():
            self.client.force_authenticate(user)
            for method, url, body in self._endpoints():
                with self.subTest(actor=label, method=method, url=url):
                    self.assertEqual(
                        self._call(method, url, body).status_code,
                        status.HTTP_403_FORBIDDEN,
                    )
        self.rel.refresh_from_db()
        self.pending.refresh_from_db()
        self.assertEqual(self.rel.status, RelationshipStatus.ACCEPTED)
        self.assertEqual(self.pending.status, RelationshipStatus.PENDING)

    def test_paused_psychologist_loses_access_to_own_rows(self):
        user = self.psych.user
        user.approval_status = ApprovalStatus.PENDING
        user.save(update_fields=["approval_status"])
        self.client.force_authenticate(user)
        for method, url, body in self._endpoints():
            with self.subTest(method=method, url=url):
                self.assertEqual(
                    self._call(method, url, body).status_code,
                    status.HTTP_403_FORBIDDEN,
                )
        self.rel.refresh_from_db()
        self.assertEqual(self.rel.status, RelationshipStatus.ACCEPTED)


DOB = date(1990, 7, 15)


class NoDateOfBirthInPsychologistResponsesTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.psych = make_psychologist()
        self.accepted_patient = make_patient(date_of_birth=DOB)
        self.ending_patient = make_patient(date_of_birth=DOB)
        self.history_patient = make_patient(date_of_birth=DOB)
        self.rel = _accept(self.accepted_patient, self.psych)
        self.to_end = _accept(self.ending_patient, self.psych)
        _ended(self.history_patient, self.psych)
        self.to_accept = services.request_psychologist(
            patient_user=make_patient(date_of_birth=DOB).user,
            psychologist_id=self.psych.pk,
        )
        self.to_decline = services.request_psychologist(
            patient_user=make_patient(date_of_birth=DOB).user,
            psychologist_id=self.psych.pk,
        )
        self.client.force_authenticate(self.psych.user)

    def _assert_clean(self, response, label):
        self.assertLess(response.status_code, 300, label)
        self.assertNotIn("date_of_birth", _all_keys(response.json()), label)
        self.assertNotIn(DOB.isoformat().encode(), response.content, label)

    def test_every_psychologist_endpoint(self):
        inbox = self.client.get(f"{BASE}/inbox/")
        self._assert_clean(inbox, "inbox")
        self.assertEqual(len(inbox.json()), 2)
        for item in inbox.json():
            self.assertIsInstance(item["requester"]["age"], int)

        patients = self.client.get(f"{BASE}/patients/")
        self._assert_clean(patients, "patients")
        self.assertEqual(len(patients.json()), 2)
        for item in patients.json():
            self.assertIsInstance(item["age"], int)

        detail = self.client.get(f"{BASE}/patients/{self.rel.pk}/")
        self._assert_clean(detail, "patient detail")
        self.assertIsInstance(detail.json()["age"], int)

        self._assert_clean(self.client.get(f"{BASE}/history/"), "history")
        self._assert_clean(
            self.client.post(f"{BASE}/requests/{self.to_accept.pk}/accept/"), "accept"
        )
        self._assert_clean(
            self.client.post(
                f"{BASE}/requests/{self.to_decline.pk}/decline/",
                {"reason": "other"},
                format="json",
            ),
            "decline",
        )
        self._assert_clean(
            self.client.post(
                f"{BASE}/patients/{self.to_end.pk}/end/",
                {"reason": "treatment_completed"},
                format="json",
            ),
            "end",
        )
        self._assert_clean(self.client.get(AVAILABILITY), "availability get")
        self._assert_clean(
            self.client.put(
                AVAILABILITY, {"accepting": False, "reason": "away"}, format="json"
            ),
            "availability put",
        )


class GetNeverWritesStatusTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.psych = make_psychologist()
        self.accepted_patient = make_patient()
        self.rel = _accept(self.accepted_patient, self.psych)
        _ended(make_patient(), self.psych)
        self.stale_patients = [make_patient(), make_patient()]
        past = timezone.now() - timedelta(days=5)
        self.stale = []
        for patient in self.stale_patients:
            rel = services.request_psychologist(
                patient_user=patient.user, psychologist_id=self.psych.pk
            )
            # QuerySet.update bypasses auto_now, so updated_at is the baseline.
            CareRelationship.objects.filter(pk=rel.pk).update(
                requested_at=past, expires_at=past + timedelta(days=3)
            )
            rel.refresh_from_db()
            self.stale.append((rel, rel.updated_at))

    def test_gets_leave_stale_rows_pending(self):
        self.client.force_authenticate(self.psych.user)
        inbox = self.client.get(f"{BASE}/inbox/")
        self.assertEqual(inbox.status_code, status.HTTP_200_OK)
        self.assertEqual(inbox.data, [])
        for url in (
            f"{BASE}/patients/",
            f"{BASE}/patients/{self.rel.pk}/",
            f"{BASE}/history/",
            AVAILABILITY,
        ):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, status.HTTP_200_OK)

        for patient in self.stale_patients:
            self.client.force_authenticate(patient.user)
            for url in (
                "/api/v1/psychologists/directory/",
                f"{BASE}/requests/",
                f"{BASE}/current/",
                f"{BASE}/recent/",
            ):
                with self.subTest(url=url):
                    self.assertEqual(
                        self.client.get(url).status_code, status.HTTP_200_OK
                    )

        for rel, updated_at in self.stale:
            rel.refresh_from_db()
            self.assertEqual(rel.status, RelationshipStatus.PENDING)
            self.assertEqual(rel.updated_at, updated_at)
