from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict, SecretStr, model_validator
from phonenumbers import parse, is_valid_number, format_number, PhoneNumberFormat, NumberParseException
from datetime import date, datetime
from typing import Literal
import re


class UserCreateDTO(BaseModel):
    email: EmailStr
    password: SecretStr = Field(
        min_length=8,
        max_length=64,
        description='Password must be between 8 and 64 characters long'
    )
    password_confirm: SecretStr = Field(min_length=8, max_length=64)
    first_name: str = Field(min_length=2, max_length=256)
    last_name: str = Field(min_length=2, max_length=256)
    phone_number: str | None = Field(default=None)
    birth_date: date | None = Field(default=None)

    @field_validator('password')
    def check_password(cls, v: SecretStr) -> SecretStr:
        password = v.get_secret_value()
        errors = []
        if not re.search(r'[a-z]', password):
            errors.append('a lowercase letter')
        if not re.search(r'[A-Z]', password):
            errors.append('an uppercase letter')
        if not re.search(r'\d', password):
            errors.append('a digit')
        if not re.search(r'[^\w\s]', password):
            errors.append('a special character')
        if errors:
            needed = ', '.join(errors)
            raise ValueError(f'Password must contain: {needed}')
        return v

    @field_validator("phone_number")
    def check_phone_number(cls, v: str | None) -> str | None:
        if v is None or v.strip() == "":
            return None
        try:
            num = parse(v, None)
        except NumberParseException:
            raise ValueError('Invalid phone number')
        if not is_valid_number(num):
            raise ValueError('Invalid phone number')
        return format_number(num, PhoneNumberFormat.E164)

    @model_validator(mode="after")
    def passwords_match(self):
        if self.password.get_secret_value() != self.password_confirm.get_secret_value():
            raise ValueError("Passwords do not match")
        return self


class UserReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    first_name: str
    last_name: str
    phone_number: str | None
    birth_date: date | None


class Token(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int = Field(description='Expiration time in seconds')


class TokenPayload(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sub: str
    roles: list[str]
    iat: int
    exp: int

