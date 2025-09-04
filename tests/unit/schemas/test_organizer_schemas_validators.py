import pytest
from pydantic import ValidationError
from app.domain.organizers.schemas import OrganizerCreateDTO


test_org_payload = {
    "name": "ABC Events",
    "email": "abcevents@gmail.com",
    "vat_number": "2393942231455",
    "registration_number": "REG12345",
    "iban": "PL341053420099760312356789123",
    "country_code": "PL"
}

@pytest.mark.parametrize("raw, expected", [
    ("600700800", "+48600700800"),
    ("600 700 800", "+48600700800"),
    ("+48 600-700-800", "+48600700800"),
    ("600-700-800", "+48600700800")
])
def test_phone_converted_to_e164(raw, expected):
    dto = OrganizerCreateDTO(**test_org_payload, phone_number=raw)
    assert dto.phone_number == expected


def test_missing_phone_raises_value_error():
    with pytest.raises(ValidationError) as e:
        OrganizerCreateDTO(**test_org_payload)
    assert "Phone number is required" in str(e.value)


def test_invalid_phone_number_format_raises_value_error():
    with pytest.raises(ValidationError) as e:
        OrganizerCreateDTO(**test_org_payload, phone_number="ABCDEFG")
    assert "Invalid phone number format" in str(e.value)


def test_invalid_phone_number_raises_value_error():
    with pytest.raises(ValueError) as e:
        OrganizerCreateDTO(**test_org_payload, phone_number="90345682")
    assert "Invalid phone number" in str(e.value)
