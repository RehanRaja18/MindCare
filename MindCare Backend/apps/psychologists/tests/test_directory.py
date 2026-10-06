"""Directory selectors: visibility, filters, ordering."""

from datetime import timedelta

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.accounts.models import ApprovalStatus, User
from apps.psychologists.selectors import get_directory_entry, list_directory
from apps.reference.models import Language, Specialization
from core.testing import make_psychologist


def _set_last_active(profile, when):
    User.objects.filter(pk=profile.user_id).update(last_active_at=when)


def _stop_accepting(profile):
    profile.is_accepting_patients = False
    profile.not_accepting_reason = "fully_booked"
    profile.save()


class DirectoryTests(TestCase):
    def setUp(self):
        self.visible = make_psychologist(full_name="Dr Aamir")
        self.pending = make_psychologist(approval_status=ApprovalStatus.PENDING)
        self.inactive = make_psychologist(is_active=False)

    def test_only_approved_active(self):
        ids = {p.pk for p in list_directory()}
        self.assertIn(self.visible.pk, ids)
        self.assertNotIn(self.pending.pk, ids)
        self.assertNotIn(self.inactive.pk, ids)
        self.assertIsNone(get_directory_entry(profile_id=self.pending.pk))
        self.assertEqual(get_directory_entry(profile_id=self.visible.pk), self.visible)

    def test_filters(self):
        other = make_psychologist(
            specializations=list(Specialization.objects.filter(slug="grief")),
            languages=list(Language.objects.filter(code="en")),
            gender="female",
            city="Karachi",
        )
        self.assertEqual(
            [p.pk for p in list_directory(specialization="grief")], [other.pk]
        )
        self.assertNotIn(other.pk, [p.pk for p in list_directory(language="ur")])
        self.assertEqual([p.pk for p in list_directory(gender="female")], [other.pk])
        self.assertEqual([p.pk for p in list_directory(city=other.city_id)], [other.pk])
        self.assertIn(other.pk, [p.pk for p in list_directory(country="PK")])
        self.assertEqual(
            [p.pk for p in list_directory(search="aamir")], [self.visible.pk]
        )

    def test_accepting_filter_and_ordering(self):
        busy = make_psychologist()
        _stop_accepting(busy)
        recent = make_psychologist()
        _set_last_active(recent, timezone.now())
        older = make_psychologist()
        _set_last_active(older, timezone.now() - timedelta(days=3))
        ordered = [p.pk for p in list_directory()]
        self.assertLess(ordered.index(recent.pk), ordered.index(older.pk))
        self.assertLess(
            ordered.index(older.pk), ordered.index(busy.pk)
        )  # accepting first
        self.assertNotIn(busy.pk, [p.pk for p in list_directory(accepting=True)])
        self.assertEqual([p.pk for p in list_directory(accepting=False)], [busy.pk])

    def test_ordering_accepting_then_recent_then_never_active_last(self):
        now = timezone.now()
        # Names chosen so alphabetical order (A3, N2, N1, A2, A1) differs from the
        # expected order: the test can't pass by name ordering alone.
        a1 = make_psychologist(full_name="Zara Accepting Recent")
        _set_last_active(a1, now - timedelta(hours=1))
        a2 = make_psychologist(full_name="Yusuf Accepting Older")
        _set_last_active(a2, now - timedelta(days=3))
        a3 = make_psychologist(
            full_name="Aaliya Accepting Never"
        )  # last_active_at NULL
        n1 = make_psychologist(full_name="Omar Busy Recent")
        _set_last_active(n1, now - timedelta(hours=1))
        _stop_accepting(n1)
        n2 = make_psychologist(full_name="Bilal Busy Never")  # last_active_at NULL
        _stop_accepting(n2)

        wanted = {a1.pk, a2.pk, a3.pk, n1.pk, n2.pk}
        ordered = [p.pk for p in list_directory() if p.pk in wanted]
        self.assertEqual(ordered, [a1.pk, a2.pk, a3.pk, n1.pk, n2.pk])

    def test_specialization_and_language_filters_return_no_duplicates(self):
        both = make_psychologist(
            specializations=list(
                Specialization.objects.filter(slug__in=["grief", "trauma-ptsd", "ocd"])
            ),
            languages=list(Language.objects.filter(code__in=["en", "ur"])),
        )
        rows = [p.pk for p in list_directory(specialization="grief", language="en")]
        self.assertEqual(rows.count(both.pk), 1)

    def _measure_directory(self):
        with CaptureQueriesContext(connection) as ctx:
            results = list(list_directory())
            for p in results:
                p.user.full_name
                p.user.last_active_at
                p.country.name
                if p.city is not None:
                    p.city.name
                    p.city.country.name
                [s.name for s in p.specializations.all()]
                [lang.name for lang in p.languages.all()]
        return len(results), len(ctx.captured_queries)

    def test_directory_has_no_per_row_queries(self):
        make_psychologist()  # 2 visible with self.visible
        rows_small, queries_small = self._measure_directory()
        self.assertEqual(rows_small, 2)
        for _ in range(5):
            make_psychologist()
        rows_large, queries_large = self._measure_directory()
        self.assertEqual(rows_large, 7)
        self.assertEqual(queries_small, queries_large)
        self.assertLessEqual(queries_large, 3)  # main query + 2 prefetches
