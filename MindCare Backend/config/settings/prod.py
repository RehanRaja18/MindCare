"""Production settings (Render deployment)."""

from .base import *  # noqa: F401,F403

DEBUG = False

SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# HSTS: one day first; raise to one year (31536000) after a week without problems
# (docs/decisions.md, 2026-10-10). No includeSubDomains: the host is a subdomain
# of onrender.com, which this app doesn't control.
SECURE_HSTS_SECONDS = 86400

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")  # noqa: F405

# Pinned explicitly so production only ever allows the real web origin, even if
# base.py's list changes later, plus whatever CORS_EXTRA_ALLOWED_ORIGINS adds on
# Render (unset by default).
CORS_ALLOWED_ORIGINS = [
    "https://mind-care-web-seven.vercel.app",
    *CORS_EXTRA_ALLOWED_ORIGINS,  # noqa: F405
]
