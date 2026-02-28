"""Route definitions and API Gateway path-to-handler mapping."""

from cdss.api.handlers import (
    engagement,
    patient,
    resource,
    scheduling,
    surgery,
    supervisor,
)

# Path -> (handler_module, optional_integration)
ROUTES = {
    "/cdss/supervisor": supervisor,
    "/cdss/patient": patient,
    "/cdss/surgery": surgery,
    "/cdss/resource": resource,
    "/cdss/scheduling": scheduling,
    "/cdss/engagement": engagement,
}
