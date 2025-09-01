from sqlalchemy import Table, Column, Integer, CheckConstraint
from app.core.database import Base

invoice_counters = Table(
    "invoice_counters",
    Base.metadata,
    Column("fiscal_year", Integer, primary_key=True),
    Column("counter", Integer, nullable=False),
    CheckConstraint("counter >= 1", name="chk_invoice_counter_ge1"),
)
