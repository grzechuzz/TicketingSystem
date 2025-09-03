import pytest
from app.core.text_utils import strip_text


@pytest.mark.parametrize(
    "test, expected",
    [
        (" Angel ", "Angel"),
        ("", None),
        ("   ", None),
        ("\t \n", None),
        (None, None),
        ("  FC   Barcelona  ", "FC   Barcelona"),
        ("\u00A0test\u00A0", "test")
    ]
)
def test_text_utils(test, expected):
    assert strip_text(test) == expected
