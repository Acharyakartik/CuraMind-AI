"""
Expose the Celery app when Celery is installed.

This keeps `python manage.py runserver` working even if you haven't installed Celery yet.
"""

try:
    from .celery import app as celery_app  # type: ignore

    __all__ = ("celery_app",)
except ModuleNotFoundError:
    __all__ = ()
