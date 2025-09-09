import pytest
from fastapi import HTTPException, status
from app.services import address_service
from tests.helper import create_role


@pytest.mark.asyncio
async def test_get_address_returns_address(mocker):
    address = mocker.Mock()
    mocker.patch(
        "app.services.address_service.crud.get_address_by_id",
        new=mocker.AsyncMock(return_value=address)
    )
    db = mocker.Mock()

    result = await address_service.get_address(db, 1)

    assert result is address


@pytest.mark.asyncio
async def test_get_address_not_found_raises_404(mocker):
    mocker.patch(
        "app.services.address_service.crud.get_address_by_id",
        new=mocker.AsyncMock(return_value=None)
    )
    db = mocker.Mock()

    with pytest.raises(HTTPException) as e:
        await address_service.get_address(db, 1)

    assert e.value.status_code == status.HTTP_404_NOT_FOUND

# TODO
"""
@pytest.mark.asyncio
async def test_list_addresses_returns_addresses(mocker):
    addresses = [mocker.Mock(), mocker.Mock()]
    spy = mocker.patch(
        "app.services.address_service.crud.list_all_addresses",
        new=mocker.AsyncMock(return_value=addresses)
    )
    db = mocker.Mock()

    result = await address_service.list_addresses(db)

    assert result == addresses
    spy.assert_awaited_once_with(db)
"""

@pytest.mark.asyncio
async def test_create_address_returns_address(mocker):
    address = mocker.Mock()
    mocker.patch(
        "app.services.address_service.crud.create_address",
        new=mocker.AsyncMock(return_value=address)
    )
    db = mocker.Mock()
    db.flush = mocker.AsyncMock()
    dto = mocker.Mock()
    dto.model_dump.return_value = {"test": "test"}

    result = await address_service.create_address(db, dto)

    assert result is address
    db.flush.assert_awaited_once_with()
    dto.model_dump.assert_called_once_with(exclude_none=True)


@pytest.mark.asyncio
async def test_get_authorized_address_admin_returns_address(mocker):
    address = mocker.Mock()
    db = mocker.Mock()
    role1 = create_role(mocker, "ADMIN")
    role2 = create_role(mocker, "ORGANIZER")
    current_user = mocker.Mock(roles=[role1, role2], organizers=None)
    mocker.patch("app.services.address_service.get_address", new=mocker.AsyncMock(return_value=address))

    result = await address_service.get_authorized_address(db, 1, current_user)

    assert result is address


@pytest.mark.asyncio
async def test_get_authorized_address_organizer_returns_address(mocker):
    organizer1 = mocker.Mock(id=1)
    organizer2 = mocker.Mock(id=2)
    address = mocker.Mock(venue=None, organizers=[organizer1, organizer2])
    mocker.patch("app.services.address_service.get_address", new=mocker.AsyncMock(return_value=address))
    db = mocker.Mock()
    role = create_role(mocker, "ORGANIZER")
    current_user = mocker.Mock(roles=[role], organizers=[organizer1])

    result = await address_service.get_authorized_address(db, 1, current_user)

    assert result is address


@pytest.mark.asyncio
async def test_get_authorized_address_empty_intersection_addresses_organizers_raises_403(mocker):
    organizer1 = mocker.Mock(id=1)
    organizer2 = mocker.Mock(id=2)
    address = mocker.Mock(venue=None, organizers=[organizer1])
    mocker.patch("app.services.address_service.get_address", new=mocker.AsyncMock(return_value=address))
    db = mocker.Mock()
    role = create_role(mocker, "ORGANIZER")
    current_user = mocker.Mock(roles=[role], organizers=[organizer2])

    with pytest.raises(HTTPException) as e:
        await address_service.get_authorized_address(db, 1, current_user)

    assert e.value.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_get_authorized_address_address_already_has_venue_raises_403(mocker):
    organizer1 = mocker.Mock(id=1)
    address = mocker.Mock(venue=mocker.Mock(), organizers=[organizer1])
    mocker.patch("app.services.address_service.get_address", new=mocker.AsyncMock(return_value=address))
    role = create_role(mocker, "ORGANIZER")
    current_user = mocker.Mock(roles=[role], organizers=[organizer1])
    db = mocker.Mock()

    with pytest.raises(HTTPException) as e:
        await address_service.get_authorized_address(db, 1, current_user)

    assert e.value.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_update_address_returns_address(mocker):
    address = mocker.Mock()
    mocker.patch("app.services.address_service.get_authorized_address", new=mocker.AsyncMock(return_value=address))
    dto = mocker.Mock()
    dto.model_dump.return_value = {"test": "test"}
    mocker.patch("app.services.address_service.crud.update_address", new=mocker.AsyncMock(return_value=address))
    current_user = mocker.Mock()
    db = mocker.Mock()

    result = await address_service.update_address(db, dto, 1, current_user)

    assert result is address
