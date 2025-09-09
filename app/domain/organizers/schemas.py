from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, model_validator, ValidationError, ConfigDict
from phonenumbers import parse, format_number, is_valid_number, PhoneNumberFormat, NumberParseException

class OrganizerCreateDTO(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    phone_number: str
    vat_number: str | None = Field(default=None, min_length=8, max_length=32, pattern=r"^[A-Z0-9]+$")
    registration_number: str | None = Field(default=None, min_length=5, max_length=40, pattern=r"^[A-Z0-9]+$")
    iban: str | None = Field(default=None, min_length=15, max_length=34, pattern=r"^[A-Z]{2}[0-9A-Z]{13,32}$")
    country_code: str = Field(min_length=2, max_length=2, pattern="^[A-Z]{2}$")
    address_id: int

    @model_validator(mode='before')
    def validate_phone_and_region(cls, data: dict) -> dict:
        raw = data.get('phone_number')
        region = data.get('country_code', '').upper()

        if not raw or not raw.strip():
            raise ValueError('Phone number is required')

        try:
            num = parse(raw, region)
        except NumberParseException:
            raise ValueError('Invalid phone number format')

        if not is_valid_number(num):
            raise ValueError('Invalid phone number')

        data['phone_number'] = format_number(num, PhoneNumberFormat.E164)
        return data


class OrganizerReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    phone_number: str
    vat_number: str
    registration_number: str
    iban: str
    country_code: str
    address_id: int
    created_at: datetime


class OrganizerPutDTO(OrganizerCreateDTO):
    pass


class OrganizersQueryDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200)
    name: str | None = None
    email: str | None = None
    registration_number: str | None = None
