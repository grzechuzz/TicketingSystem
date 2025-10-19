import pytest
import time_machine
from datetime import datetime, timezone, timedelta, date
from sqlalchemy.exc import IntegrityError
from decimal import Decimal
from app.services import booking_service
from app.domain.exceptions import NotFound, Conflict, Unauthorized, InvalidInput


@pytest.mark.asyncio
@pytest.mark.parametrize("exception", [NotFound, Unauthorized])
async def test_reserve_ticket_when_prechecks_fail_raise_errors(mocker, exception):
    mocker.patch(
        "app.services.booking_service._require_event_on_sale_status",
        new=mocker.AsyncMock(side_effect=exception)
    )
    ett_spy = mocker.patch("app.services.booking_service._load_ett_for_event", new=mocker.AsyncMock())
    db = mocker.Mock()
    user = mocker.Mock()

    with pytest.raises(exception):
        await booking_service.reserve_ticket(db, user, event_id=1, event_ticket_type_id=2, seat_id=None)

    ett_spy.assert_not_awaited()


@time_machine.travel("2025-01-01 12:00:00", tick=False)
@pytest.mark.asyncio
async def test_reserve_ticket_when_order_in_awaiting_payment_status_raises_conflict(mocker):
    mocker.patch("app.services.booking_service._require_event_on_sale_status", new=mocker.AsyncMock())
    ett_spy = mocker.patch("app.services.booking_service._load_ett_for_event", new=mocker.AsyncMock())
    order = mocker.Mock()
    order.reserved_until = datetime.now(timezone.utc) + timedelta(minutes=5)
    db = mocker.Mock()
    db.scalar = mocker.AsyncMock(return_value=order)
    user = mocker.Mock()

    with pytest.raises(Conflict):
        await booking_service.reserve_ticket(db, user, event_id=1, event_ticket_type_id=2, seat_id=None)

    ett_spy.assert_not_awaited()


@time_machine.travel("2025-01-01 12:00:00", tick=False)
@pytest.mark.asyncio
@pytest.mark.parametrize("is_ga, seat_id, message", [
    (True, 1, "GA sector shouldn't include seat"),
    (False, None, "Seat is required for this sector")
])
async def test_reserve_ticket_when_ticket_type_does_not_match_event_raises_invalid_input(mocker, is_ga, seat_id, message):
    sector = mocker.Mock()
    sector.is_ga = is_ga
    event_sector = mocker.Mock()
    event_sector.sector = sector
    ett = mocker.Mock()
    ett.event_sector = event_sector
    mocker.patch("app.services.booking_service._require_event_on_sale_status", new=mocker.AsyncMock())
    ett_spy = mocker.patch("app.services.booking_service._load_ett_for_event", new=mocker.AsyncMock(return_value=ett))
    db = mocker.Mock()
    db.scalar = mocker.AsyncMock(return_value=None)
    db.execute = mocker.AsyncMock()
    user = mocker.Mock()

    with pytest.raises(InvalidInput) as e:
        await booking_service.reserve_ticket(db, user, 1, 2, seat_id)

    assert str(e.value) == message
    ett_spy.assert_awaited_once()
    db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_reserve_ticket_inserts_and_fetches_pending_order_but_exceeds_ticket_limit_raises_invalid_input(mocker):
    event = mocker.Mock()
    mocker.patch(
        "app.services.booking_service._require_event_on_sale_status",
        new=mocker.AsyncMock(return_value=event),
    )
    sector = mocker.Mock(is_ga=True)
    event_sector = mocker.Mock(sector=sector, id=10)
    ett = mocker.Mock(
        event_sector=event_sector,
        event_sector_id=10,
        price_net=Decimal("5.00"),
        vat_rate=Decimal("1.23"),
        ticket_type=mocker.Mock(name="Regular"),
    )
    mocker.patch(
        "app.services.booking_service._load_ett_for_event",
        new=mocker.AsyncMock(return_value=ett),
    )
    db = mocker.Mock()
    db.execute = mocker.AsyncMock()
    db.flush = mocker.AsyncMock()
    db.scalar = mocker.AsyncMock(return_value=None)
    order = mocker.Mock(id=1, total_price=Decimal("299"))
    req_order = mocker.patch(
        "app.services.booking_service._require_order",
        new=mocker.AsyncMock(return_value=order),
    )
    mocker.patch(
        "app.services.booking_service._ensure_user_ticket_limit_not_exceeded",
        new=mocker.AsyncMock(side_effect=InvalidInput("Ticket limit for this event exceeded")),
    )
    ga_decrement_spy = mocker.patch(
        "app.services.booking_service._ga_decrement",
        new=mocker.AsyncMock(),
    )
    user = mocker.Mock(id=123)

    with pytest.raises(InvalidInput) as e:
        await booking_service.reserve_ticket(db, user, 1, 1)

    assert isinstance(e.value, InvalidInput)
    req_order.assert_awaited_once()
    ga_decrement_spy.assert_not_awaited()
    db.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_reserve_ticket_ga_no_tickets_left_raises_conflict(mocker):
    mocker.patch("app.services.booking_service._require_event_on_sale_status",
                 new=mocker.AsyncMock(return_value=mocker.Mock()))
    sector = mocker.Mock(is_ga=True)
    event_sector = mocker.Mock(sector=sector, id=10)
    ett = mocker.Mock(event_sector=event_sector, event_sector_id=10,
                      price_net=Decimal("5.00"), vat_rate=Decimal("1.23"),
                      ticket_type=mocker.Mock(name="Regular"))
    mocker.patch("app.services.booking_service._load_ett_for_event",
                 new=mocker.AsyncMock(return_value=ett))

    db = mocker.Mock()
    db.execute = mocker.AsyncMock()
    db.flush = mocker.AsyncMock()
    db.scalar = mocker.AsyncMock(return_value=None)

    mocker.patch("app.services.booking_service._require_order",
                 new=mocker.AsyncMock(return_value=mocker.Mock(id=1, total_price=Decimal("299"))))
    mocker.patch("app.services.booking_service._ensure_user_ticket_limit_not_exceeded",
                 new=mocker.AsyncMock())

    ga_decrement = mocker.patch("app.services.booking_service._ga_decrement",
                                new=mocker.AsyncMock(side_effect=Conflict("No tickets left")))

    user = mocker.Mock(id=123)

    with pytest.raises(Conflict) as e:
        await booking_service.reserve_ticket(db, user, 1, 1)

    assert str(e.value) == "No tickets left"
    ga_decrement.assert_awaited_once_with(db, event_sector.id)
    db.add.assert_not_called()
    db.flush.assert_not_awaited()


@time_machine.travel("2025-01-01 12:00:00", tick=False)
@pytest.mark.asyncio
async def test_reserve_ticket_ga_successful_reservation(mocker):
    event = mocker.Mock(id=1)
    mocker.patch("app.services.booking_service._require_event_on_sale_status",
                 new=mocker.AsyncMock(return_value=event))

    sector = mocker.Mock(is_ga=True)
    event_sector = mocker.Mock(sector=sector, id=10)
    ett = mocker.Mock(event_sector=event_sector, event_sector_id=10,
                      price_net=Decimal("5.00"), vat_rate=Decimal("1.23"),
                      ticket_type=mocker.Mock(name="Regular"))
    mocker.patch("app.services.booking_service._load_ett_for_event",
                 new=mocker.AsyncMock(return_value=ett))

    db = mocker.Mock()
    db.execute = mocker.AsyncMock()
    db.flush = mocker.AsyncMock()
    db.scalar = mocker.AsyncMock(return_value=None)

    order = mocker.Mock(id=1, total_price=Decimal("50.00"),
                        reserved_until=datetime.now(timezone.utc))
    initial_reserved = order.reserved_until
    mocker.patch("app.services.booking_service._require_order",
                 new=mocker.AsyncMock(return_value=order))
    mocker.patch("app.services.booking_service._ensure_user_ticket_limit_not_exceeded",
                 new=mocker.AsyncMock())
    ga_decrement = mocker.patch("app.services.booking_service._ga_decrement",
                                new=mocker.AsyncMock())

    user = mocker.Mock(id=10)

    returned_order, ti = await booking_service.reserve_ticket(db, user, 1, 1)

    assert returned_order is order
    assert returned_order.reserved_until == initial_reserved + timedelta(minutes=15)
    assert order.total_price == Decimal("56.15")
    db.add.assert_called_once()
    assert ti.order_id == order.id
    assert ti.price_gross_snapshot == Decimal("6.15")
    assert ti.seat_id is None
    assert ti.event_ticket_type_id == 1
    assert ti.event_id == 1
    ga_decrement.assert_awaited_once()


@pytest.mark.asyncio
async def test_reserve_ticket_seated_selected_seat_not_available_raises_conflict(mocker):
    mocker.patch("app.services.booking_service._require_event_on_sale_status",
                 new=mocker.AsyncMock(return_value=mocker.Mock()))

    sector = mocker.Mock(is_ga=False)
    event_sector = mocker.Mock(sector=sector, sector_id=99)
    ett = mocker.Mock(event_sector=event_sector,
                      price_net=Decimal("5.00"), vat_rate=Decimal("1.23"),
                      ticket_type=mocker.Mock(name="Regular"))
    mocker.patch("app.services.booking_service._load_ett_for_event",
                 new=mocker.AsyncMock(return_value=ett))

    db = mocker.Mock()
    db.execute = mocker.AsyncMock()
    db.flush = mocker.AsyncMock(side_effect=IntegrityError("dup", None, None))
    db.scalar = mocker.AsyncMock(return_value=None)

    mocker.patch("app.services.booking_service._require_order",
                 new=mocker.AsyncMock(return_value=mocker.Mock(id=1, total_price=Decimal("50.00"))))
    mocker.patch("app.services.booking_service._ensure_user_ticket_limit_not_exceeded",
                 new=mocker.AsyncMock())
    seat_check = mocker.patch("app.services.booking_service._require_seat_in_sector",
                              new=mocker.AsyncMock())

    user = mocker.Mock(id=7)
    seat_id = 555

    with pytest.raises(Conflict) as e:
        await booking_service.reserve_ticket(db, user, 1, 1, seat_id)

    assert str(e.value) == "Selected seat is not available"
    seat_check.assert_awaited_once_with(db, seat_id, event_sector.sector_id)
    db.add.assert_called_once()
    db.flush.assert_awaited_once()


@time_machine.travel("2025-01-01 12:00:00", tick=False)
@pytest.mark.asyncio
async def test_reserve_ticket_seated_successful_reservation(mocker):
    event = mocker.Mock()
    event.id = 1
    mocker.patch("app.services.booking_service._require_event_on_sale_status", new=mocker.AsyncMock(return_value=event))

    sector = mocker.Mock()
    sector.is_ga = False
    event_sector = mocker.Mock()
    event_sector.sector = sector
    event_sector.sector_id = 99

    ett = mocker.Mock(
        event_sector=event_sector,
        price_net=Decimal("5.00"),
        vat_rate=Decimal("1.23"),
        ticket_type=mocker.Mock()
    )
    ett.ticket_type.name = "Regular"
    mocker.patch("app.services.booking_service._load_ett_for_event", new=mocker.AsyncMock(return_value=ett))

    db = mocker.Mock()
    db.execute = mocker.AsyncMock()
    db.add = mocker.Mock()
    db.flush = mocker.AsyncMock()
    db.scalar = mocker.AsyncMock(return_value=None)

    order = mocker.Mock(id=1, total_price=Decimal("50.00"), reserved_until=datetime.now(timezone.utc))
    initial_reserved = order.reserved_until
    mocker.patch("app.services.booking_service._require_order", new=mocker.AsyncMock(return_value=order))
    mocker.patch("app.services.booking_service._ensure_user_ticket_limit_not_exceeded", new=mocker.AsyncMock())

    ga_decrement_spy = mocker.patch("app.services.booking_service._ga_decrement", new=mocker.AsyncMock())
    seat_check_spy = mocker.patch("app.services.booking_service._require_seat_in_sector", new=mocker.AsyncMock())

    user = mocker.Mock()
    seat_id = 777

    returned_order, returned_ticket_instance = await booking_service.reserve_ticket(db, user, 1, 1, seat_id)

    assert returned_order is order
    assert returned_order.reserved_until == initial_reserved + timedelta(minutes=15)
    assert order.total_price == Decimal("56.15")

    db.add.assert_called_once()
    db.flush.assert_awaited_once()

    assert returned_ticket_instance.order_id == order.id
    assert returned_ticket_instance.event_id == 1
    assert returned_ticket_instance.event_ticket_type_id == 1
    assert returned_ticket_instance.seat_id == seat_id
    assert returned_ticket_instance.price_gross_snapshot == Decimal("6.15")

    seat_check_spy.assert_awaited_once_with(db, seat_id, event_sector.sector_id)
    ga_decrement_spy.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("exception", [NotFound("x"), InvalidInput("y")])
async def test_reserve_ticket_seated_seat_validation_errors_propagate(mocker, exception):
    mocker.patch("app.services.booking_service._require_event_on_sale_status",
                 new=mocker.AsyncMock(return_value=mocker.Mock()))
    sector = mocker.Mock(is_ga=False)
    event_sector = mocker.Mock(sector=sector, sector_id=99)
    ett = mocker.Mock(event_sector=event_sector,
                      price_net=Decimal("5.00"), vat_rate=Decimal("1.23"),
                      ticket_type=mocker.Mock(name="Regular"))
    mocker.patch("app.services.booking_service._load_ett_for_event",
                 new=mocker.AsyncMock(return_value=ett))

    db = mocker.Mock()
    db.execute = mocker.AsyncMock()
    db.add = mocker.Mock()
    db.flush = mocker.AsyncMock()
    db.scalar = mocker.AsyncMock(return_value=None)

    mocker.patch("app.services.booking_service._require_order",
                 new=mocker.AsyncMock(return_value=mocker.Mock(id=1, total_price=Decimal("0"))))
    mocker.patch("app.services.booking_service._ensure_user_ticket_limit_not_exceeded",
                 new=mocker.AsyncMock())

    seat_check = mocker.patch("app.services.booking_service._require_seat_in_sector",
                              new=mocker.AsyncMock(side_effect=exception))
    ga_decrement = mocker.patch("app.services.booking_service._ga_decrement",
                                new=mocker.AsyncMock())

    user = mocker.Mock(id=5)

    with pytest.raises(type(exception)):
        await booking_service.reserve_ticket(db, user, 1, 1, 777)

    seat_check.assert_awaited_once_with(db, 777, event_sector.sector_id)
    db.add.assert_not_called()
    db.flush.assert_not_awaited()
    ga_decrement.assert_not_awaited()


@pytest.mark.asyncio
async def test_remove_ticket_instance_ticket_instance_not_found_raises_notfound(mocker):
    db = mocker.Mock()
    db.scalar = mocker.AsyncMock(return_value=None)
    user = mocker.Mock()
    req_order = mocker.patch("app.services.booking_service._require_order", new=mocker.AsyncMock())

    with pytest.raises(NotFound) as e:
        await booking_service.remove_ticket_instance(db, user, 1)

    assert str(e.value) == "Ticket instance not found"
    req_order.assert_not_awaited()


@pytest.mark.asyncio
async def test_remove_ticket_instance_order_not_found_raises_notfound(mocker):
    ti = mocker.Mock()
    db = mocker.Mock()
    db.scalar = mocker.AsyncMock(return_value=ti)
    user = mocker.Mock()
    req_order = mocker.patch(
        "app.services.booking_service._require_order",
        new=mocker.AsyncMock(side_effect=NotFound)
    )

    with pytest.raises(NotFound) as e:
        await booking_service.remove_ticket_instance(db, user, 1)

    assert isinstance(e.value, NotFound)
    assert db.scalar.call_count == 1
    req_order.assert_awaited_once()


@pytest.mark.asyncio
async def test_remove_ticket_instance_when_ticket_instance_not_found_in_order_raises_notfound(mocker):
    ti = mocker.Mock(order_id=1)
    db = mocker.Mock()
    db.scalar = mocker.AsyncMock(return_value=ti)
    user = mocker.Mock()
    order = mocker.AsyncMock(id=2)
    req_order = mocker.patch("app.services.booking_service._require_order", new=order)

    with pytest.raises(NotFound) as e:
        await booking_service.remove_ticket_instance(db, user, 1)

    assert isinstance(e.value, NotFound)
    assert db.scalar.call_count == 1
    req_order.assert_awaited_once()


@pytest.mark.parametrize("is_ga", [True, False])
@pytest.mark.asyncio
async def test_remove_ticket_instance_depending_sector_is_ga(mocker, is_ga):
    db = mocker.Mock()
    db.delete = mocker.AsyncMock()
    db.flush = mocker.AsyncMock()
    ti = mocker.Mock(order_id=1, price_gross_snapshot=10)
    sector = mocker.Mock(is_ga=is_ga)
    event_sector = mocker.Mock(sector=sector)
    ett = mocker.Mock(event_sector=event_sector, event_sector_id=1)
    db.scalar = mocker.AsyncMock(side_effect=[ti, ett])
    order = mocker.Mock(id=1)
    req_order = mocker.patch("app.services.booking_service._require_order", new=mocker.AsyncMock(return_value=order))
    ga_increment = mocker.patch("app.services.booking_service._ga_increment", new=mocker.AsyncMock())
    bump_total = mocker.patch("app.services.booking_service._bump_total", new=mocker.Mock())
    user = mocker.Mock()

    await booking_service.remove_ticket_instance(db, user, 1)

    if is_ga:
        ga_increment.assert_awaited_once_with(db, ett.event_sector_id, 1)
    else:
        ga_increment.assert_not_awaited()

    bump_total.assert_called_once_with(order, -ti.price_gross_snapshot)
    assert db.scalar.call_count == 2
    req_order.assert_awaited_once()
    db.delete.assert_awaited_once_with(ti)
    db.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_upsert_ticket_holder_when_ticket_instance_not_found_raises_404(mocker):
    db = mocker.Mock()
    db.scalar = mocker.AsyncMock(return_value=None)
    schema = mocker.Mock()
    schema.model_dump = mocker.Mock(return_value={})
    user = mocker.Mock()

    with pytest.raises(NotFound) as e:
        await booking_service.upsert_ticket_holder(db, 1, schema, user)

    assert str(e.value) == "Ticket instance not found in your order"
    db.scalar.assert_awaited_once()


@pytest.mark.asyncio
async def test_upsert_ticket_holder_when_holder_is_not_required_raises_400(mocker):
    db = mocker.Mock()
    db.scalar = mocker.AsyncMock(side_effect=[mocker.AsyncMock(), False])
    db.flush = mocker.AsyncMock()
    schema = mocker.Mock()
    schema.model_dump = mocker.Mock(return_value={})
    user = mocker.Mock()

    with pytest.raises(InvalidInput) as e:
        await booking_service.upsert_ticket_holder(db, 1, schema, user)

    assert str(e.value) == "Holder data not required for this event"
    assert db.scalar.call_count == 2
    db.flush.assert_not_awaited()

@pytest.mark.parametrize(("ticket_holder_exi", "db_add_exec"), [
    (True, 0),
    (False, 1)
])
@pytest.mark.asyncio
async def test_upsert_ticket_holder_depending_on_whether_holder_already_exists(mocker, ticket_holder_exi, db_add_exec):
    ti = mocker.AsyncMock(ticket_holder=mocker.Mock() if ticket_holder_exi else None, order_id=1, event_id=1)
    db = mocker.Mock()
    db.scalar = mocker.AsyncMock(side_effect=[ti, True])
    db.add = mocker.Mock()
    db.flush = mocker.AsyncMock()
    schema = mocker.Mock(
        first_name='Karl', last_name='Sand', birth_date=date(1999, 1, 1), identification_number="99183940231"
    )
    schema.model_dump = mocker.Mock(
        return_value={
            "first_name": 'Karl',
            "last_name": 'Sand',
            "birth_date": date(1999, 1, 1),
            "identification_number": "99183940231"
        }
    )
    user = mocker.Mock()

    await booking_service.upsert_ticket_holder(db, 1, schema, user)

    assert db.add.call_count == db_add_exec
    assert db.scalar.call_count == 2
    db.flush.assert_awaited_once()

@pytest.mark.asyncio
async def test_set_invoice_requested(mocker):
    order = mocker.Mock(id=1)
    mocker.patch("app.services.booking_service._require_order", new=mocker.AsyncMock(return_value=order))
    db = mocker.Mock()
    db.flush = mocker.AsyncMock()
    schema = mocker.Mock(invoice_requested=True)
    user = mocker.Mock()

    await booking_service.set_invoice_requested(db, schema, user)

    assert order.invoice_requested is True
    db.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_upsert_invoice_when_invoice_not_requested_raises_400(mocker):
    order = mocker.Mock(invoice_requested=False)
    mocker.patch("app.services.booking_service._require_order", new=mocker.AsyncMock(return_value=order))
    schema = mocker.Mock()
    schema.model_dump = mocker.Mock(return_value={})
    db = mocker.Mock()
    db.flush = mocker.AsyncMock()
    user = mocker.Mock()

    with pytest.raises(InvalidInput) as e:
        await booking_service.upsert_invoice(db, schema, user)

    assert str(e.value) == "Invoice not requested for this order"
    db.flush.assert_not_awaited()


@pytest.mark.parametrize(("invoice_exi", "db_add_exec"), [
    (True, 0),
    (False, 1)
])
@pytest.mark.asyncio
async def test_upsert_invoice_depending_on_whether_invoice_already_exists(mocker, invoice_exi, db_add_exec):
    invoice = mocker.Mock()
    order = mocker.Mock(id=1, invoice_requested=True, invoice=invoice if invoice_exi else None)
    mocker.patch("app.services.booking_service._require_order", new=mocker.AsyncMock(return_value=order))
    schema = mocker.Mock()
    schema.model_dump = mocker.Mock(return_value={})
    db = mocker.Mock()
    db.flush = mocker.AsyncMock()
    db.add = mocker.Mock()
    user = mocker.Mock()

    await booking_service.upsert_invoice(db, schema, user)

    assert db.add.call_count == db_add_exec
    db.flush.assert_awaited_once()


@time_machine.travel("2025-01-01T12:00:00Z", tick=False)
@pytest.mark.asyncio
async def test_process_order_expired_reservation_raises_409(mocker):
    user = mocker.Mock(id=1)
    order = mocker.AsyncMock(reserved_until=datetime(2025, 1, 1, 11, 0, 0, tzinfo=timezone.utc))
    mocker.patch("app.services.booking_service._require_order", new=mocker.AsyncMock(return_value=order))
    db = mocker.Mock()
    require_cart_spy = mocker.patch(
        "app.services.booking_service._require_cart_has_items", new=mocker.AsyncMock(return_value=True)
    )

    with pytest.raises(Conflict) as e:
        await booking_service.process_order(db, user)

    assert str(e.value) == "Reservation expired"
    require_cart_spy.assert_not_awaited()
