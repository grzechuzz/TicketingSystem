from typing import Generic, TypeVar
from pydantic import BaseModel, computed_field
from sqlalchemy import select, func
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession


T = TypeVar("T")


class PageDTO(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int

    @computed_field
    @property
    def pages(self) -> int:
        if self.page_size <= 0:
            return 1
        return max(1, (self.total + self.page_size - 1) // self.page_size)

    @computed_field
    @property
    def has_next(self) -> bool:
        return self.page < self.pages


async def paginate(
        db: AsyncSession,
        base_stmt,
        *,
        page: int = 1,
        page_size: int = 20,
        where: list[Any] | None = None,
        order_by: list[Any] | None = None,
        distinct_on: Any | None = None,
        scalars: bool = True,
        count_by: Any | None = None
):
    page = max(1, int(page))
    page_size = max(1, min(200, int(page_size)))

    stmt = base_stmt
    if where:
        stmt = stmt.where(*where)

    if distinct_on:
        stmt = stmt.distinct(*distinct_on)
        if order_by:
            stmt = stmt.order_by(*distinct_on, *order_by)
        else:
            stmt = stmt.order_by(*distinct_on)
    elif order_by:
        stmt = stmt.order_by(*order_by)

    if count_by is not None:
        count_stmt = stmt.with_only_columns(count_by).order_by(None).distinct()
        total = await db.scalar(select(func.count()).select_from(count_stmt.subquery()))
    else:
        total_subquery = stmt.order_by(None).limit(None).offset(None)
        total = await db.scalar(select(func.count()).select_from(total_subquery.subquery()))

    stmt = stmt.limit(page_size).offset((page - 1) * page_size)

    if scalars:
        result = await db.scalars(stmt)
    else:
        result = await db.execute(stmt)

    items = result.all()
    return items, int(total or 0)
