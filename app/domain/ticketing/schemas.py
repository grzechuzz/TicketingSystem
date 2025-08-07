from pydantic import BaseModel, Field, ConfigDict


class EventSectorCreateDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')

    sector_id: int = Field(gt=0)


class EventSectorBulkCreateDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')

    sectors: list[EventSectorCreateDTO]


class EventSectorReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra='forbid')

    id: int
    event_id: int
    sector_id: int
    tickets_left: int | None


class TicketTypeCreateDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')

    name: str = Field(min_length=2, max_length=100)


class TicketTypeReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra='forbid')

    id: int
    name: str