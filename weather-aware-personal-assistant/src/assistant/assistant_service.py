"""Application service orchestration for calendar, weather, and advice."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from assistant.advice_engine import generate_advice
from assistant.calendar_loader import load_calendar
from assistant.config import DEFAULT_CALENDAR_PATH
from assistant.models import (
    AdviceBundle,
    CalendarEvent,
    EventWeatherSummary,
    WeatherHour,
)
from assistant.weather_client import fetch_hourly_forecast
from assistant.weather_window import summarize_event_weather

LoadCalendarFn = Callable[[str | Path], tuple[CalendarEvent, ...]]
FetchWeatherFn = Callable[..., tuple[WeatherHour, ...]]
SummarizeWeatherFn = Callable[
    [CalendarEvent, tuple[WeatherHour, ...]],
    EventWeatherSummary,
]
GenerateAdviceFn = Callable[[CalendarEvent, EventWeatherSummary], AdviceBundle]


class AssistantService:
    """Coordinate calendar loading, weather retrieval, and advice generation."""

    def __init__(
        self,
        *,
        calendar_path: str | Path = DEFAULT_CALENDAR_PATH,
        load_calendar_fn: LoadCalendarFn = load_calendar,
        fetch_weather_fn: FetchWeatherFn = fetch_hourly_forecast,
        summarize_weather_fn: SummarizeWeatherFn = summarize_event_weather,
        generate_advice_fn: GenerateAdviceFn = generate_advice,
    ) -> None:
        self._calendar_path = Path(calendar_path)
        self._load_calendar_fn = load_calendar_fn
        self._fetch_weather_fn = fetch_weather_fn
        self._summarize_weather_fn = summarize_weather_fn
        self._generate_advice_fn = generate_advice_fn
        self._events: tuple[CalendarEvent, ...] = ()
        self._weather_hours: tuple[WeatherHour, ...] = ()

    @property
    def events(self) -> tuple[CalendarEvent, ...]:
        """Return the most recently loaded calendar events."""
        return self._events

    @property
    def weather_hours(self) -> tuple[WeatherHour, ...]:
        """Return the most recently fetched weather hours."""
        return self._weather_hours

    def load_events(self) -> tuple[CalendarEvent, ...]:
        """Load calendar events from the configured path."""
        events = self._load_calendar_fn(self._calendar_path)
        _validate_events_tuple(events)
        self._events = events
        return events

    def fetch_weather(self) -> tuple[WeatherHour, ...]:
        """Fetch hourly weather using the injected fetcher."""
        weather_hours = self._fetch_weather_fn()
        _validate_weather_hours_tuple(weather_hours)
        self._weather_hours = weather_hours
        return weather_hours

    def reload(self) -> tuple[CalendarEvent, ...]:
        """Reload calendar events and weather atomically."""
        new_events = self._load_calendar_fn(self._calendar_path)
        _validate_events_tuple(new_events)

        new_weather = self._fetch_weather_fn()
        _validate_weather_hours_tuple(new_weather)

        self._events = new_events
        self._weather_hours = new_weather
        return new_events

    def initialize(self) -> None:
        """Load calendar events and weather."""
        self.reload()

    def advice_for_event(self, event: CalendarEvent) -> AdviceBundle:
        """Generate advice for one event using cached weather."""
        if not isinstance(event, CalendarEvent):
            raise TypeError("event must be a CalendarEvent instance.")

        summary = self._summarize_weather_fn(event, self._weather_hours)
        if not isinstance(summary, EventWeatherSummary):
            raise TypeError("summarize_weather_fn must return an EventWeatherSummary.")

        bundle = self._generate_advice_fn(event, summary)
        if not isinstance(bundle, AdviceBundle):
            raise TypeError("generate_advice_fn must return an AdviceBundle.")

        return bundle

    def advice_for_all_events(self) -> tuple[AdviceBundle, ...]:
        """Generate advice for all cached events in stored order."""
        return tuple(self.advice_for_event(event) for event in self._events)


def create_default_service() -> AssistantService:
    """Return a service configured with the approved default dependencies."""
    return AssistantService()


def _validate_events_tuple(events: object) -> None:
    if not isinstance(events, tuple):
        raise TypeError("load_calendar_fn must return a tuple.")
    for event in events:
        if not isinstance(event, CalendarEvent):
            raise TypeError("load_calendar_fn must return CalendarEvent instances.")


def _validate_weather_hours_tuple(weather_hours: object) -> None:
    if not isinstance(weather_hours, tuple):
        raise TypeError("fetch_weather_fn must return a tuple.")
    for hour in weather_hours:
        if not isinstance(hour, WeatherHour):
            raise TypeError("fetch_weather_fn must return WeatherHour instances.")
