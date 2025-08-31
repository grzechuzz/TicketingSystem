from typing import Generic, TypeVar
from pydantic import BaseModel, computed_field

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
        return self.page < self.total
