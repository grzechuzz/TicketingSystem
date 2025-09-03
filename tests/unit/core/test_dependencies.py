import pytest
from fastapi import HTTPException, status
from jose import JWTError
from app.core import dependencies
from sqlalchemy import Select


def create_db(mocker, value):
    fake_scalars = mocker.Mock()
    fake_scalars.first.return_value = value
    fake_result = mocker.Mock()
    fake_result.scalars.return_value = fake_scalars
    db = mocker.Mock()
    db.execute = mocker.AsyncMock(return_value=fake_result)
    return db, fake_result, fake_scalars


def create_role(mocker, name: str):
    role = mocker.Mock()
    role.name = name
    return role


def create_organizer(mocker, organizer_id: int):
    organizer = mocker.Mock()
    organizer.id = organizer_id
    return organizer


def create_event(mocker, organizer_id: int):
    event = mocker.Mock()
    event.organizer_id = organizer_id
    return event


def create_user(mocker, roles=None, organizers=None):
    user = mocker.Mock()
    user.roles = roles
    user.organizers = organizers
    return user


def create_event_ticket_type(mocker, event_sector_event_id: int):
    event_ticket_type = mocker.Mock()
    event_ticket_type.event_sector.event_id = event_sector_event_id
    return event_ticket_type


@pytest.mark.asyncio
async def test_get_token_payload_ok(mocker):
    mocker.patch("app.core.dependencies.SECRET_KEY", "fake-key")
    mocker.patch("app.core.dependencies.jwt.decode",
                 return_value={"sub": "7", "roles": ["ADMIN"], "iat": 1, "exp": 2})

    payload = await dependencies.get_token_payload("token")

    assert payload.sub == "7"
    assert payload.roles == ["ADMIN"]


@pytest.mark.asyncio
async def test_get_token_payload_invalid_jwt_raises_401(mocker):
    mocker.patch("app.core.dependencies.SECRET_KEY", "fake-key")
    mocker.patch("app.core.dependencies.jwt.decode", side_effect=JWTError("err"))

    with pytest.raises(HTTPException) as e:
        await dependencies.get_token_payload("bad-token")

    assert e.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert e.value.headers.get("WWW-Authenticate") == "Bearer"


@pytest.mark.asyncio
async def test_get_token_payload_invalid_payload_raises_401(mocker):
    mocker.patch("app.core.dependencies.SECRET_KEY", "fake-key")
    mocker.patch("app.core.dependencies.jwt.decode",
                 return_value={"sub": "7", "roles": ["ADMIN"], "iat": 1})

    with pytest.raises(HTTPException) as e:
        await dependencies.get_token_payload("token")

    assert e.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert e.value.headers.get("WWW-Authenticate") == "Bearer"


@pytest.mark.asyncio
async def test_get_current_user_with_roles_when_roles_intersect_and_user_found(mocker):
    dependency = dependencies.get_current_user_with_roles("ADMIN", "CUSTOMER")

    fake_user = create_user(mocker)
    db, fake_result, fake_scalars = create_db(mocker, fake_user)
    payload = mocker.Mock()
    payload.sub = "1"
    payload.roles = ["CUSTOMER"]

    user = await dependency(payload, db)

    assert user is fake_user
    db.execute.assert_awaited_once()
    fake_result.scalars.assert_called_once()
    fake_scalars.first.assert_called_once()
    assert isinstance(db.execute.call_args.args[0], Select)


@pytest.mark.asyncio
async def test_get_current_user_with_roles_when_roles_do_not_intersect_raises_403(mocker):
    dependency = dependencies.get_current_user_with_roles("ADMIN")

    payload = mocker.Mock()
    payload.roles = ["ORGANIZER", "CUSTOMER"]
    db = mocker.Mock()
    db.execute = mocker.AsyncMock()

    with pytest.raises(HTTPException) as e:
        await dependency(payload, db)

    assert e.value.status_code == status.HTTP_403_FORBIDDEN
    db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_current_user_with_roles_when_roles_intersect_and_user_not_found_raises_401(mocker):
    dependency = dependencies.get_current_user_with_roles("ORGANIZER")

    db, _, _ = create_db(mocker, None)
    payload = mocker.Mock()
    payload.roles = ["ORGANIZER"]
    payload.sub = "1"

    with pytest.raises(HTTPException) as e:
        await dependency(payload, db)

    assert e.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert e.value.headers.get("WWW-Authenticate") == "Bearer"


def test_require_organizer_member_when_organizer_organizer_id_in_user_organizers(mocker):
    role = create_role(mocker, "ORGANIZER")
    organizer1 = create_organizer(mocker, 1)
    organizer2 = create_organizer(mocker, 2)
    user = create_user(mocker, [role], [organizer1, organizer2])

    result = dependencies.require_organizer_member(1, user)

    assert result == 1


def test_require_organizer_member_when_admin(mocker):
    role = create_role(mocker, "ADMIN")
    user = create_user(mocker, [role])

    result = dependencies.require_organizer_member(333, user)

    assert result == 333


def test_require_organizer_member_when_organizer_id_not_in_user_organizer_raises_403(mocker):
    role = create_role(mocker, "ORGANIZER")
    organizer1 = create_organizer(mocker, 1)
    organizer2 = create_organizer(mocker, 2)
    user = create_user(mocker, [role], [organizer1, organizer2])

    with pytest.raises(HTTPException) as e:
        dependencies.require_organizer_member(3, user)

    assert e.value.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_require_event_owner_when_event_exists_and_user_is_event_organizer(mocker):
    organizer1 = create_organizer(mocker, 1)
    organizer2 = create_organizer(mocker, 2)
    role = create_role(mocker, "ORGANIZER")
    user = create_user(mocker, [role], [organizer1, organizer2])
    event = create_event(mocker, 1)
    db, _, _ = create_db(mocker, event)

    result = await dependencies.require_event_owner(1, db, user)

    assert result == event
    db.execute.assert_awaited_once()
    assert isinstance(db.execute.call_args.args[0], Select)


@pytest.mark.asyncio
async def test_require_event_owner_when_event_exists_and_user_is_not_event_organizer_raises_403(mocker):
    organizer1 = create_organizer(mocker, 1)
    organizer2 = create_organizer(mocker, 2)
    role = create_role(mocker, "ORGANIZER")
    user = create_user(mocker, [role], [organizer1, organizer2])
    event = create_event(mocker, 3)
    db, _, _ = create_db(mocker, event)

    with pytest.raises(HTTPException) as e:
        await dependencies.require_event_owner(1, db, user)

    assert e.value.status_code == status.HTTP_403_FORBIDDEN
    db.execute.assert_awaited_once()
    assert isinstance(db.execute.call_args.args[0], Select)


@pytest.mark.asyncio
async def test_require_event_owner_when_event_exists_and_user_is_admin(mocker):
    role = create_role(mocker, "ADMIN")
    user = create_user(mocker, [role])
    event = create_event(mocker, 1)
    db, _, _ = create_db(mocker, event)

    result = await dependencies.require_event_owner(1, db, user)

    assert result == event
    db.execute.assert_awaited_once()
    assert isinstance(db.execute.call_args.args[0], Select)


@pytest.mark.asyncio
async def test_require_event_owner_when_event_does_not_exist_raises_404(mocker):
    user = create_user(mocker)
    db, _, _ = create_db(mocker, None)

    with pytest.raises(HTTPException) as e:
        await dependencies.require_event_owner(1, db, user)

    assert e.value.status_code == status.HTTP_404_NOT_FOUND
    db.execute.assert_awaited_once()
    assert isinstance(db.execute.call_args.args[0], Select)


@pytest.mark.asyncio
async def test_require_event_ticket_type_access_when_event_ticket_type_exists(mocker):
    spy = mocker.patch("app.core.dependencies.require_event_owner", return_value=mocker.AsyncMock())
    user = create_user(mocker)
    event_ticket_type = create_event_ticket_type(mocker, 1)
    db, _, _ = create_db(mocker, event_ticket_type)

    result = await dependencies.require_event_ticket_type_access(1, db, user)

    assert result == event_ticket_type
    db.execute.assert_awaited_once()
    assert isinstance(db.execute.call_args.args[0], Select)
    spy.assert_awaited_once_with(1, db=db, user=user)


@pytest.mark.asyncio
async def test_require_event_ticket_type_access_when_event_ticket_type_does_not_exist_raises_404(mocker):
    user = create_user(mocker)
    db, _, _ = create_db(mocker, None)

    with pytest.raises(HTTPException) as e:
        await dependencies.require_event_ticket_type_access(1, db, user)

    assert e.value.status_code == status.HTTP_404_NOT_FOUND
    db.execute.assert_awaited_once()
    assert isinstance(db.execute.call_args.args[0], Select)
