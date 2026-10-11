"""Read-path tests for the Motivation Corner (apps/motivation/selectors.py) and
the seed migration."""

from django.test import TestCase

from apps.motivation import selectors
from apps.motivation.models import Quote, QuoteCategory


class SeededQuotesTests(TestCase):
    def test_migration_seeds_about_thirty_active_text_quotes(self):
        seeded = Quote.objects.all()
        self.assertGreaterEqual(seeded.count(), 30)
        self.assertTrue(all(q.is_active for q in seeded))
        for q in seeded:
            self.assertLessEqual(len(q.text), 200, q.text)
            self.assertIn(q.category, QuoteCategory.values)
            self.assertTrue(q.author)
        self.assertEqual(
            set(seeded.values_list("category", flat=True)), set(QuoteCategory.values)
        )


class ActiveQuotesTests(TestCase):
    def setUp(self):
        Quote.objects.all().delete()
        self.hope = Quote.objects.create(
            text="Hope is a waking dream", category=QuoteCategory.HOPE
        )
        self.calm = Quote.objects.create(
            text="Calm seas, steady mind", category=QuoteCategory.CALM
        )
        self.none = Quote.objects.create(text="No category")
        Quote.objects.create(
            text="Hidden from the app", category="hope", is_active=False
        )

    def test_active_only_newest_first(self):
        self.assertEqual(
            list(selectors.active_quotes()), [self.none, self.calm, self.hope]
        )

    def test_category_filter(self):
        self.assertEqual(list(selectors.active_quotes(category="hope")), [self.hope])

    def test_random_returns_an_active_quote(self):
        seen = {selectors.random_active_quote() for _ in range(30)}
        self.assertTrue(seen <= {self.hope, self.calm, self.none})
        self.assertGreater(len(seen), 1)

    def test_random_with_category_and_with_nothing_active(self):
        self.assertEqual(selectors.random_active_quote(category="calm"), self.calm)
        Quote.objects.update(is_active=False)
        self.assertIsNone(selectors.random_active_quote())
