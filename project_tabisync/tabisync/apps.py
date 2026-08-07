from django.apps import AppConfig


class TabisyncConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tabisync'

    def ready(self):
        from .concierge_agent import checks  # noqa: F401
