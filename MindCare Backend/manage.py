#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""

import os
import sys


def main():
    """Run administrative tasks."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # Force (not setdefault) the guarded test settings: the dev settings read
        # DATABASE_URL from .env, which may point at production, and Django's test
        # runner would create/drop a test database on that server.
        os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings.test"
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
