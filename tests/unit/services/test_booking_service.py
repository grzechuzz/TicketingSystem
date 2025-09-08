import pytest
import time_machine
from datetime import datetime, timezone, timedelta
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status
from decimal import Decimal
from app.services import booking_service


@pytest.mark.asyncio
@pytest.mark.parametrize("exception", [
    HTTPException(status_code=status.HTTP_404_NOT_FOUND),
    HTTPException(status_code=status.HTTP_400_BAD_REQUEST)
])
async def test_reserve_ticket_when_prechecks_fail_raise_errors(mocker, exception):
    mocker.patch(
        "app.services.booking_service._require_event_on_sale_status",
        new=mocker.AsyncMock(side_effect=exception)
    )
    ett_spy = mocker.patch("app.services.booking_service._load_ett_for_event", new=mocker.AsyncMock())
    db = mocker.Mock()
    user = mocker.Mock()
    user.id = 123

    with pytest.raises(HTTPException) as e:
        await booking_service.reserve_ticket(db, user, event_id=1, event_ticket_type_id=2, seat_id=None)

    assert e.value.status_code == exception.status_code
    ett_spy.assert_not_awaited()


@time_machine.travel("2025-01-01 12:00:00", tick=False)
@pytest.mark.asyncio
async def test_reserve_ticket_when_order_in_awaiting_payment_status_raises_409(mocker):
    mocker.patch("app.services.booking_service._require_event_on_sale_status", new=mocker.AsyncMock())
    ett_spy = mocker.patch("app.services.booking_service._load_ett_for_event", new=mocker.AsyncMock())
    order = mocker.Mock()
    order.reserved_until = datetime.now(timezone.utc) + timedelta(minutes=5)
    db = mocker.Mock()
    db.scalar = mocker.AsyncMock(return_value=order)
    user = mocker.Mock()

    with pytest.raises(HTTPException) as e:
        await booking_service.reserve_ticket(db, user, event_id=1, event_ticket_type_id=2, seat_id=None)

    assert e.value.status_code == status.HTTP_409_CONFLICT
    ett_spy.assert_not_awaited()


@time_machine.travel("2025-01-01 12:00:00", tick=False)
@pytest.mark.asyncio
@pytest.mark.parametrize("is_ga, seat_id, message", [
    (True, 1, "GA sector shouldn't include seat"),
    (False, None, "Seat is required for this sector")
])
async def test_reserve_ticket_when_ticket_type_does_not_match_event_raises_400(mocker, is_ga, seat_id, message):
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

    with pytest.raises(HTTPException) as e:
        await booking_service.reserve_ticket(db, user, 1, 2, seat_id)

    assert e.value.status_code == status.HTTP_400_BAD_REQUEST
    assert e.value.detail == message
    ett_spy.assert_awaited_once()
    db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_reserve_ticket_inserts_and_fetches_pending_order_but_exceeds_ticket_limit_raises_400(mocker):
    event = mocker.Mock()
    mocker.patch("app.services.booking_service._require_event_on_sale_status", new=mocker.AsyncMock(return_value=event))
    sector = mocker.Mock()
    sector.is_ga = True
    event_sector = mocker.Mock()
    event_sector.sector = sector
    event_sector.id = 10
    ett = mocker.Mock(
        event_sector=event_sector,
        event_sector_id=10,
        price_net=Decimal("5.00"),
        vat_rate=Decimal("1.23"),
        ticket_type=mocker.Mock()
    )
    ett.ticket_type.name = "Regular"
    mocker.patch("app.services.booking_service._load_ett_for_event", new=mocker.AsyncMock(return_value=ett))
    db = mocker.Mock()
    db.execute = mocker.AsyncMock()
    db.flush = mocker.AsyncMock()
    db.scalar = mocker.AsyncMock(return_value=None)
    order = mocker.Mock(id=1, total_price=299)
    req_order = mocker.patch("app.services.booking_service._require_order", new=mocker.AsyncMock(return_value=order))
    mocker.patch(
        "app.services.booking_service._ensure_user_ticket_limit_not_exceeded",
        new=mocker.AsyncMock(side_effect=HTTPException(status_code=status.HTTP_400_BAD_REQUEST))
    )
    ga_decrement_spy = mocker.patch("app.services.booking_service._ga_decrement", new=mocker.AsyncMock())
    user = mocker.Mock()

    with pytest.raises(HTTPException) as e:
        await booking_service.reserve_ticket(db, user, 1, 1, None)

    assert e.value.status_code == status.HTTP_400_BAD_REQUEST
    req_order.assert_awaited_once()
    ga_decrement_spy.assert_not_awaited()


@pytest.mark.asyncio
async def test_reserve_ticket_ga_no_tickets_left_raises_409(mocker):
    event = mocker.Mock()
    mocker.patch("app.services.booking_service._require_event_on_sale_status", new=mocker.AsyncMock(return_value=event))
    sector = mocker.Mock()
    sector.is_ga = True
    event_sector = mocker.Mock()
    event_sector.sector = sector
    event_sector.id = 10
    ett = mocker.Mock(
        event_sector=event_sector,
        event_sector_id=10,
        price_net=Decimal("5.00"),
        vat_rate=Decimal("1.23"),
        ticket_type=mocker.Mock()
    )
    ett.ticket_type.name = "Regular"
    mocker.patch("app.services.booking_service._load_ett_for_event", new=mocker.AsyncMock(return_value=ett))
    db = mocker.Mock()
    db.execute = mocker.AsyncMock()
    db.flush = mocker.AsyncMock()
    db.add = mocker.Mock()
    db.scalar = mocker.AsyncMock(return_value=None)
    order = mocker.Mock(id=1, total_price=299)
    mocker.patch("app.services.booking_service._require_order", new=mocker.AsyncMock(return_value=order))
    mocker.patch("app.services.booking_service._ensure_user_ticket_limit_not_exceeded", new=mocker.AsyncMock())
    ga_decrement = mocker.patch(
        "app.services.booking_service._ga_decrement",
        new=mocker.AsyncMock(side_effect=HTTPException(status_code=status.HTTP_409_CONFLICT))
    )
    bump_total_spy = mocker.patch("app.services.booking_service._bump_total", new=mocker.Mock())
    user = mocker.Mock()

    with pytest.raises(HTTPException) as e:
        await booking_service.reserve_ticket(db, user, 1, 1, None)

    assert e.value.status_code == status.HTTP_409_CONFLICT
    ga_decrement.assert_awaited_once_with(db, event_sector.id)
    db.add.assert_not_called()
    db.flush.assert_not_awaited()
    bump_total_spy.assert_not_called()


@time_machine.travel("2025-01-01 12:00:00", tick=False)
@pytest.mark.asyncio
async def test_reserve_ticket_ga_successful_reservation(mocker):
    event = mocker.Mock()
    event.id = 1
    mocker.patch("app.services.booking_service._require_event_on_sale_status", new=mocker.AsyncMock(return_value=event))
    sector = mocker.Mock()
    sector.is_ga = True
    event_sector = mocker.Mock()
    event_sector.sector = sector
    event_sector.id = 10
    ett = mocker.Mock(
        event_sector=event_sector,
        event_sector_id=10,
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
    seat_check_spy = mocker.patch(
        "app.services.booking_service._require_seat_in_sector",
        new=mocker.AsyncMock(),
    )
    user = mocker.Mock()
    user.id = 10

    returned_order, returned_ticket_instance = await booking_service.reserve_ticket(db, user, 1, 1, None)

    assert returned_order is order
    assert returned_order.reserved_until == initial_reserved + timedelta(minutes=15)
    assert order.total_price == Decimal("56.15")
    db.add.assert_called_once()
    assert returned_ticket_instance.order_id == order.id
    assert returned_ticket_instance.price_gross_snapshot == Decimal("6.15")  # 5 * 1.23 = 6.15
    assert returned_ticket_instance.seat_id is None
    assert returned_ticket_instance.event_ticket_type_id == 1
    assert returned_ticket_instance.event_id == 1
    seat_check_spy.assert_not_awaited()
    ga_decrement_spy.assert_awaited_once()


@pytest.mark.asyncio
async def test_reserve_ticket_seated_selected_seat_not_available_raises_409(mocker):
    event = mocker.Mock()
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
    db.flush = mocker.AsyncMock(side_effect=IntegrityError("dup", None, None))
    db.scalar = mocker.AsyncMock(return_value=None)

    order = mocker.Mock(id=1, total_price=Decimal("50.00"))
    mocker.patch("app.services.booking_service._require_order", new=mocker.AsyncMock(return_value=order))
    mocker.patch("app.services.booking_service._ensure_user_ticket_limit_not_exceeded", new=mocker.AsyncMock())

    ga_decrement_spy = mocker.patch("app.services.booking_service._ga_decrement", new=mocker.AsyncMock())
    seat_check_spy = mocker.patch("app.services.booking_service._require_seat_in_sector", new=mocker.AsyncMock())

    user = mocker.Mock()
    seat_id = 555

    with pytest.raises(HTTPException) as e:
        await booking_service.reserve_ticket(db, user, 1, 1, seat_id)

    assert e.value.status_code == status.HTTP_409_CONFLICT
    assert e.value.detail == "Selected seat is not available"

    seat_check_spy.assert_awaited_once_with(db, seat_id, event_sector.sector_id)
    ga_decrement_spy.assert_not_awaited()
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
@pytest.mark.parametrize("code", [status.HTTP_404_NOT_FOUND, status.HTTP_400_BAD_REQUEST])
async def test_reserve_ticket_seated_seat_validation_errors_propagate(mocker, code):
    event = mocker.Mock()
    mocker.patch(
        "app.services.booking_service._require_event_on_sale_status",
        new=mocker.AsyncMock(return_value=event),
    )

    sector = mocker.Mock()
    sector.is_ga = False
    event_sector = mocker.Mock()
    event_sector.sector = sector
    event_sector.sector_id = 99

    ett = mocker.Mock(
        event_sector=event_sector,
        price_net=Decimal("5.00"),
        vat_rate=Decimal("1.23"),
        ticket_type=mocker.Mock(),
    )
    ett.ticket_type.name = "Regular"
    mocker.patch(
        "app.services.booking_service._load_ett_for_event",
        new=mocker.AsyncMock(return_value=ett),
    )

    db = mocker.Mock()
    db.execute = mocker.AsyncMock()
    db.add = mocker.Mock()
    db.flush = mocker.AsyncMock()
    db.scalar = mocker.AsyncMock(return_value=None)

    order = mocker.Mock(id=1, total_price=Decimal("0"))
    mocker.patch(
        "app.services.booking_service._require_order",
        new=mocker.AsyncMock(return_value=order),
    )
    mocker.patch(
        "app.services.booking_service._ensure_user_ticket_limit_not_exceeded",
        new=mocker.AsyncMock(),
    )

    seat_check = mocker.patch(
        "app.services.booking_service._require_seat_in_sector",
        new=mocker.AsyncMock(side_effect=HTTPException(status_code=code)),
    )
    ga_decrement = mocker.patch(
        "app.services.booking_service._ga_decrement",
        new=mocker.AsyncMock(),
    )

    with pytest.raises(HTTPException) as e:
        await booking_service.reserve_ticket(db, mocker.Mock(), event_id=1, event_ticket_type_id=1, seat_id=777)

    assert e.value.status_code == code
    seat_check.assert_awaited_once_with(db, 777, event_sector.sector_id)
    db.add.assert_not_called()
    db.flush.assert_not_awaited()
    ga_decrement.assert_not_awaited()
