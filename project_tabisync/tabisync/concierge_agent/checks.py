from django.core.checks import Error, register

from .errors import ConciergeDefinitionError
from .registry import build_registry


@register()
def check_concierge_agent_definitions(app_configs, **kwargs):
    try:
        build_registry()
    except ConciergeDefinitionError as exc:
        return [Error(str(exc), id="tabisync.concierge_agent.E001")]
    return []
