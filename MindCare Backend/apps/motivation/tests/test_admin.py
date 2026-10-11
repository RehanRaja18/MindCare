"""Django admin for quotes: admins add, search and toggle them."""

from django.test import TestCase

from apps.motivation.models import Quote
from core.testing import make_admin


class QuoteAdminTests(TestCase):
    def setUp(self):
        admin = make_admin(is_staff=True, is_superuser=True)
        self.client.force_login(admin)

    def test_changelist_search_and_add(self):
        r = self.client.get("/admin/motivation/quote/", {"q": "feathers"})
        self.assertEqual(r.status_code, 200)
        r = self.client.post(
            "/admin/motivation/quote/add/",
            {
                "text": "A new quote",
                "author": "",
                "category": "calm",
                "is_active": "on",
            },
        )
        self.assertEqual(r.status_code, 302)
        self.assertTrue(
            Quote.objects.filter(text="A new quote", is_active=True).exists()
        )

    def test_deactivate_and_activate_actions(self):
        q = Quote.objects.create(text="Toggle me please")
        url = "/admin/motivation/quote/"
        self.client.post(url, {"action": "deactivate", "_selected_action": [q.pk]})
        q.refresh_from_db()
        self.assertFalse(q.is_active)
        self.client.post(url, {"action": "activate", "_selected_action": [q.pk]})
        q.refresh_from_db()
        self.assertTrue(q.is_active)
