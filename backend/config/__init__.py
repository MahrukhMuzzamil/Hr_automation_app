# Ensure the Celery app is loaded when Django starts so that shared_task
# decorators and the @app configuration are always available.
from .celery import app as celery_app

__all__ = ("celery_app",)
