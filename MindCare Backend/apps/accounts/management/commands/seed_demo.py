"""Create (or with --remove, delete) the clearly fake demo accounts.

    DEMO_PASSWORD=... python manage.py seed_demo
    python manage.py seed_demo --remove

Idempotent. The password comes only from the DEMO_PASSWORD environment variable
and is never printed. See apps/accounts/demo.py for the accounts.
"""

import os

from django.core.management.base import BaseCommand, CommandError

from apps.accounts import demo
from core.exceptions import DomainValidationError


class Command(BaseCommand):
    help = (
        "Create 6 approved demo psychologists and 2 demo patients (or --remove them)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--remove",
            action="store_true",
            help="Delete the demo accounts (and their relationship rows) instead.",
        )

    def handle(self, *args, remove=False, **options):
        if remove:
            result = demo.remove_demo_accounts()
            self.stdout.write(
                self.style.SUCCESS(
                    f"Removed {result['users']} demo accounts and "
                    f"{result['relationships']} relationship rows."
                )
            )
            return

        password = os.environ.get("DEMO_PASSWORD", "")
        if not password:
            raise CommandError("Set the DEMO_PASSWORD environment variable first.")
        try:
            result = demo.seed_demo_accounts(password=password)
        except DomainValidationError as exc:
            raise CommandError(f"Seeding failed: {exc.errors}") from exc
        self.stdout.write(
            self.style.SUCCESS(
                f"Demo accounts: {result['created']} created, "
                f"{result['existing']} already existed."
            )
        )
        for email in demo.DEMO_EMAILS:
            self.stdout.write(f"  {email}")
