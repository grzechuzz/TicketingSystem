import pytest
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from app.services import event_sectors_service


@pytest.mark.asyncio
async def test_get_event_sector_returns_event_sector(mocker):
    event_sector = mocker.Mock()
    mocker.patch(
        "app.services.event_sectors_service.crud.get_event_sector",
        new=mocker.AsyncMock(return_value=event_sector)
    )
    db = mocker.Mock()

    result = await event_sectors_service.get_event_sector(db, 1, 1)

    assert result is event_sector


@pytest.mark.asyncio
async def test_get_event_sector_not_found_raises_404(mocker):
    mocker.patch(
        "app.services.event_sectors_service.crud.get_event_sector",
        new=mocker.AsyncMock(return_value=None)
    )
    db = mocker.Mock()

    with pytest.raises(HTTPException) as e:
        await event_sectors_service.get_event_sector(db, 1, 1)

    assert e.value.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_list_event_sectors(mocker):
    event_sectors = [mocker.Mock(), mocker.Mock()]
    mocker.patch(
        "app.services.event_sectors_service.crud.list_event_sectors",
        new=mocker.AsyncMock(return_value=event_sectors)
    )
    db = mocker.Mock()

    result = await event_sectors_service.list_event_sectors(db, 1)

    assert result == event_sectors


@pytest.mark.asyncio
async def test_create_event_sector_venue_mismatch_raises_400(mocker):
    event = mocker.Mock(id=10, venue_id=10)
    sector = mocker.Mock(venue_id=999, is_ga=False)
    schema = mocker.Mock()
    db = mocker.Mock()
    user = mocker.Mock()
    req = mocker.Mock()
    mocker.patch("app.services.event_sectors_service.get_sector", new=mocker.AsyncMock(return_value=sector))

    with pytest.raises(HTTPException) as e:
        await event_sectors_service.create_event_sector(db, schema, event, user, req)

    assert e.value.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_create_event_sector_ga_sets_tickets_left_and_flushes(mocker):
    event = mocker.Mock(id=10, venue_id=1)
    sector = mocker.Mock(venue_id=1, is_ga=True, base_capacity=250)
    mocker.patch("app.services.event_sectors_service.get_sector", new=mocker.AsyncMock(return_value=sector))
    schema = mocker.Mock(sector_id=3)
    schema.model_dump.return_value = {"sector_id": 3}
    created = mocker.Mock()
    create_spy = mocker.patch(
        "app.services.event_sectors_service.crud.create_event_sector",
        new=mocker.AsyncMock(return_value=created)
    )
    db = mocker.Mock()
    db.flush = mocker.AsyncMock()
    user = mocker.Mock()
    req = mocker.Mock()

    result = await event_sectors_service.create_event_sector(db, schema, event, user, req)

    assert result is created
    create_spy.assert_awaited_once_with(
        db,
        {"sector_id": 3, "event_id": 10, "tickets_left": 250}
    )
    db.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_event_sector_non_ga_does_not_set_tickets_left(mocker):
    event = mocker.Mock(id=10, venue_id=1)
    sector = mocker.Mock(venue_id=1, is_ga=False, base_capacity=250)
    mocker.patch("app.services.event_sectors_service.get_sector", new=mocker.AsyncMock(return_value=sector))
    schema = mocker.Mock(sector_id=3)
    schema.model_dump.return_value = {"sector_id": 3}
    created = mocker.Mock()
    create_spy = mocker.patch(
        "app.services.event_sectors_service.crud.create_event_sector",
        new=mocker.AsyncMock(return_value=created)
    )
    db = mocker.Mock()
    db.flush = mocker.AsyncMock()
    user = mocker.Mock()
    req = mocker.Mock()

    result = await event_sectors_service.create_event_sector(db, schema, event, user, req)

    assert result is created
    create_spy.assert_awaited_once_with(
        db,
        {"sector_id": 3, "event_id": 10}
    )
    db.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_event_sector_integrity_error_maps_to_409_raise(mocker):
    event = mocker.Mock(id=10, venue_id=1)
    sector = mocker.Mock(venue_id=1, is_ga=False)
    mocker.patch("app.services.event_sectors_service.get_sector", new=mocker.AsyncMock(return_value=sector))
    schema = mocker.Mock(sector_id=3)
    schema.model_dump.return_value = {"sector_id": 3}
    mocker.patch("app.services.event_sectors_service.crud.create_event_sector", new=mocker.AsyncMock())
    db = mocker.Mock()
    db.flush = mocker.AsyncMock(side_effect=IntegrityError("dup", None, None))
    user = mocker.Mock()
    req = mocker.Mock()

    with pytest.raises(HTTPException) as e:
        await event_sectors_service.create_event_sector(db, schema, event, user, req)

    assert e.value.status_code == status.HTTP_409_CONFLICT
    assert e.value.detail == "Sector already assigned to this event"


@pytest.mark.asyncio
async def test_bulk_create_event_sectors_mixed_payload(mocker):
    event = mocker.Mock(id=10, venue_id=1)
    ga_sector = mocker.Mock(id=1, venue_id=1, is_ga=True, base_capacity=250)
    non_ga_sector = mocker.Mock(id=2, venue_id=1, is_ga=False, base_capacity=300)

    async def get_sector_side_effect(db, sector_id):
        return ga_sector if sector_id == 1 else non_ga_sector

    mocker.patch(
        "app.services.event_sectors_service.get_sector",
        new=mocker.AsyncMock(side_effect=get_sector_side_effect)
    )
    sec1 = mocker.Mock(sector_id=1)
    sec2 = mocker.Mock(sector_id=2)
    sec1.model_dump.return_value = {"sector_id": 1}
    sec2.model_dump.return_value = {"sector_id": 2}
    schema = mocker.Mock(sectors=[sec1, sec2])
    bulk_spy = mocker.patch("app.services.event_sectors_service.crud.bulk_add_event_sectors", new=mocker.AsyncMock())
    db = mocker.Mock()
    user = mocker.Mock()
    req = mocker.Mock()

    await event_sectors_service.bulk_create_event_sectors(db, schema, event, user, req)

    bulk_spy.assert_awaited_once_with(
        db,
        10,
        [
            {"sector_id": 1, "tickets_left": 250},
            {"sector_id": 2}
        ]
    )

@pytest.mark.asyncio
async def test_bulk_create_event_sectors_venue_mismatch_stops_bulk_create_raises_400(mocker):
    event = mocker.Mock(id=10, venue_id=1)
    bad_sector = mocker.Mock(venue_id=2, is_ga=False)
    good_sector = mocker.Mock(venue_id=1, is_ga=True, base_capacity=250)
    get_sector_spy = mocker.patch(
        "app.services.event_sectors_service.get_sector",
        new=mocker.AsyncMock(side_effect=[bad_sector, good_sector])
    )
    sec1 = mocker.Mock(sector_id=1)
    sec2 = mocker.Mock(sector_id=2)
    sec1.model_dump.return_value = {"sector_id": 1}
    sec2.model_dump.return_value = {"sector_id": 2}
    schema = mocker.Mock(sectors=[sec1, sec2])
    bulk_spy = mocker.patch("app.services.event_sectors_service.crud.bulk_add_event_sectors", new=mocker.AsyncMock())
    db = mocker.Mock()
    user = mocker.Mock()
    req = mocker.Mock()

    with pytest.raises(HTTPException) as e:
        await event_sectors_service.bulk_create_event_sectors(db, schema, event, user, req)

    assert e.value.status_code == status.HTTP_400_BAD_REQUEST
    get_sector_spy.assert_awaited_once()
    bulk_spy.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_event_sector_ok(mocker):
    event_sector = mocker.Mock()
    get_sector_spy = mocker.patch(
        "app.services.event_sectors_service.get_event_sector",
        new=mocker.AsyncMock(return_value=event_sector)
    )
    delete_spy = mocker.patch("app.services.event_sectors_service.crud.delete_event_sector", new=mocker.AsyncMock())
    db = mocker.Mock()
    db.flush = mocker.AsyncMock()
    user = mocker.Mock()
    req = mocker.Mock()

    await event_sectors_service.delete_event_sector(db, 1, 1, user, req)

    get_sector_spy.assert_awaited_once_with(db, 1, 1)
    delete_spy.assert_awaited_once_with(db, event_sector)
    db.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_event_sector_integrity_error_raises_409(mocker):
    mocker.patch("app.services.event_sectors_service.get_event_sector", new=mocker.AsyncMock())
    mocker.patch("app.services.event_sectors_service.crud.delete_event_sector", new=mocker.AsyncMock())
    db = mocker.Mock()
    db.flush = mocker.AsyncMock(side_effect=IntegrityError("fk", None, None))
    user = mocker.Mock()
    req = mocker.Mock()

    with pytest.raises(HTTPException) as e:
        await event_sectors_service.delete_event_sector(db, 1, 1, user, req)

    assert e.value.status_code == status.HTTP_409_CONFLICT
    assert e.value.detail == "Event sector in use"
