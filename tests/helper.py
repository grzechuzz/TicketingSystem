def db_with_scalars_first(mocker, value):
    res = mocker.Mock()
    res.scalars.return_value.first.return_value = value
    db = mocker.Mock()
    db.execute = mocker.AsyncMock(return_value=res)
    return db, res


def db_with_tuples_first(mocker, tuple_value):
    res = mocker.Mock()
    res.tuples.return_value.first.return_value = tuple_value
    db = mocker.Mock()
    db.execute = mocker.AsyncMock(return_value=res)
    return db, res


def db_with_scalar(mocker, value):
    db = mocker.Mock()
    db.scalar = mocker.AsyncMock(return_value=value)
    return db


def create_role(mocker, name: str):
    role = mocker.Mock()
    role.name = name
    return role
