"""Validation shared by endpoint clients."""

from math import isfinite


def is_finite_number(value: object) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return isfinite(value)
    except OverflowError:
        return False


def validate_coordinates(place: tuple[float, float], name: str) -> None:
    if not isinstance(place, tuple) or len(place) != 2:
        raise ValueError(f"{name} must be a (latitude, longitude) tuple")
    if not all(is_finite_number(coord) for coord in place):
        raise ValueError(f"{name} coordinates must be finite numbers")
    if not (-90 <= place[0] <= 90 and -180 <= place[1] <= 180):
        raise ValueError(f"{name} latitude must be within [-90, 90] and longitude within [-180, 180]")
