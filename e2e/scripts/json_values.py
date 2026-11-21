"""
The JSON values the e2e log scripts read: the stack's structured log lines,
and Jaeger's query responses.
"""

from typing import Union

# A decoded JSON value. Union, not |: the scripts run on the host's python3, whose floor is 3.9.
JSON = Union[dict[str, "JSON"], list["JSON"], str, int, float, bool, None]


def json_objects(value: JSON) -> list[dict[str, JSON]]:
    """The objects in ``value`` where it is an array."""
    if not isinstance(value, list):
        return []
    return [each for each in value if isinstance(each, dict)]


def json_text(entry: dict[str, JSON], key: str) -> str:
    """The string ``entry`` holds at ``key``, or "" where it holds none."""
    value = entry.get(key)
    return value if isinstance(value, str) else ""
