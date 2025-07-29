from pydantic import BaseModel, Field, ConfigDict, field_validator
from datetime import datetime
from app.domain.events.models import EventStatus
from app.core.text_utils import strip_text


class EventCreateDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')

    name: str = Field(min_length=5, max_length=100)
    venue_id: int
    event_start: datetime
    event_end: datetime
    sales_start: datetime
    sales_end: datetime
    max_tickets_per_user: int | None = Field(default=None, gt=0)
    age_restriction: int | None = Field(default=None, ge=0)
    holder_data_required: bool = Field(default=False)
    description: str | None = Field(min_length=10, max_length=1000)

    _strip_name = field_validator("name", mode="before")(strip_text)
    _strip_desc = field_validator("description", mode="before")(strip_text)


class EventReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra='forbid')

    id: int
    name: str
    organizer_id: int
    venue_id: int
    status: EventStatus
    event_start: datetime
    event_end: datetime
    sales_start: datetime
    sales_end: datetime
    max_tickets_per_user: int | None
    age_restriction: int | None
    holder_data_required: bool
    description: str | None
    created_at: datetime
    updated_at: datetime


class EventUpdateDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=5, max_length=100)
    description: str | None = Field(default=None, min_length=10, max_length=1000)
    event_start: datetime | None = None
    event_end: datetime | None = None
    sales_start: datetime | None = None
    sales_end: datetime | None = None
    max_tickets_per_user: int | None = Field(default=None, gt=0)
    age_restriction: int | None = Field(default=None, ge=0)
    holder_data_required: bool | None = None

    _strip_name = field_validator("name", mode="before")(strip_text)
    _strip_desc = field_validator("description", mode="before")(strip_text)


class EventStatusDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    new_status: EventStatus
