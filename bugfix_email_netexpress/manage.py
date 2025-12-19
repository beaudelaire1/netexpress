#!/usr/bin/env python
import os
import sys

def main():
    # Charger dotenv UNIQUEMENT en développement
    if os.environ.get("DJANGO_ENV") == "development":
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "netexpress.settings.dev")

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise
    execute_from_command_line(sys.argv)

if __name__ == "__main__":
    main()
