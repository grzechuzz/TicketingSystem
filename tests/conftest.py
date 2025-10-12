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
    def __init__(
        self,
        *,
        scope: str,
        action: str,
        object_type: str | None = None,
        object_id: int | None = None,
        organizer_id: int | None = None,
        event_id: int | None = None,
        order_id: int | None = None,
        payment_id: int | None = None,
        invoice_id: int | None = None,
        meta: dict | None = None,
        **_ignored
    ):
        self.scope = scope
        self.action = action
        self.object_type = object_type
        self.object_id = object_id
        self.organizer_id = organizer_id
        self.event_id = event_id
        self.order_id = order_id
        self.payment_id = payment_id
        self.invoice_id = invoice_id
        self.meta = dict(meta or {})
        self.entered = False
        self.exited = False
        self.exit_args = None

    async def __aenter__(self):
        self.entered = True
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self.exited = True
        self.exit_args = (exc_type, exc, tb)
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
