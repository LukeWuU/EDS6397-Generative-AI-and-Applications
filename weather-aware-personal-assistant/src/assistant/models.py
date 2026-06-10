"""Immutable domain models for calendar events, weather, and advice."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class AssistantError(Exception):
    """Base exception for assistant application errors."""


class CalendarError(AssistantError):
    """Raised when calendar data is invalid or cannot be loaded."""


class WeatherFetchError(AssistantError):
    """Raised when weather data cannot be fetched or parsed."""


@dataclass(frozen=True)
class CalendarEvent:
    """A scheduled event with timezone-aware start and end times."""

    title: str
    start: datetime
    end: datetime
    location: str

    def __post_init__(self) -> None:
        if not isinstance(self.title, str) or not self.title.strip():
            raise CalendarError("Event title must be a non-empty string.")
        if not isinstance(self.location, str):
            raise CalendarError("Event location must be a string.")
        if not isinstance(self.start, datetime):
            raise CalendarError("Event start must be a datetime instance.")
        if not isinstance(self.end, datetime):
            raise CalendarError("Event end must be a datetime instance.")
        if self.start.tzinfo is None or self.start.tzinfo.utcoffset(self.start) is None:
            raise CalendarError("Event start datetime must be timezone-aware.")
        if self.end.tzinfo is None or self.end.tzinfo.utcoffset(self.end) is None:
            raise CalendarError("Event end datetime must be timezone-aware.")
        if self.end <= self.start:
            raise CalendarError("Event end must be strictly after start.")


@dataclass(frozen=True)
class WeatherHour:
    """Hourly forecast values; wind_speed_ms is meters per second."""

    timestamp: datetime
    temperature_c: float | None
    precipitation_mm: float | None
    weather_code: int | None
    wind_speed_ms: float | None

    def __post_init__(self) -> None:
        if not isinstance(self.timestamp, datetime):
            raise TypeError("WeatherHour timestamp must be a datetime instance.")
        if self.timestamp.tzinfo is None or self.timestamp.tzinfo.utcoffset(self.timestamp) is None:
            raise ValueError("WeatherHour timestamp must be timezone-aware.")


class ForecastStatus(Enum):
    """Availability of forecast data for an event window."""

    AVAILABLE = "available"
    FORECAST_UNAVAILABLE = "forecast_unavailable"


@dataclass(frozen=True)
class EventWeatherSummary:
    """Aggregated weather across hours overlapping an event window."""

    status: ForecastStatus
    overlapping_hours: tuple[WeatherHour, ...]
    min_temperature_c: float | None
    max_temperature_c: float | None
    max_precipitation_mm: float | None
    max_wind_speed_ms: float | None
    worst_weather_code: int | None

    @property
    def has_temperature_data(self) -> bool:
        return self.min_temperature_c is not None or self.max_temperature_c is not None

    @property
    def has_precipitation_data(self) -> bool:
        return self.max_precipitation_mm is not None

    @property
    def has_wind_data(self) -> bool:
        return self.max_wind_speed_ms is not None

    @property
    def has_weather_code_data(self) -> bool:
        return self.worst_weather_code is not None

    def __post_init__(self) -> None:
        if not isinstance(self.overlapping_hours, tuple):
            raise TypeError("EventWeatherSummary overlapping_hours must be a tuple.")
        for hour in self.overlapping_hours:
            if not isinstance(hour, WeatherHour):
                raise TypeError(
                    "EventWeatherSummary overlapping_hours must contain WeatherHour instances."
                )


@dataclass(frozen=True)
class AdviceItem:
    """A single rule-based advice message for an event."""

    priority: int
    category: str
    message: str
    rule_id: str


@dataclass(frozen=True)
class AdviceBundle:
    """Advice items produced for one event and its weather summary."""

    event: CalendarEvent
    summary: EventWeatherSummary
    items: tuple[AdviceItem, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.items, tuple):
            raise TypeError("AdviceBundle items must be a tuple.")
        for item in self.items:
            if not isinstance(item, AdviceItem):
                raise TypeError("AdviceBundle items must contain AdviceItem instances.")
