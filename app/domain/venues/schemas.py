from pydantic import BaseModel, Field, ConfigDict, field_validator
from datetime import datetime


class VenueCreateDTO(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    address_id: int

    @field_validator("name", mode="before")
    def strip_name(cls, v: str) -> str:
        return v.strip()


class VenueReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    address_id: int


class VenueUpdateDTO(BaseModel):
    name: str = Field(min_length=2, max_length=100)

    @field_validator("name", mode="before")
    def strip_name(cls, v: str) -> str:
        return v.strip()


class SectorCreateDTO(BaseModel):
    venue_id: int
    name: str = Field(min_length=1, max_length=15)
    base_capacity: int = Field(ge=1)
    is_ga: bool = Field(default=False)

    @field_validator("name", mode="before")
    def strip_name(cls, v: str) -> str:
        return v.strip()


class SectorReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    venue_id: int
    name: str
    base_capacity: int
    is_ga: bool
    created_at: datetime
    updated_at: datetime


class SectorUpdateDTO(BaseModel):
    name: str = Field(min_length=1, max_length=15)

    @field_validator("name", mode="before")
    def strip_name(cls, v: str) -> str:
        return v.strip()