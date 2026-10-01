"""`manage.py test` must switch to the guarded test settings."""

import os
import subprocess
import sys
from pathlib import Path

from django.test import SimpleTestCase

BACKEND_DIR = Path(__file__).resolve().parents[2]


class ManagePyTestGuardTests(SimpleTestCase):
    def test_manage_test_uses_guarded_settings(self):
        # Fails at settings import (non-local TEST_DATABASE_URL), before any DB
        # connection is attempted. Never runs the real test command.
        result = subprocess.run(
            [sys.executable, "manage.py", "test", "--help"],
            cwd=BACKEND_DIR,
            env={
                **os.environ,
                "TEST_DATABASE_URL": "postgresql://x:y@db.not-a-real-host.invalid:5432/nope",
                "DJANGO_SETTINGS_MODULE": "config.settings.dev",
            },
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "Tests must run against a local, disposable Postgres", result.stderr
        )
