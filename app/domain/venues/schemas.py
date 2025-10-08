from pydantic import BaseModel, Field, ConfigDict, field_validator
from datetime import datetime
from app.core.utils.text_utils import strip_text


class VenueCreateDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')

    name: str = Field(min_length=2, max_length=100)
    address_id: int

    _strip_name = field_validator("name", mode='before')(strip_text)


class VenueReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra='forbid')

    id: int
    name: str
    address_id: int


class VenueUpdateDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')

    name: str = Field(min_length=2, max_length=100)

    _strip_name = field_validator("name", mode='before')(strip_text)


class VenuesQueryDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200)
    name: str | None = None


class SectorCreateDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')

    name: str = Field(min_length=1, max_length=15)
    base_capacity: int = Field(ge=1)
    is_ga: bool = Field(default=False)

    _strip_name = field_validator("name", mode='before')(strip_text)


class SectorReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra='forbid')

    id: int
    venue_id: int
    name: str
    base_capacity: int
    is_ga: bool
    created_at: datetime
    updated_at: datetime


class SectorUpdateDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')

    name: str = Field(min_length=1, max_length=15)

    _strip_name = field_validator("name", mode='before')(strip_text)


class SeatCreateDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')

    row: int = Field(gt=0)
    number: int = Field(gt=0)


class SeatBulkCreateDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')

    seats: list[SeatCreateDTO] = Field(min_length=1, max_length=5000)


class SeatReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra='forbid')

    id: int
    sector_id: int
    row: int
    number: int


class SeatUpdateDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')

    row: int | None = Field(default=None, gt=0)
    number: int | None = Field(default=None, gt=0)
