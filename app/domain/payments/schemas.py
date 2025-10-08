from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.core.utils.text_utils import strip_text
from decimal import Decimal
from app.domain.payments.models import PaymentStatus


class PaymentMethodCreateDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')

    name: str

    _strip_name = field_validator("name", mode="before")(strip_text)


class PaymentMethodUpdateDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')

    name: str | None = Field(default=None, min_length=2, max_length=100)
    is_active: bool | None = None

    _strip_name = field_validator("name", mode="before")(strip_text)


class PaymentMethodReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra='forbid')

    id: int
    name: str
    is_active: bool


class PaymentCreateDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')

    payment_method_id: int = Field(gt=0)


class PaymentReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra='forbid')

    id: int
    order_id: int
    payment_method_id: int
    amount: Decimal
    provider: str
    status: PaymentStatus
    created_at: datetime
    paid_at: datetime | None
    redirect_url: str | None = None


class PaymentFinalizeDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')

    success: bool


class PaymentInOrderDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra='forbid')

    id: int
    amount: Decimal
    payment_method: PaymentMethodReadDTO
    paid_at: datetime
    provider: str


class AdminPaymentReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra='forbid')

    id: int
    order_id: int
    user_id: int
    user_email: str
    status: PaymentStatus
    amount: Decimal
    payment_method: PaymentMethodReadDTO
    created_at: datetime
    paid_at: datetime | None
