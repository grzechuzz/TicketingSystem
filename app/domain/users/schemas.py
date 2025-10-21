from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict, SecretStr, model_validator, computed_field
from datetime import date, datetime
from app.core.utils.validators import check_password_strength, normalize_phone_or_none, ensure_passwords_match


ALLOWED_ROLES = {"CUSTOMER", "ORGANIZER"}


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
    def _check_password(cls, v: SecretStr) -> SecretStr:
        check_password_strength(v)
        return v

    _phone = field_validator('phone_number', mode="before")(normalize_phone_or_none)

    @model_validator(mode="after")
    def _passwords_match(self):
        return ensure_passwords_match(self, self.password, self.password_confirm)


class UserReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    first_name: str
    last_name: str
    phone_number: str | None
    birth_date: date | None


class RoleReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class AdminUserListItemDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    phone_number: str | None
    first_name: str
    last_name: str
    created_at: datetime
    roles: list[RoleReadDTO]

    @computed_field(return_type=bool)
    @property
    def is_admin(self) -> bool:
        return any(r.name == "ADMIN" for r in self.roles)


class AdminUsersQueryDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200)
    email: str | None = None
    name: str | None = None
    role: str | None = None
    is_active: bool | None = None
    created_from: datetime | None = None
    created_to: datetime | None = None


class PasswordChangeDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')

    old_password: SecretStr = Field(min_length=8, max_length=64)
    new_password: SecretStr = Field(min_length=8, max_length=64)
    confirm_new_password: SecretStr = Field(min_length=8, max_length=64)

    @field_validator('new_password')
    def _check_password(cls, v: SecretStr) -> SecretStr:
        check_password_strength(v)
        return v

    @model_validator(mode="after")
    def _passwords_match(self):
        return ensure_passwords_match(self, self.new_password, self.confirm_new_password)


class UserRolesUpdateDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')

    roles: list[str] = Field(default_factory=list, max_length=2)

    @field_validator('roles', mode='before')
    def _normalize(cls, v):
        if v is None:
            return []
        if isinstance(v, str):
            v = [v]

        seen, out = set(), []
        for x in v:
            n = str(x).strip().upper()
            if not n or n not in ALLOWED_ROLES:
                raise ValueError(f'Invalid role: {x}')
            if n not in seen:
                seen.add(n)
                out.append(n)
        return out
