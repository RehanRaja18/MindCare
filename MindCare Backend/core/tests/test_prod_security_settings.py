"""Production security headers (docs/decisions.md, 2026-10-10: HSTS)."""

import os
import subprocess
import sys
from pathlib import Path

from django.test import SimpleTestCase

BACKEND = Path(__file__).resolve().parents[2]


def _prod(expr):
    env = {**os.environ, "SECRET_KEY": os.environ.get("SECRET_KEY", "x")}
    out = subprocess.run(
        [sys.executable, "-c", f"import config.settings.prod as s; print({expr})"],
        cwd=BACKEND,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    return out.stdout.strip()


class ProdSecuritySettingsTests(SimpleTestCase):
    def test_hsts_starts_at_one_day_without_subdomains(self):
        self.assertEqual(_prod("s.SECURE_HSTS_SECONDS"), "86400")
        self.assertEqual(
            _prod("getattr(s, 'SECURE_HSTS_INCLUDE_SUBDOMAINS', False)"), "False"
        )
