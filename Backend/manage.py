#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'weather_project.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc

    # Auto-migrate if starting the server
    if len(sys.argv) > 1 and sys.argv[1] == 'runserver':
        try:
            from django.core.management import call_command
            import django
            django.setup()
            print("Auto-generating and applying database migrations...")
            call_command('makemigrations', 'weather', interactive=False)
            call_command('migrate', interactive=False)
        except Exception as e:
            print(f"Warning: Auto-migration skipped or failed: {e}")

    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
