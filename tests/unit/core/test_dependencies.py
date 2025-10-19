import pytest
from jose import JWTError
from app.core.dependencies.auth import get_current_user_with_roles, get_token_payload
from app.core.dependencies.events import require_organizer_member, require_event_ticket_type_access
from app.core.dependencies.addresses import require_authorized_address
from app.domain.exceptions import Unauthorized, Forbidden, NotFound
from tests.helper import create_role, db_with_scalars_first, db_with_tuples_first


@pytest.mark.asyncio
async def test_get_token_payload_ok(mocker):
    mocker.patch("app.core.dependencies.auth.SECRET_KEY", "fake-key")
    mocker.patch("app.core.dependencies.auth.jwt.decode",
                 return_value={
                     "sub": "7",
                     "iat": 1,
                     "exp": 2,
                     "nbf": 1,
                     "typ": "access",
                     "iss": "ticketing-api",
                     "aud": "web"
                 })

    payload = await get_token_payload("token")

    assert payload.sub == "7"


@pytest.mark.asyncio
async def test_get_token_payload_invalid_jwt_raises_401(mocker):
    mocker.patch("app.core.dependencies.auth.SECRET_KEY", "fake-key")
    mocker.patch("app.core.dependencies.auth.jwt.decode", side_effect=JWTError("err"))

    with pytest.raises(Unauthorized) as e:
        await get_token_payload("bad-token")

    assert "invalid_token" in e.value.ctx.get("reason", "")


@pytest.mark.asyncio
async def test_get_token_payload_invalid_payload_raises_401(mocker):
    mocker.patch("app.core.dependencies.auth.SECRET_KEY", "fake-key")
    mocker.patch("app.core.dependencies.auth.jwt.decode",
                 return_value={"sub": "7", "iat": 1})

    with pytest.raises(Unauthorized) as e:
        await get_token_payload("invalid-payload")

    assert e.value.ctx.get("reason") == "invalid_type"


@pytest.mark.asyncio
async def test_get_current_user_with_roles_when_roles_intersect_and_user_found(mocker):
    dependency = get_current_user_with_roles("ADMIN", "CUSTOMER")
    role = create_role(mocker, "CUSTOMER")
    fake_user = mocker.Mock(is_active=True, roles=[role])

    db, res = db_with_scalars_first(mocker, fake_user)
    payload = mocker.Mock(sub="1")

    user = await dependency(payload, db)

    assert user is fake_user
    db.execute.assert_awaited_once()
    res.scalars.assert_called_once()
    res.scalars.return_value.first.assert_called_once()


@pytest.mark.asyncio
async def test_get_current_user_with_roles_when_roles_do_not_intersect_raises_403(mocker):
    dependency = get_current_user_with_roles("ADMIN")
    role = create_role(mocker, "ORGANIZER")
    fake_user = mocker.Mock(is_active=True, roles=[role])

    db, res = db_with_scalars_first(mocker, fake_user)
    payload = mocker.Mock(sub="1")

    with pytest.raises(Forbidden) as e:
        await dependency(payload, db)

    assert e.value.ctx["required"] == "['ADMIN']"
    db.execute.assert_awaited_once()
    res.scalars.assert_called_once()
    res.scalars.return_value.first.assert_called_once()


@pytest.mark.asyncio
async def test_get_current_user_with_roles_when_roles_intersect_and_user_not_found_raises_401(mocker):
    dependency = get_current_user_with_roles("ORGANIZER")

    db, result = db_with_scalars_first(mocker, None)
    payload = mocker.Mock(sub="1")

    with pytest.raises(Unauthorized) as e:
        await dependency(payload, db)

    assert str(e.value) == "User not found"
    assert e.value.ctx == {"user_id": "1"}

    db.execute.assert_awaited_once()
    result.scalars.assert_called_once()
    result.scalars.return_value.first.assert_called_once()


def test_require_organizer_member_when_organizer_organizer_id_in_user_organizers(mocker):
    role = create_role(mocker, "ORGANIZER")
    organizer1 = mocker.Mock(id=1)
    organizer2 = mocker.Mock(id=2)
    user = mocker.Mock(roles=[role], organizers=[organizer1, organizer2])

    result = require_organizer_member(1, user)

    assert result == 1


def test_require_organizer_member_when_admin(mocker):
    role = create_role(mocker, "ADMIN")
    user = mocker.Mock(roles=[role])

    result = require_organizer_member(333, user)

    assert result == 333


def test_require_organizer_member_when_organizer_id_not_in_user_organizer_raises_403(mocker):
    role = create_role(mocker, "ORGANIZER")
    user = mocker.Mock(roles=[role], organizers=[mocker.Mock(id=1), mocker.Mock(id=2)])

    with pytest.raises(Forbidden) as e:
        require_organizer_member(3, user)

    assert str(e.value) == "Not allowed"
    assert e.value.ctx == {"organizer_id": 3, "reason": "organizer_mismatch"}


@pytest.mark.asyncio
async def test_get_current_user_with_roles_when_user_not_found_raises_401(mocker):
    dependency = get_current_user_with_roles("ORGANIZER")

    db, res = db_with_scalars_first(mocker, None)
    payload = mocker.Mock(sub="1")

    with pytest.raises(Unauthorized) as e:
        await dependency(payload, db)

    assert e.value.ctx["user_id"] == "1"
    db.execute.assert_awaited_once()
    res.scalars.assert_called_once()
    res.scalars.return_value.first.assert_called_once()


@pytest.mark.asyncio
async def test_require_event_owner_ok_for_admin(mocker):
    from app.core.dependencies.events import require_event_owner
    event = mocker.Mock(organizer_id=123)
    db, res = db_with_scalars_first(mocker, event)
    user = mocker.Mock(roles=[create_role(mocker, "ADMIN")])

    out = await require_event_owner(1, db, user)

    assert out is event
    db.execute.assert_awaited_once()
    res.scalars.assert_called_once()
    res.scalars.return_value.first.assert_called_once()

@pytest.mark.asyncio
async def test_require_event_owner_forbidden_when_not_organizer(mocker):
    from app.core.dependencies.events import require_event_owner
    event = mocker.Mock(organizer_id=3)
    db, res = db_with_scalars_first(mocker, event)
    user = mocker.Mock(
        roles=[create_role(mocker, "ORGANIZER")],
        organizers=[mocker.Mock(id=1), mocker.Mock(id=2)],
    )

    with pytest.raises(Forbidden) as e:
        await require_event_owner(1, db, user)

    assert str(e.value) == "Not allowed"
    assert e.value.ctx == {"event_id": 1, "reason": "organizer_mismatch"}
    db.execute.assert_awaited_once()
    res.scalars.assert_called_once()
    res.scalars.return_value.first.assert_called_once()


@pytest.mark.asyncio
async def test_require_event_owner_not_found(mocker):
    from app.core.dependencies.events import require_event_owner
    db, res = db_with_scalars_first(mocker, None)
    user = mocker.Mock()

    with pytest.raises(NotFound) as e:
        await require_event_owner(1, db, user)

    assert str(e.value) == "Event not found"
    assert e.value.ctx == {"event_id": 1}
    db.execute.assert_awaited_once()
    res.scalars.assert_called_once()
    res.scalars.return_value.first.assert_called_once()


@pytest.mark.asyncio
async def test_require_event_owner_ok_for_organizer_member(mocker):
    from app.core.dependencies.events import require_event_owner
    event = mocker.Mock(organizer_id=2)
    db, res = db_with_scalars_first(mocker, event)
    user = mocker.Mock(
        roles=[create_role(mocker, "ORGANIZER")],
        organizers=[mocker.Mock(id=1), mocker.Mock(id=2)],
    )

    out = await require_event_owner(1, db, user)

    assert out is event
    db.execute.assert_awaited_once()
    res.scalars.assert_called_once()
    res.scalars.return_value.first.assert_called_once()


@pytest.mark.asyncio
async def test_require_event_ticket_type_access_when_event_ticket_type_exists(mocker):
    spy = mocker.patch(
        "app.core.dependencies.events._ensure_event_owner",
        new=mocker.AsyncMock(return_value=None),
    )

    user = mocker.Mock()
    event_ticket_type = mocker.Mock()
    db, _res = db_with_tuples_first(mocker, (event_ticket_type, 1))

    returned = await require_event_ticket_type_access(1, db, user)

    assert returned.event_ticket_type is event_ticket_type
    assert returned.user is user
    db.execute.assert_awaited_once()
    spy.assert_awaited_once_with(1, db=db, user=user)


@pytest.mark.asyncio
async def test_require_event_ticket_type_access_when_not_found_raises_404(mocker):
    user = mocker.Mock()
    db, res = db_with_tuples_first(mocker, None)

    with pytest.raises(NotFound) as e:
        await require_event_ticket_type_access(1, db, user)

    assert str(e.value) == "Event ticket type not found"
    assert e.value.ctx == {"event_ticket_type_id": 1}
    db.execute.assert_awaited_once()
    res.tuples.assert_called_once()
    res.tuples.return_value.first.assert_called_once()


@pytest.mark.asyncio
async def test_require_authorized_address_admin_ok(mocker):
    address = mocker.Mock(organizers=[], venue=mocker.Mock())
    mocker.patch(
        "app.core.dependencies.addresses.crud.get_address_by_id",
        new=mocker.AsyncMock(return_value=address),
    )
    admin_role = mocker.Mock()
    admin_role.name = "ADMIN"
    user = mocker.Mock(roles=[admin_role])

    db = mocker.Mock()

    result = await require_authorized_address(123, db, user)
    assert result is address


@pytest.mark.asyncio
async def test_require_authorized_address_not_found_raises_404(mocker):
    mocker.patch(
        "app.core.dependencies.addresses.crud.get_address_by_id",
        new=mocker.AsyncMock(return_value=None),
    )
    db = mocker.Mock()
    user = mocker.Mock()

    with pytest.raises(NotFound) as e:
        await require_authorized_address(777, db, user)

    assert e.value.ctx == {"address_id": 777}


@pytest.mark.asyncio
async def test_require_authorized_address_organizer_ok_when_shared_org_and_not_attached(mocker):
    addr_org = mocker.Mock(id=5)
    address = mocker.Mock(organizers=[addr_org], venue=None)
    mocker.patch(
        "app.core.dependencies.addresses.crud.get_address_by_id",
        new=mocker.AsyncMock(return_value=address),
    )
    org_role = mocker.Mock()
    org_role.name = "ORGANIZER"
    user = mocker.Mock(roles=[org_role], organizers=[mocker.Mock(id=5), mocker.Mock(id=9)])
    db = mocker.Mock()

    result = await require_authorized_address(10, db, user)

    assert result is address


@pytest.mark.asyncio
async def test_require_authorized_address_organizer_mismatch_raises_403(mocker):
    address = mocker.Mock(organizers=[mocker.Mock(id=2)], venue=None)
    mocker.patch(
        "app.core.dependencies.addresses.crud.get_address_by_id",
        new=mocker.AsyncMock(return_value=address),
    )
    org_role = mocker.Mock()
    org_role.name = "ORGANIZER"
    user = mocker.Mock(roles=[org_role], organizers=[mocker.Mock(id=7), mocker.Mock(id=8)])

    db = mocker.Mock()

    with pytest.raises(Forbidden) as e:
        await require_authorized_address(44, db, user)

    assert e.value.ctx == {"address_id": 44, "reason": "organizer_mismatch"}


@pytest.mark.asyncio
async def test_require_authorized_address_attached_to_venue_raises_403(mocker):
    addr_org = mocker.Mock(id=1)
    address = mocker.Mock(organizers=[addr_org], venue=mocker.Mock())
    mocker.patch(
        "app.core.dependencies.addresses.crud.get_address_by_id",
        new=mocker.AsyncMock(return_value=address),
    )
    org_role = mocker.Mock()
    org_role.name = "ORGANIZER"
    user = mocker.Mock(roles=[org_role], organizers=[mocker.Mock(id=1)])

    db = mocker.Mock()

    with pytest.raises(Forbidden) as e:
        await require_authorized_address(55, db, user)

    assert e.value.ctx == {"address_id": 55, "reason": "address_attached_to_venue"}
