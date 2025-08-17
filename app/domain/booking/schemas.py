from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field
from app.domain.booking.models import OrderStatus


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


class TicketInstanceReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra='forbid', populate_by_name=True)

    id: int
    event_ticket_type_id: int
    seat_id: int | None
    price_net: Decimal = Field(validation_alias='price_net_snapshot')
    vat_rate: Decimal = Field(validation_alias='vat_rate_snapshot')
    price_gross: Decimal = Field(validation_alias='price_gross_snapshot')


class OrderSummaryDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra='forbid')

    id: int
    status: OrderStatus
    total_price: Decimal
    reserved_until: datetime | None
    created_at: datetime


class OrderDetailsDTO(OrderSummaryDTO):
    items: list[TicketInstanceReadDTO] = Field(
        default_factory=list,
        validation_alias='ticket_instances',
        serialization_alias='items'
    )
