def create_db(mocker, value):
    fake_scalars = mocker.Mock()
    fake_scalars.first = mocker.Mock(return_value=value)
    fake_result = mocker.Mock()
    fake_result.scalars = mocker.Mock(return_value=fake_scalars)
    db = mocker.Mock()
    db.execute = mocker.AsyncMock(return_value=fake_result)
    return db, fake_result, fake_scalars


def create_role(mocker, name: str):
    role = mocker.Mock()
    role.name = name
    return role
