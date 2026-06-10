"""Unit tests for Open-Meteo weather client."""

from __future__ import annotations

import copy
from datetime import datetime
from pathlib import Path

import httpx
import pytest
from zoneinfo import ZoneInfo

from assistant.config import (
    DEFAULT_LATITUDE,
    DEFAULT_LONGITUDE,
    DEFAULT_TIMEZONE,
    FORECAST_DAYS,
    HOURLY_WEATHER_VARIABLES,
    OPEN_METEO_FORECAST_URL,
    WIND_SPEED_UNIT,
)
from assistant.models import WeatherFetchError, WeatherHour
from assistant.weather_client import (
    build_forecast_params,
    fetch_hourly_forecast,
    parse_forecast_response,
)

HOUSTON = ZoneInfo("America/Chicago")


def _hourly_payload(
    *,
    times: list[str] | None = None,
    temperatures: list[object] | None = None,
    precipitation: list[object] | None = None,
    weather_codes: list[object] | None = None,
    wind_speeds: list[object] | None = None,
) -> dict[str, object]:
    resolved_times = (
        list(times)
        if times is not None
        else ["2026-06-10T09:00:00", "2026-06-10T10:00:00"]
    )
    count = len(resolved_times)

    if temperatures is None:
        temperatures = [28.0, 29][:count] if count else []
    if precipitation is None:
        precipitation = ([0.0, None] if count > 1 else [0.0])[:count]
    if weather_codes is None:
        weather_codes = [0, 61][:count] if count else []
    if wind_speeds is None:
        wind_speeds = [5.5, 6.0][:count] if count else []

    return {
        "hourly": {
            "time": resolved_times,
            "temperature_2m": temperatures,
            "precipitation": precipitation,
            "weather_code": weather_codes,
            "wind_speed_10m": wind_speeds,
        }
    }


def test_build_forecast_params_default_houston_latitude() -> None:
    params = build_forecast_params()
    assert params["latitude"] == 29.76


def test_build_forecast_params_default_longitude() -> None:
    params = build_forecast_params()
    assert params["longitude"] == -95.36


def test_build_forecast_params_timezone() -> None:
    params = build_forecast_params()
    assert params["timezone"] == "America/Chicago"


def test_build_forecast_params_forecast_days() -> None:
    params = build_forecast_params()
    assert params["forecast_days"] == 7


def test_build_forecast_params_hourly_variables() -> None:
    params = build_forecast_params()
    assert params["hourly"] == "temperature_2m,precipitation,weather_code,wind_speed_10m"


def test_build_forecast_params_wind_speed_unit() -> None:
    params = build_forecast_params()
    assert params["wind_speed_unit"] == "ms"


def test_build_forecast_params_custom_coordinates() -> None:
    params = build_forecast_params(latitude=30.0, longitude=-96.0)
    assert params["latitude"] == 30.0
    assert params["longitude"] == -96.0


def test_parse_valid_response_returns_tuple_of_weather_hour() -> None:
    hours = parse_forecast_response(_hourly_payload())
    assert isinstance(hours, tuple)
    assert all(isinstance(hour, WeatherHour) for hour in hours)


def test_parse_timestamps_are_timezone_aware_houston_datetimes() -> None:
    hours = parse_forecast_response(_hourly_payload())
    assert hours[0].timestamp == datetime(2026, 6, 10, 9, 0, 0, tzinfo=HOUSTON)
    assert hours[0].timestamp.tzinfo == HOUSTON


def test_parse_values_mapped_by_matching_array_index() -> None:
    hours = parse_forecast_response(_hourly_payload())
    assert hours[1].temperature_c == 29.0
    assert hours[1].precipitation_mm is None
    assert hours[1].weather_code == 61
    assert hours[1].wind_speed_ms == 6.0


def test_parse_integer_numeric_values_become_floats() -> None:
    hours = parse_forecast_response(_hourly_payload())
    assert hours[1].temperature_c == 29.0
    assert isinstance(hours[1].temperature_c, float)


def test_parse_weather_codes_become_ints() -> None:
    hours = parse_forecast_response(_hourly_payload())
    assert hours[1].weather_code == 61
    assert isinstance(hours[1].weather_code, int)


def test_parse_null_optional_values_become_none() -> None:
    hours = parse_forecast_response(_hourly_payload())
    assert hours[1].precipitation_mm is None


def test_parse_preserves_response_order() -> None:
    payload = _hourly_payload(
        times=["2026-06-10T08:00:00", "2026-06-10T09:00:00", "2026-06-10T10:00:00"],
        temperatures=[20.0, 21.0, 22.0],
        precipitation=[0.0, 0.0, 0.0],
        weather_codes=[0, 1, 2],
        wind_speeds=[1.0, 2.0, 3.0],
    )
    hours = parse_forecast_response(payload)
    assert [hour.weather_code for hour in hours] == [0, 1, 2]


def test_parse_wind_speed_remains_interpreted_as_ms() -> None:
    hours = parse_forecast_response(_hourly_payload())
    assert hours[0].wind_speed_ms == 5.5


def test_fetch_requests_expected_open_meteo_url() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["params"] = dict(request.url.params)
        return httpx.Response(200, json=_hourly_payload())

    transport = httpx.MockTransport(handler)
    fetch_hourly_forecast(transport=transport)
    assert str(captured["url"]).startswith(OPEN_METEO_FORECAST_URL)
    params = captured["params"]
    assert params["latitude"] == str(DEFAULT_LATITUDE)
    assert params["longitude"] == str(DEFAULT_LONGITUDE)
    assert params["timezone"] == DEFAULT_TIMEZONE
    assert params["forecast_days"] == str(FORECAST_DAYS)
    assert params["hourly"] == ",".join(HOURLY_WEATHER_VARIABLES)
    assert params["wind_speed_unit"] == WIND_SPEED_UNIT


def test_fetch_uses_injected_mock_transport() -> None:
    called = {"value": False}

    def handler(request: httpx.Request) -> httpx.Response:
        called["value"] = True
        return httpx.Response(200, json=_hourly_payload())

    transport = httpx.MockTransport(handler)
    fetch_hourly_forecast(transport=transport)
    assert called["value"] is True


def test_fetch_non_success_status_raises_weather_fetch_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": "unavailable"})

    transport = httpx.MockTransport(handler)
    with pytest.raises(WeatherFetchError, match="HTTP 503"):
        fetch_hourly_forecast(transport=transport)


def test_fetch_timeout_raises_weather_fetch_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("timed out")

    transport = httpx.MockTransport(handler)
    with pytest.raises(WeatherFetchError, match="timed out"):
        fetch_hourly_forecast(transport=transport)


def test_fetch_connection_failure_raises_weather_fetch_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection failed")

    transport = httpx.MockTransport(handler)
    with pytest.raises(WeatherFetchError, match="failed"):
        fetch_hourly_forecast(transport=transport)


def test_fetch_invalid_json_raises_weather_fetch_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not-json")

    transport = httpx.MockTransport(handler)
    with pytest.raises(WeatherFetchError, match="valid JSON"):
        fetch_hourly_forecast(transport=transport)


def test_parse_root_non_object_rejected() -> None:
    with pytest.raises(WeatherFetchError, match="root must be an object"):
        parse_forecast_response([])


def test_parse_missing_hourly_rejected() -> None:
    with pytest.raises(WeatherFetchError, match="missing required field 'hourly'"):
        parse_forecast_response({})


def test_parse_non_object_hourly_rejected() -> None:
    with pytest.raises(WeatherFetchError, match="'hourly' must be an object"):
        parse_forecast_response({"hourly": []})


@pytest.mark.parametrize(
    "missing_field",
    ["time", "temperature_2m", "precipitation", "weather_code", "wind_speed_10m"],
)
def test_parse_missing_hourly_field_rejected(missing_field: str) -> None:
    hourly = _hourly_payload()["hourly"]
    assert isinstance(hourly, dict)
    hourly = dict(hourly)
    del hourly[missing_field]
    with pytest.raises(WeatherFetchError, match=f"'{missing_field}' is required"):
        parse_forecast_response({"hourly": hourly})


@pytest.mark.parametrize(
    "invalid_field",
    ["time", "temperature_2m", "precipitation", "weather_code", "wind_speed_10m"],
)
def test_parse_non_list_hourly_field_rejected(invalid_field: str) -> None:
    hourly = dict(_hourly_payload()["hourly"])
    assert isinstance(hourly, dict)
    hourly[invalid_field] = "bad"
    with pytest.raises(WeatherFetchError, match=f"'{invalid_field}' must be a list"):
        parse_forecast_response({"hourly": hourly})


def test_parse_mismatched_array_lengths_rejected() -> None:
    payload = _hourly_payload()
    hourly = dict(payload["hourly"])
    assert isinstance(hourly, dict)
    hourly["precipitation"] = [0.0]
    with pytest.raises(WeatherFetchError, match="identical lengths"):
        parse_forecast_response({"hourly": hourly})


def test_parse_invalid_timestamp_rejected() -> None:
    payload = _hourly_payload(times=["not-a-time"])
    with pytest.raises(WeatherFetchError, match="invalid ISO 8601 timestamp"):
        parse_forecast_response(payload)


def test_parse_invalid_numeric_string_rejected() -> None:
    payload = _hourly_payload(
        times=["2026-06-10T09:00:00"],
        temperatures=["warm"],
    )
    with pytest.raises(WeatherFetchError, match="temperature_2m"):
        parse_forecast_response(payload)


def test_parse_boolean_weather_value_rejected() -> None:
    payload = _hourly_payload(temperatures=[True, 29])
    with pytest.raises(WeatherFetchError, match="temperature_2m"):
        parse_forecast_response(payload)


def test_parse_fractional_weather_code_rejected() -> None:
    payload = _hourly_payload(weather_codes=[61.5, 0])
    with pytest.raises(WeatherFetchError, match="weather_code"):
        parse_forecast_response(payload)


def test_parse_boolean_weather_code_rejected() -> None:
    payload = _hourly_payload(weather_codes=[True, 0])
    with pytest.raises(WeatherFetchError, match="weather_code"):
        parse_forecast_response(payload)


def test_parse_ambiguous_houston_timestamp_rejected() -> None:
    payload = _hourly_payload(times=["2026-11-01T01:30:00"])
    with pytest.raises(WeatherFetchError, match="ambiguous Houston local datetime"):
        parse_forecast_response(payload)


def test_parse_nonexistent_houston_timestamp_rejected() -> None:
    payload = _hourly_payload(times=["2026-03-08T02:30:00"])
    with pytest.raises(WeatherFetchError, match="nonexistent Houston local datetime"):
        parse_forecast_response(payload)


def test_parse_empty_hourly_arrays_return_empty_tuple() -> None:
    payload = _hourly_payload(times=[])
    hours = parse_forecast_response(payload)
    assert hours == ()


def test_parse_does_not_mutate_supplied_data() -> None:
    payload = _hourly_payload()
    original = copy.deepcopy(payload)
    parse_forecast_response(payload)
    assert payload == original


def test_source_does_not_import_forbidden_modules() -> None:
    import assistant.weather_client as weather_client

    source = Path(weather_client.__file__).read_text(encoding="utf-8")
    assert "rich" not in source.lower()
    assert "assistant.cli" not in source
    assert "calendar_loader" not in source
    assert "advice_engine" not in source


def test_source_does_not_contain_print_or_input() -> None:
    import assistant.weather_client as weather_client

    source = Path(weather_client.__file__).read_text(encoding="utf-8")
    assert "print(" not in source
    assert "input(" not in source


def test_source_uses_httpx_not_requests() -> None:
    import assistant.weather_client as weather_client

    source = Path(weather_client.__file__).read_text(encoding="utf-8")
    assert "httpx" in source
    assert "requests" not in source


def test_no_live_network_used() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_hourly_payload())

    transport = httpx.MockTransport(handler)
    hours = fetch_hourly_forecast(transport=transport)
    assert len(hours) == 2
