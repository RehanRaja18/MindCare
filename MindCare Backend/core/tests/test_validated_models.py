"""ValidatedModelMixin: the field rules apply on save(), not only in the API,
so services, management commands and Django admin are covered too."""

from django.test import TestCase

from apps.accounts.models import Role, User
from apps.motivation.models import Quote
from apps.reference.models import City, Country, Language, Specialization
from core.exceptions import DomainValidationError
from core.testing import make_user


class SaveRunsFieldRulesTests(TestCase):
    def test_create_with_a_bad_name_is_refused(self):
        with self.assertRaises(DomainValidationError) as ctx:
            User.objects.create_user(
                email="bad@example.com",
                password="strongpass123",
                full_name="Agent 007",
                role=Role.PATIENT,
            )
        self.assertIn("full_name", ctx.exception.errors)
        self.assertFalse(User.objects.filter(email="bad@example.com").exists())

    def test_values_are_normalised_on_save(self):
        user = make_user(role=Role.PATIENT, full_name="  Sara    Ahmed ")
        user.refresh_from_db()
        self.assertEqual(user.full_name, "Sara Ahmed")

    def test_legacy_row_can_still_save_other_fields(self):
        # A row stored before the rule (written with QuerySet.update, which
        # bypasses save()) must still be able to log in: login saves only
        # last_login.
        user = make_user(role=Role.PSYCHOLOGIST)
        User.objects.filter(pk=user.pk).update(full_name="Dr. Old Name (Demo)")
        user.refresh_from_db()
        user.save(update_fields=["last_login"])  # no error
        with self.assertRaises(DomainValidationError):
            user.save()  # a full save re-validates the name
        with self.assertRaises(DomainValidationError):
            user.save(update_fields=["full_name"])

    def test_quote_rules(self):
        with self.assertRaises(DomainValidationError) as ctx:
            Quote.objects.create(text="<b>Be brave</b> always and forever")
        self.assertEqual(
            ctx.exception.errors, {"text": ["Quote can't contain HTML tags."]}
        )
        with self.assertRaises(DomainValidationError):
            Quote.objects.create(text="A fine quote here.", author="Author 2")


class SeededReferenceDataPassesTheRulesTests(TestCase):
    """Every row seeded by migrations is valid, so an admin can edit any of them."""

    def test_every_seeded_row_validates(self):
        for model in (Country, Language, Specialization, City):
            for row in model.objects.all():
                with self.subTest(model=model.__name__, row=str(row)):
                    row.full_clean(validate_unique=False, validate_constraints=False)

    def test_every_seeded_quote_validates(self):
        for quote in Quote.objects.all():
            with self.subTest(quote=quote.text[:30]):
                quote.full_clean()


class DjangoAdminUsesTheRulesTests(TestCase):
    def test_admin_change_form_rejects_a_bad_name(self):
        from django.urls import reverse

        from core.testing import admin_change_form_data

        root = User.objects.create_superuser(
            email="root@example.com", password="strongpass123"
        )
        self.client.force_login(root)
        target = make_user(role=Role.PATIENT, full_name="Sara Ahmed")
        url = reverse("admin:accounts_user_change", args=[target.pk])
        data = admin_change_form_data(self.client.get(url))
        data["full_name"] = "Sara Ahmed 2"
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)  # form redisplayed
        self.assertContains(response, "Full name can only contain letters")
        target.refresh_from_db()
        self.assertEqual(target.full_name, "Sara Ahmed")
