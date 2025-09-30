import pytest
import importlib

SERVICE_MODULES = [
    "app.services.address_service",
    "app.services.auth_service",
    "app.services.booking_service",
    "app.services.event_sectors_service",
    "app.services.event_service",
    "app.services.event_ticket_type_service",
    "app.services.organizer_service",
    "app.services.payment_service",
    "app.services.ticket_type_service",
    "app.services.venue_service"
]

class _StubSpan:
    def __init__(self, *a, **k):
        self.kwargs = k
        self.request = a[0] if a else k.get("request")
        self.scope = k.get('scope')
        self.action = k.get('action')
        self.user = k.get('user')
        self.object_type = k.get('object_type')
        self.object_id = k.get('object_id')
        self.organizer_id = k.get('organizer_id')
        self.event_id = k.get('event_id')
        self.order_id = k.get('order_id')
        self.payment_id = k.get('payment_id')
        self.invoice_id = k.get('invoice_id')
        self.meta = dict(k.get('meta', {}))

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


@pytest.fixture(autouse=True)
def auditspan_stub(mocker, request):
    instances = []

    def factory(*a, **k):
        s = _StubSpan(*a, **k)
        instances.append(s)
        return s

    for mod in SERVICE_MODULES:
        importlib.import_module(mod)
        mocker.patch(f"{mod}.AuditSpan", side_effect=factory)

    return instances
