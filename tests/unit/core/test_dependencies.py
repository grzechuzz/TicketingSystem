import pytest
from fastapi import HTTPException, status
from jose import JWTError
from app.core import dependencies
from sqlalchemy import Select
from tests.helper import create_role, create_db


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

    fake_user = mocker.Mock()
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
    organizer1 = mocker.Mock(id=1)
    organizer2 = mocker.Mock(id=2)
    user = mocker.Mock(roles=[role], organizers=[organizer1, organizer2])

    result = dependencies.require_organizer_member(1, user)

    assert result == 1


def test_require_organizer_member_when_admin(mocker):
    role = create_role(mocker, "ADMIN")
    user = mocker.Mock(roles=[role])

    result = dependencies.require_organizer_member(333, user)

    assert result == 333


def test_require_organizer_member_when_organizer_id_not_in_user_organizer_raises_403(mocker):
    role = create_role(mocker, "ORGANIZER")
    organizer1 = mocker.Mock(id=1)
    organizer2 = mocker.Mock(id=2)
    user = mocker.Mock(roles=[role], organizers=[organizer1, organizer2])

    with pytest.raises(HTTPException) as e:
        dependencies.require_organizer_member(3, user)

    assert e.value.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_require_event_owner_when_event_exists_and_user_is_event_organizer(mocker):
    organizer1 = mocker.Mock(id=1)
    organizer2 = mocker.Mock(id=2)
    role = create_role(mocker, "ORGANIZER")
    user = mocker.Mock(roles=[role], organizers=[organizer1, organizer2])
    event = mocker.Mock(organizer_id=1)
    db, _, _ = create_db(mocker, event)

    result = await dependencies.require_event_owner(1, db, user)

    assert result == event
    db.execute.assert_awaited_once()
    assert isinstance(db.execute.call_args.args[0], Select)


@pytest.mark.asyncio
async def test_require_event_owner_when_event_exists_and_user_is_not_event_organizer_raises_403(mocker):
    organizer1 = mocker.Mock(id=1)
    organizer2 = mocker.Mock(id=2)
    role = create_role(mocker, "ORGANIZER")
    user = mocker.Mock(roles=[role], organizers=[organizer1, organizer2])
    event = mocker.Mock(organizer_id=3)
    db, _, _ = create_db(mocker, event)

    with pytest.raises(HTTPException) as e:
        await dependencies.require_event_owner(1, db, user)

    assert e.value.status_code == status.HTTP_403_FORBIDDEN
    db.execute.assert_awaited_once()
    assert isinstance(db.execute.call_args.args[0], Select)


@pytest.mark.asyncio
async def test_require_event_owner_when_event_exists_and_user_is_admin(mocker):
    role = create_role(mocker, "ADMIN")
    user = mocker.Mock(roles=[role])
    event = mocker.Mock(organizer_id=1)
    db, _, _ = create_db(mocker, event)

    result = await dependencies.require_event_owner(1, db, user)

    assert result == event
    db.execute.assert_awaited_once()
    assert isinstance(db.execute.call_args.args[0], Select)


@pytest.mark.asyncio
async def test_require_event_owner_when_event_does_not_exist_raises_404(mocker):
    user = mocker.Mock()
    db, _, _ = create_db(mocker, None)

    with pytest.raises(HTTPException) as e:
        await dependencies.require_event_owner(1, db, user)

    assert e.value.status_code == status.HTTP_404_NOT_FOUND
    db.execute.assert_awaited_once()
    assert isinstance(db.execute.call_args.args[0], Select)


@pytest.mark.asyncio
async def test_require_event_ticket_type_access_when_event_ticket_type_exists(mocker):
    spy = mocker.patch("app.core.dependencies.require_event_owner", new=mocker.AsyncMock(return_value=None))
    user = mocker.Mock()
    event_sector = mocker.Mock(event_id=1)
    event_ticket_type = mocker.Mock(event_sector=event_sector)
    db, _, _ = create_db(mocker, event_ticket_type)

    result = await dependencies.require_event_ticket_type_access(1, db, user)

    assert result == event_ticket_type
    db.execute.assert_awaited_once()
    assert isinstance(db.execute.call_args.args[0], Select)
    spy.assert_awaited_once_with(1, db=db, user=user)


@pytest.mark.asyncio
async def test_require_event_ticket_type_access_when_event_ticket_type_does_not_exist_raises_404(mocker):
    user = mocker.Mock()
    db, _, _ = create_db(mocker, None)

    with pytest.raises(HTTPException) as e:
        await dependencies.require_event_ticket_type_access(1, db, user)

    assert e.value.status_code == status.HTTP_404_NOT_FOUND
    db.execute.assert_awaited_once()
    assert isinstance(db.execute.call_args.args[0], Select)
