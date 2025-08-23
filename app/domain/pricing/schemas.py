from pydantic import BaseModel, Field, ConfigDict
from decimal import Decimal


class TicketTypeCreateDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')

    name: str = Field(min_length=2, max_length=100)


class TicketTypeReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra='forbid')

    id: int
    name: str


class EventTicketTypeCreateDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')

    ticket_type_id: int = Field(gt=0)
    price_net: Decimal = Field(gt=0, description='Price of a ticket')
    vat_rate: Decimal = Field(ge=1, le=2, description='VAT rate multiplier (eg. 1.23 = 23% vat rate)')


class EventTicketTypeBulkCreateDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')

    event_ticket_types: list[EventTicketTypeCreateDTO]


class EventTicketTypeReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra='forbid')

    id: int
    event_sector_id: int
    ticket_type_id: int
    price_net: Decimal
    vat_rate: Decimal


class EventTicketTypeUpdateDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')

    price_net: Decimal | None = Field(default=None, gt=0, description='Price of a ticket')
    vat_rate: Decimal | None = Field(default=None, ge=1, le=2, description='VAT rate multiplier (eg. 1.23 = 23% vat rate)')
