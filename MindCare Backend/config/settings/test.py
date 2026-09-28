"""Settings used when running the test suite (pytest-django)."""

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F401,F403

DEBUG = False

# Tests never inherit DATABASE_URL: it can point at production Supabase, and the
# test runner creates/drops a database on whatever server it's given. Tests get
# their own local, disposable Postgres (docker-compose's `db` by default) and
# refuse to start against anything else. Deliberately no override flag.
DATABASES = {
    "default": env.db(  # noqa: F405
        "TEST_DATABASE_URL",
        default="postgresql://mindcare:mindcare@localhost:5432/mindcare",
    )
}
_LOCAL_TEST_DB_HOSTS = {"localhost", "127.0.0.1", "::1"}
if (DATABASES["default"].get("HOST") or "localhost") not in _LOCAL_TEST_DB_HOSTS:
    raise ImproperlyConfigured(
        "Tests must run against a local, disposable Postgres "
        f"(host one of {sorted(_LOCAL_TEST_DB_HOSTS)}). "
        "Set TEST_DATABASE_URL to a localhost database, e.g. "
        "`docker compose up -d db` in MindCare Backend/."
    )

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Use LocMemCache for tests to keep them fast and isolated from the real
# Redis instance used in dev/prod (see base.py's CACHES for the rationale).
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}
