import pytest
from app.core.pagination import PageDTO


@pytest.mark.parametrize(
    "total, page_size, expected_pages",
    [
        (0, 10, 1),
        (10, 10, 1),
        (1, 10, 1),
        (0, 0, 1),
        (11, 10, 2),
        (20, 10, 2),
        (5, 2, 3),
        (100, -5, 1)
    ]
)
def test_pages_calculation(total, page_size, expected_pages):
    dto = PageDTO(items=[], total=total, page=1, page_size=page_size)
    assert dto.pages == expected_pages


@pytest.mark.parametrize(
    "total, page_size, page, expected_has_next",
    [
        (0, 10, 1, False),
        (10, 10, 1, False),
        (11, 10, 1, True),
        (11, 10, 2, False),
        (21, 10, 1, True),
        (21, 10, 3, False),
        (21, 0, 1, False),
        (21, 10, 5, False),
    ]
)
def test_has_next(total, page_size, page, expected_has_next):
    dto = PageDTO(items=[], total=total, page=page, page_size=page_size)
    assert dto.has_next == expected_has_next
