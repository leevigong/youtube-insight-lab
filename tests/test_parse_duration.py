import pytest
from app.services.youtube import parse_duration


@pytest.mark.parametrize("duration, expected", [
    ("PT15M33S", 933), ("PT1H2M3S", 3723), ("PT30S", 30),
    ("PT10M", 600), ("PT1H", 3600), ("PT0S", 0),
    ("PT1H30M", 5400), ("", 0), ("INVALID", 0),
])
def test_parse_duration(duration: str, expected: int):
    assert parse_duration(duration) == expected
