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


def create_address(mocker, venue=None, organizers=None):
    address = mocker.Mock()
    address.venue = venue
    address.organizers = organizers
    return address
