from django.apps import AppConfig


class SkareConfig(AppConfig):
    name = 'SkaRe'

    def ready(self):
        from . import checks  # noqa: F401  (registers the system checks)
