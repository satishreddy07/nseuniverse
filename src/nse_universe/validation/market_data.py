"""Dependency-free validation primitives for market data."""

from __future__ import annotations

import math
from datetime import datetime, timezone


def is_finite_number(value: object) -> bool:
    """Only finite int/float values count; booleans are not market numbers."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return math.isfinite(value)


def require_finite_number(value: object, *, field_name: str) -> float:
    if not is_finite_number(value):
        raise ValueError(f"{field_name} must be a finite number")
    return float(value)


def require_aware_datetime(value: datetime, *, field_name: str = "timestamp") -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return value


def to_utc(value: datetime, *, field_name: str = "timestamp") -> datetime:
    return require_aware_datetime(value, field_name=field_name).astimezone(timezone.utc)


def age_seconds(observed_at: datetime, *, now: datetime) -> float:
    age = (to_utc(now, field_name="now") - to_utc(observed_at, field_name="observed_at")).total_seconds()
    if age < 0:
        raise ValueError("observed_at cannot be in the future relative to now")
    return age


def is_fresh(observed_at: datetime, *, now: datetime, max_age_seconds: float) -> bool:
    limit = require_finite_number(max_age_seconds, field_name="max_age_seconds")
    if limit < 0:
        raise ValueError("max_age_seconds must be non-negative")
    return age_seconds(observed_at, now=now) <= limit
