"""Load and validate calendar events from JSON."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from assistant.config import DEFAULT_TIMEZONE
from assistant.models import CalendarError, CalendarEvent

_REQUIRED_EVENT_FIELDS: frozenset[str] = frozenset({"title", "start", "end", "location"})
_HOUSTON_TZ = ZoneInfo(DEFAULT_TIMEZONE)


def load_calendar(path: str | Path) -> tuple[CalendarEvent, ...]:
    """Read UTF-8 JSON from ``path`` and return validated calendar events."""
    calendar_path = Path(path)
    try:
        text = calendar_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise CalendarError(f"Calendar file not found: {calendar_path}") from exc
    except UnicodeDecodeError as exc:
        raise CalendarError(f"Calendar file is not valid UTF-8: {calendar_path}") from exc
    except OSError as exc:
        raise CalendarError(f"Unable to read calendar file: {calendar_path}") from exc

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise CalendarError(f"Invalid JSON in calendar file: {calendar_path}") from exc

    return parse_calendar_data(data)


def parse_calendar_data(data: object) -> tuple[CalendarEvent, ...]:
    """Validate a parsed JSON value and return sorted calendar events."""
    if not isinstance(data, dict):
        raise CalendarError("Calendar root must be an object.")

    if "events" not in data:
        raise CalendarError("Calendar root is missing required field 'events'.")

    events = data["events"]
    if not isinstance(events, list):
        raise CalendarError("Calendar field 'events' must be a list.")

    parsed = tuple(parse_event(raw_event, event_index) for event_index, raw_event in enumerate(events))
    return tuple(sorted(parsed, key=lambda event: event.start))


def parse_event(raw_event: object, event_index: int) -> CalendarEvent:
    """Validate one raw event object and return a ``CalendarEvent``."""
    if not isinstance(raw_event, dict):
        raise CalendarError(f"Event {event_index}: event must be an object.")

    keys = set(raw_event.keys())
    missing = _REQUIRED_EVENT_FIELDS - keys
    if missing:
        missing_fields = ", ".join(f"'{field}'" for field in sorted(missing))
        raise CalendarError(f"Event {event_index}: missing required field(s): {missing_fields}.")

    extra = keys - _REQUIRED_EVENT_FIELDS
    if extra:
        extra_fields = ", ".join(f"'{field}'" for field in sorted(extra))
        raise CalendarError(f"Event {event_index}: unexpected field(s): {extra_fields}.")

    title = raw_event["title"]
    if not isinstance(title, str):
        raise CalendarError(f"Event {event_index}: field 'title' must be a string.")
    if not title.strip():
        raise CalendarError(f"Event {event_index}: field 'title' must be a non-empty string.")

    location = raw_event["location"]
    if not isinstance(location, str):
        raise CalendarError(f"Event {event_index}: field 'location' must be a string.")

    start = parse_local_datetime(
        raw_event["start"],
        field_name="start",
        event_index=event_index,
    )
    end = parse_local_datetime(
        raw_event["end"],
        field_name="end",
        event_index=event_index,
    )
    if end <= start:
        raise CalendarError(
            f"Event {event_index}: field 'end' must be strictly after field 'start'."
        )

    return CalendarEvent(title=title, start=start, end=end, location=location)


def parse_local_datetime(
    value: object,
    *,
    field_name: str,
    event_index: int,
) -> datetime:
    """Parse an ISO 8601 datetime string into Houston-local aware time."""
    if not isinstance(value, str):
        raise CalendarError(
            f"Event {event_index}: field '{field_name}' must be an ISO 8601 string."
        )

    raw_value = value.strip()
    if not raw_value:
        raise CalendarError(
            f"Event {event_index}: field '{field_name}' must be an ISO 8601 string."
        )

    try:
        if raw_value.endswith("Z"):
            parsed = datetime.fromisoformat(raw_value[:-1] + "+00:00")
            return parsed.astimezone(_HOUSTON_TZ)

        parsed = datetime.fromisoformat(raw_value)
    except ValueError as exc:
        raise CalendarError(
            f"Event {event_index}: field '{field_name}' has invalid ISO 8601 datetime: {value!r}."
        ) from exc

    if parsed.tzinfo is None:
        return _localize_naive_houston(
            parsed,
            field_name=field_name,
            event_index=event_index,
        )

    return parsed.astimezone(_HOUSTON_TZ)


def _localize_naive_houston(
    naive: datetime,
    *,
    field_name: str,
    event_index: int,
) -> datetime:
    """Attach Houston timezone to a naive datetime with DST validation."""
    aware_fold0 = naive.replace(tzinfo=_HOUSTON_TZ, fold=0)
    aware_fold1 = naive.replace(tzinfo=_HOUSTON_TZ, fold=1)
    offset_fold0 = aware_fold0.utcoffset()
    offset_fold1 = aware_fold1.utcoffset()

    if offset_fold0 != offset_fold1:
        if offset_fold0 is not None and offset_fold1 is not None and offset_fold0 < offset_fold1:
            raise CalendarError(
                f"Event {event_index}: field '{field_name}' is a nonexistent Houston local datetime: {naive.isoformat()}."
            )
        raise CalendarError(
            f"Event {event_index}: field '{field_name}' is an ambiguous Houston local datetime: {naive.isoformat()}."
        )

    round_trip = aware_fold0.astimezone(_HOUSTON_TZ).replace(tzinfo=None)
    if round_trip != naive:
        raise CalendarError(
            f"Event {event_index}: field '{field_name}' is a nonexistent Houston local datetime: {naive.isoformat()}."
        )

    return aware_fold0
