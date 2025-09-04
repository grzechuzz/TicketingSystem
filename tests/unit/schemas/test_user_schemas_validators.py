import pytest
from pydantic import ValidationError
from app.domain.users.schemas import UserCreateDTO


test_user_payload = {
    "email": "john@gmail.com",
    "first_name": "John",
    "last_name": "Derek",
    "birth_date": None,
    "phone_number": None
}


def create_payload(**override):
    data = dict(test_user_payload)
    data.setdefault("password", "Str0ng!Password")
    data.setdefault("password_confirm", "Str0ng!Password")
    data.update(override)
    return data


def test_check_password_pass_validation():
    dto = UserCreateDTO(**create_payload())
    assert dto.password.get_secret_value() == "Str0ng!Password"


@pytest.mark.parametrize(
    "password, expected_parts",
    [
        ("ABCDEFGH1!", {"a lowercase letter"}),
        ("abcdefgh1!", {"an uppercase letter"}),
        ("Abcdefgh!!", {"a digit"}),
        ("Abcdefgh1", {"a special character"}),
        ("abcdefgh", {"an uppercase letter", "a digit", "a special character"})
    ]
)
def test_check_password_weak_passwords_raise_validation_error(password, expected_parts):
    with pytest.raises(ValidationError) as e:
        UserCreateDTO(**create_payload(**{"password": password, "password_confirm": password}))
    msg = str(e.value)
    for part in expected_parts:
        assert part in msg


def test_passwords_do_not_match_raises_validation_error():
    with pytest.raises(ValidationError) as e:
        UserCreateDTO(**create_payload(**{"password_confirm": "Tokyo123@!"}))
    assert "Passwords do not match" in str(e.value)


def test_phone_valid_e164_passes():
    dto = UserCreateDTO(**create_payload(phone_number="+48123456789"))
    assert dto.phone_number == "+48123456789"


@pytest.mark.parametrize("bad_phone_number", [
    "123456789",
    "+48 123 456 789",
    "+48-123-456-789",
    "+48ABCDEF",
    "+" + "1"*16,
])
def test_phone_invalid_formats_raise_validation_error(bad_phone_number):
    with pytest.raises(ValidationError) as e:
        UserCreateDTO(**create_payload(phone_number=bad_phone_number))
    assert "Wrong phone number format" in str(e.value)
