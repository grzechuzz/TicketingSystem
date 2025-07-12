from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict
from datetime import date
import re


class UserCreateDTO(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=64, description='Password must be between 8 and 64 characters long')
    first_name: str = Field(min_length=2, max_length=256)
    last_name: str = Field(min_length=2, max_length=256)
    phone_number: str | None = Field(default=None)
    birth_date: date | None = Field(default=None)

    @field_validator('password')
    def check_password(cls, password: str) -> str:
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
        return password

    @field_validator("phone_number")
    def check_phone_number(cls, v: str | None) -> str | None:
        if v is None or v == "":
            return None
        pattern = re.compile(r"^\+\d{1,15}$")
        if not pattern.match(v):
            raise ValueError("Wrong phone number format")
        return v


class UserReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    first_name: str
    last_name: str
    phone_number: str | None
    birth_date: date | None
