"""Unit tests for calendar loading and validation."""

from __future__ import annotations

import copy
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from assistant.calendar_loader import (
    load_calendar,
    parse_calendar_data,
    parse_event,
    parse_local_datetime,
)
from assistant.models import CalendarError, CalendarEvent

HOUSTON = ZoneInfo("America/Chicago")


def _event_dict(
    *,
    title: str = "Team Standup",
    start: str = "2026-06-10T09:00:00",
    end: str = "2026-06-10T09:30:00",
    location: str = "Office Building A, Houston",
) -> dict[str, str]:
    return {
        "title": title,
        "start": start,
        "end": end,
        "location": location,
    }


def _calendar_dict(*events: dict[str, str]) -> dict[str, list[dict[str, str]]]:
    return {"events": list(events)}


def _write_calendar(path: Path, data: dict[str, object]) -> None:
    import json

    path.write_text(json.dumps(data), encoding="utf-8")


def test_load_valid_calendar_from_utf8_file(tmp_path: Path) -> None:
    calendar_path = tmp_path / "calendar.json"
    _write_calendar(calendar_path, _calendar_dict(_event_dict()))
    events = load_calendar(calendar_path)
    assert len(events) == 1
    assert events[0].title == "Team Standup"


def test_events_returned_as_tuple(tmp_path: Path) -> None:
    calendar_path = tmp_path / "calendar.json"
    _write_calendar(calendar_path, _calendar_dict(_event_dict()))
    events = load_calendar(calendar_path)
    assert isinstance(events, tuple)


def test_events_sorted_by_start() -> None:
    later = _event_dict(title="Later", start="2026-06-11T10:00:00", end="2026-06-11T11:00:00")
    earlier = _event_dict(title="Earlier", start="2026-06-10T10:00:00", end="2026-06-10T11:00:00")
    events = parse_calendar_data(_calendar_dict(later, earlier))
    assert [event.title for event in events] == ["Earlier", "Later"]


def test_parse_naive_houston_local_datetime() -> None:
    parsed = parse_local_datetime("2026-06-10T09:00:00", field_name="start", event_index=0)
    assert parsed == datetime(2026, 6, 10, 9, 0, 0, tzinfo=HOUSTON)
    assert parsed.tzinfo == HOUSTON


def test_parse_explicit_offset_converted_to_houston() -> None:
    parsed = parse_local_datetime(
        "2026-06-10T15:00:00-04:00",
        field_name="start",
        event_index=0,
    )
    assert parsed.tzinfo == HOUSTON
    assert parsed == datetime(2026, 6, 10, 14, 0, 0, tzinfo=HOUSTON)


def test_parse_trailing_z_converted_from_utc() -> None:
    parsed = parse_local_datetime("2026-06-10T14:00:00Z", field_name="start", event_index=0)
    assert parsed.tzinfo == HOUSTON
    assert parsed == datetime(2026, 6, 10, 9, 0, 0, tzinfo=HOUSTON)


def test_empty_events_list_accepted() -> None:
    events = parse_calendar_data({"events": []})
    assert events == ()


def test_missing_file_raises_calendar_error(tmp_path: Path) -> None:
    with pytest.raises(CalendarError, match="not found"):
        load_calendar(tmp_path / "missing.json")


def test_invalid_utf8_raises_calendar_error(tmp_path: Path) -> None:
    calendar_path = tmp_path / "calendar.json"
    calendar_path.write_bytes(b"\xff\xfe")
    with pytest.raises(CalendarError, match="UTF-8"):
        load_calendar(calendar_path)


def test_malformed_json_raises_calendar_error(tmp_path: Path) -> None:
    calendar_path = tmp_path / "calendar.json"
    calendar_path.write_text("{not json", encoding="utf-8")
    with pytest.raises(CalendarError, match="Invalid JSON"):
        load_calendar(calendar_path)


def test_root_list_rejected() -> None:
    with pytest.raises(CalendarError, match="root must be an object"):
        parse_calendar_data([])


def test_missing_events_rejected() -> None:
    with pytest.raises(CalendarError, match="missing required field 'events'"):
        parse_calendar_data({})


def test_non_list_events_rejected() -> None:
    with pytest.raises(CalendarError, match="'events' must be a list"):
        parse_calendar_data({"events": {}})


def test_non_object_event_rejected() -> None:
    with pytest.raises(CalendarError, match="Event 0: event must be an object"):
        parse_calendar_data({"events": ["bad"]})


@pytest.mark.parametrize("missing_field", ["title", "start", "end", "location"])
def test_missing_required_field_rejected(missing_field: str) -> None:
    event = _event_dict()
    del event[missing_field]
    with pytest.raises(CalendarError, match=f"Event 0: missing required field"):
        parse_calendar_data({"events": [event]})


def test_extra_field_rejected() -> None:
    event = _event_dict()
    event["notes"] = "unexpected"
    with pytest.raises(CalendarError, match="Event 0: unexpected field"):
        parse_calendar_data({"events": [event]})


def test_non_string_title_rejected() -> None:
    event = _event_dict()
    event["title"] = 123
    with pytest.raises(CalendarError, match="Event 0: field 'title' must be a string"):
        parse_calendar_data({"events": [event]})


def test_non_string_start_rejected() -> None:
    event = _event_dict()
    event["start"] = 123
    with pytest.raises(CalendarError, match="Event 0: field 'start' must be an ISO 8601 string"):
        parse_calendar_data({"events": [event]})


def test_non_string_end_rejected() -> None:
    event = _event_dict()
    event["end"] = 123
    with pytest.raises(CalendarError, match="Event 0: field 'end' must be an ISO 8601 string"):
        parse_calendar_data({"events": [event]})


def test_non_string_location_rejected() -> None:
    event = _event_dict()
    event["location"] = 123
    with pytest.raises(CalendarError, match="Event 0: field 'location' must be a string"):
        parse_calendar_data({"events": [event]})


def test_invalid_iso_datetime_rejected() -> None:
    with pytest.raises(CalendarError, match="Event 0: field 'start' has invalid ISO 8601 datetime"):
        parse_local_datetime("not-a-datetime", field_name="start", event_index=0)


def test_end_equal_to_start_rejected() -> None:
    event = _event_dict(start="2026-06-10T09:00:00", end="2026-06-10T09:00:00")
    with pytest.raises(CalendarError, match="Event 0: field 'end' must be strictly after field 'start'"):
        parse_event(event, 0)


def test_end_before_start_rejected() -> None:
    event = _event_dict(start="2026-06-10T10:00:00", end="2026-06-10T09:00:00")
    with pytest.raises(CalendarError, match="Event 0: field 'end' must be strictly after field 'start'"):
        parse_event(event, 0)


def test_spring_forward_nonexistent_local_time_rejected() -> None:
    with pytest.raises(CalendarError, match="Event 1: field 'start' is a nonexistent Houston local datetime"):
        parse_local_datetime("2026-03-08T02:30:00", field_name="start", event_index=1)


def test_fall_back_ambiguous_naive_local_time_rejected() -> None:
    with pytest.raises(CalendarError, match="Event 2: field 'start' is an ambiguous Houston local datetime"):
        parse_local_datetime("2026-11-01T01:30:00", field_name="start", event_index=2)


def test_fall_back_explicit_offset_accepted() -> None:
    parsed = parse_local_datetime(
        "2026-11-01T01:30:00-05:00",
        field_name="start",
        event_index=0,
    )
    assert parsed.tzinfo == HOUSTON
    assert parsed.utcoffset() is not None


def test_error_message_includes_event_index_and_field_name() -> None:
    with pytest.raises(CalendarError, match="Event 3: field 'end' has invalid ISO 8601 datetime"):
        parse_local_datetime("bad-end", field_name="end", event_index=3)


def test_parse_calendar_data_does_not_mutate_input_dictionary() -> None:
    data = _calendar_dict(_event_dict())
    original = copy.deepcopy(data)
    parse_calendar_data(data)
    assert data == original


def test_no_network_use() -> None:
    import assistant.calendar_loader as calendar_loader

    source = Path(calendar_loader.__file__).read_text(encoding="utf-8")
    assert "httpx" not in source
    assert "requests" not in source
    assert "urllib" not in source
    assert "socket" not in source


def test_parse_event_returns_calendar_event() -> None:
    event = parse_event(_event_dict(), 0)
    assert isinstance(event, CalendarEvent)
