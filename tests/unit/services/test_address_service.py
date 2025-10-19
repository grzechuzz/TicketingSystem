import pytest
from app.core.pagination import PageDTO
from app.domain.addresses.schemas import AddressesQueryDTO, AddressReadDTO
from app.domain.exceptions import NotFound
from app.services import address_service


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

    with pytest.raises(NotFound) as e:
        await address_service.get_address(db, 1)

    assert str(e.value) == "Address not found"
    assert e.value.ctx == {"address_id": 1}


@pytest.mark.asyncio
async def test_list_addresses_returns_addresses(mocker):
    addresses_raw = [
        {"id": 1, "city": "A", "street": "B", "postal_code": "42-191",
         "building_number": "1", "apartment_number": None, "country_code": "TS"},
        {"id": 2, "city": "A", "street": "C", "postal_code": "42-191",
         "building_number": "1", "apartment_number": "22", "country_code": "TS"}
    ]
    crud = mocker.patch(
        "app.services.address_service.crud.list_all_addresses",
        new=mocker.AsyncMock(return_value=(addresses_raw, 2))
    )
    db = mocker.Mock()
    query = AddressesQueryDTO(page=1, page_size=20)

    page = await address_service.list_addresses(db, query)

    crud.assert_awaited_once_with(db, 1, 20)
    assert isinstance(page, PageDTO)
    assert page.page == 1
    assert page.total == 2
    assert page.page_size == 20
    assert all(isinstance(item, AddressReadDTO) for item in page.items)


@pytest.mark.asyncio
async def test_list_addresses_empty_page(mocker):
    mocker.patch(
        "app.services.address_service.crud.list_all_addresses",
        new=mocker.AsyncMock(return_value=([], 0)),
    )

    page = await address_service.list_addresses(mocker.Mock(), AddressesQueryDTO(page=1, page_size=20))

    assert page.items == []
    assert page.total == 0


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


@pytest.mark.asyncio
async def test_update_address_returns_address(mocker):
    address = mocker.Mock()
    dto = mocker.Mock()
    dto.model_dump.return_value = {"test": "test"}
    mocker.patch("app.services.address_service.crud.update_address", new=mocker.AsyncMock(return_value=address))
    db = mocker.Mock()
    db.flush = mocker.AsyncMock()

    result = await address_service.update_address(db, dto, address)

    assert result is address
    assert db.flush.await_count == 1
