import pytest
from pydantic import ValidationError
from app.domain.booking.schemas import InvoiceUpsertDTO
from app.domain.booking.models import InvoiceType


def test_person_invoice_upsert_passes_validation_and_trimmed():
    dto = InvoiceUpsertDTO(
        invoice_type=InvoiceType.PERSON,
        full_name=" John Cox   ",
        street=" Grodzka ",
        postal_code=" 00-001 ",
        city=" Krakow ",
        country_code=" pl "
    )

    assert dto.full_name == "John Cox"
    assert dto.company_name is None
    assert dto.tax_id is None
    assert dto.street == "Grodzka"
    assert dto.postal_code == "00-001"
    assert dto.city == "Krakow"
    assert dto.country_code == "PL"


def test_company_invoice_upsert_passes_validation_and_trimmed():
    dto = InvoiceUpsertDTO(
        invoice_type=InvoiceType.COMPANY,
        company_name=" Company A ",
        tax_id=" 2334344 ",
        street=" Grodzka ",
        postal_code=" 00-001 ",
        city=" Krakow ",
        country_code=" pl "
    )

    assert dto.full_name is None
    assert dto.company_name == "Company A"
    assert dto.tax_id == "2334344"
    assert dto.street == "Grodzka"
    assert dto.postal_code == "00-001"
    assert dto.city == "Krakow"
    assert dto.country_code == "PL"


def test_person_invoice_upsert_missing_required_fields():
    with pytest.raises(ValidationError):
        InvoiceUpsertDTO(
            invoice_type=InvoiceType.PERSON,
            street=" Grodzka ",
            postal_code=" 00-001 ",
            city=" Krakow ",
            country_code=" pl "
        )


def test_company_invoice_upsert_missing_required_fields():
    with pytest.raises(ValidationError):
        InvoiceUpsertDTO(
            invoice_type=InvoiceType.COMPANY,
            company_name=" Company A ",
            street=" Grodzka ",
            postal_code=" 00-001 ",
            city=" Krakow ",
            country_code=" pl "
        )
