from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field


class ReserveTicketRequestDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')

    event_ticket_type_id: int = Field(gt=0)
    seat_id: int | None = Field(default=None, gt=0)


class ReserveTicketReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra='forbid')

    order_id: int
    ticket_instance_id: int
    reserved_until: datetime | None
    order_total_price: Decimal
