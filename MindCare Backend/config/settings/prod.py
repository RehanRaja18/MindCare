"""Production settings (Render deployment)."""

from .base import *  # noqa: F401,F403

DEBUG = False

SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")  # noqa: F405

# Pinned explicitly so production only ever allows the real web origin, even if
# base.py's list changes later.
CORS_ALLOWED_ORIGINS = [
    "https://mind-care-web-seven.vercel.app",
]
