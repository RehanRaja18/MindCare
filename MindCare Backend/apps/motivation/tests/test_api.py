"""API tests for /api/v1/motivation/quotes/ and /quotes/random/."""

from django.conf import settings
from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Role
from apps.motivation.models import Quote, QuoteCategory
from core.testing import make_patient, make_psychologist, make_user

LIST = "/api/v1/motivation/quotes/"
RANDOM = "/api/v1/motivation/quotes/random/"


class QuoteAPITests(APITestCase):
    def setUp(self):
        cache.clear()
        Quote.objects.all().delete()
        self.quote = Quote.objects.create(
            text="Hope is the thing with feathers.",
            author="Emily Dickinson",
            category=QuoteCategory.HOPE,
        )
        Quote.objects.create(text="Unattributed calm", category=QuoteCategory.CALM)
        Quote.objects.create(text="Hidden from the app", is_active=False)
        self.client.force_authenticate(make_patient().user)

    def tearDown(self):
        cache.clear()

    def test_list_is_paginated_active_only_with_exact_shape(self):
        r = self.client.get(LIST)
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        body = r.json()
        self.assertEqual(set(body), {"count", "next", "previous", "results"})
        self.assertEqual(body["count"], 2)
        self.assertEqual(
            body["results"][1],
            {
                "id": self.quote.pk,
                "text": "Hope is the thing with feathers.",
                "author": "Emily Dickinson",
                "category": "hope",
            },
        )
        # Blank author comes back as null, so the App can hide the byline.
        self.assertIsNone(body["results"][0]["author"])

    def test_category_filter_and_unknown_category(self):
        r = self.client.get(LIST, {"category": "hope"})
        self.assertEqual([q["id"] for q in r.json()["results"]], [self.quote.pk])
        bad = self.client.get(LIST, {"category": "surah"})
        self.assertEqual(bad.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("category", bad.json())

    def test_page_size_capped(self):
        Quote.objects.bulk_create(Quote(text=f"q{i}") for i in range(60))
        r = self.client.get(LIST, {"page_size": 100})
        self.assertEqual(len(r.json()["results"]), 50)

    def test_random_returns_one_active_quote_and_honours_category(self):
        r = self.client.get(RANDOM)
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertIn(
            r.json()["text"], {"Hope is the thing with feathers.", "Unattributed calm"}
        )
        r = self.client.get(RANDOM, {"category": "hope"})
        self.assertEqual(r.json()["id"], self.quote.pk)

    def test_random_404_when_nothing_active(self):
        Quote.objects.update(is_active=False)
        r = self.client.get(RANDOM)
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(r.json(), {"detail": "No quotes available."})

    def test_admin_change_shows_up_immediately(self):
        Quote.objects.create(text="Added in Django admin", category="calm")
        texts = [q["text"] for q in self.client.get(LIST).json()["results"]]
        self.assertEqual(texts[0], "Added in Django admin")

    def test_any_logged_in_user_but_not_anonymous(self):
        for user in (make_psychologist().user, make_user(role=Role.ADMIN)):
            self.client.force_authenticate(user)
            self.assertEqual(self.client.get(LIST).status_code, status.HTTP_200_OK)
            self.assertEqual(self.client.get(RANDOM).status_code, status.HTTP_200_OK)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(LIST).status_code, 401)
        self.assertEqual(self.client.get(RANDOM).status_code, 401)

    def test_throttled_per_user_and_both_endpoints_share_the_scope(self):
        rate = settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["motivation"]
        self.assertEqual(rate, "60/min")
        codes = [self.client.get(LIST).status_code for _ in range(30)]
        codes += [self.client.get(RANDOM).status_code for _ in range(31)]
        self.assertEqual(codes[:60], [status.HTTP_200_OK] * 60)
        self.assertEqual(codes[60], status.HTTP_429_TOO_MANY_REQUESTS)

    def test_documented_in_openapi_schema(self):
        schema = self.client.get("/api/schema/?format=json").json()
        list_op = schema["paths"][LIST]["get"]
        self.assertIn("category", {p["name"] for p in list_op["parameters"]})
        self.assertIn("404", schema["paths"][RANDOM]["get"]["responses"])
