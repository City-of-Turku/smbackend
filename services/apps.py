from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ServicesConfig(AppConfig):
    name = "services"
    verbose_name = _("Services")

    def ready(self):
        # register signals
        from services import signals  # noqa: F401
