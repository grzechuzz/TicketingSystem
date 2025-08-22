from datetime import datetime, date
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field, model_validator, field_validator
from app.domain.booking.models import OrderStatus, InvoiceType
from app.core.text_utils import strip_text


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
    model_config = ConfigDict(from_attributes=True, extra='forbid')

    items: list[TicketInstanceReadDTO] = Field(
        default_factory=list,
        validation_alias='ticket_instances',
        serialization_alias='items'
    )


class InvoiceUpsertDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')

    invoice_type: InvoiceType
    full_name: str | None = Field(default=None, min_length=3, max_length=200)
    company_name: str | None = Field(default=None, min_length=2, max_length=200)
    tax_id: str | None = Field(default=None, min_length=6, max_length=32, pattern=r"^[A-Z0-9\-]+$")
    street: str = Field(min_length=2, max_length=200)
    postal_code: str = Field(min_length=4, max_length=12)
    city: str = Field(min_length=2, max_length=100)
    country_code: str = Field(min_length=2, max_length=2, pattern="^[A-Z]{2}$")

    _strip_full_name = field_validator("full_name", mode="before")(strip_text)
    _strip_company_name = field_validator("company_name", mode="before")(strip_text)
    _strip_tax_id = field_validator("tax_id", mode="before")(strip_text)
    _strip_street = field_validator("street", mode="before")(strip_text)
    _strip_postal_code = field_validator("postal_code", mode="before")(strip_text)
    _strip_city = field_validator("city", mode="before")(strip_text)
    _strip_country_code = field_validator("country_code", mode="before")(lambda v: strip_text(v).upper() if v else v)

    @model_validator(mode="after")
    def _check_person_or_company(self):
        if self.invoice_type == InvoiceType.COMPANY:
            if not self.company_name or not self.tax_id:
                raise ValueError("Company name and TAX ID are required for COMPANY invoice")
            self.full_name = None
            self.tax_id = self.tax_id.upper()
        else:
            if not self.full_name:
                raise ValueError("Full name is required for PERSON invoice")
            self.company_name = None
            self.tax_id = None
        return self


class InvoiceReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: int
    invoice_type: InvoiceType
    full_name: str | None
    company_name: str | None
    tax_id: str | None
    street: str
    postal_code: str
    city: str
    country_code: str
    created_at: datetime


class TicketHolderUpsertDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')

    first_name: str = Field(min_length=2, max_length=200)
    last_name: str = Field(min_length=2, max_length=200)
    birth_date: date
    identification_number: str = Field(min_length=6, max_length=100)

    _strip_first_name = field_validator("first_name", mode="before")(strip_text)
    _strip_last_name = field_validator("last_name", mode="before")(strip_text)
    _strip_identification_number = field_validator("identification_number", mode="before")(strip_text)


class TicketHolderReadDTO(BaseModel):
    model_config = ConfigDict(extra='forbid', from_attributes=True)
    id: int
    ticket_instance_id: int
    first_name: str
    last_name: str
    birth_date: date
    identification_number: str


class InvoiceRequestDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')

    invoice_requested: bool
