from pydantic import BaseModel, ConfigDict, Field
from typing import Literal


class Token(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int = Field(description='Expiration time in seconds')


class TokenPayload(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sub: str
    iat: int
    nbf: int
    exp: int
    jti: str | None = None
    typ: Literal["access", "refresh"] | None = None
    iss: str | None = None
    aud: str | list[str] | None = None
    sid: str | None = None


class LoginResponse(Token):
    refresh_token: str
    refresh_expires_in: int
    sid: str


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str
    