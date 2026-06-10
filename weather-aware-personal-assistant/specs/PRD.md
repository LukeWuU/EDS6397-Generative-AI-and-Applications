# Product Requirements Document - Weather-Aware Personal Assistant

## Problem

Students and professionals need quick, practical guidance about upcoming calendar events without manually checking weather apps. A lightweight terminal assistant can combine local schedule data with live forecasts and produce actionable advice.

## Intended User

A single local user running a Python CLI on their machine who maintains a simple `calendar.json` file and wants Houston-area weather context for upcoming events.

## Goals

- Provide a REPL-based personal assistant that reads local calendar events.
- Fetch live hourly weather from Open-Meteo without an API key.
- Generate deterministic, rule-based advice from weather and event context.
- Keep weather retrieval, calendar loading, advice logic, formatting, and CLI interaction modular and testable.

## Non-Goals

- No large language model (LLM) or generative AI for advice.
- No geocoding or per-event coordinate lookup.
- No user accounts, persistence beyond `calendar.json`, or web UI.
- No `requests` library; HTTP uses `httpx` only.
- No multi-city weather support or external deployment claims.

## Functional Requirements

### Calendar

- Read `calendar.json` from the project root (override via `ASSISTANT_CALENDAR_PATH`).
- **Schema:** root object with an `events` array. Each event requires:

| Field | Type | Notes |
|-------|------|-------|
| `title` | string | Human-readable event name |
| `start` | string | Naive ISO 8601 datetime (e.g. `2026-06-10T09:00:00`) |
| `end` | string | Naive ISO 8601 datetime; must be strictly after `start` |
| `location` | string | Free text; used for advice heuristics (physical, online, travel) |

Example:

```json
{
  "events": [
    {
      "title": "Team Standup",
      "start": "2026-06-10T09:00:00",
      "end": "2026-06-10T09:30:00",
      "location": "Office Building A, Houston"
    }
  ]
}
```

- Strict validation: one invalid event fails the entire load with index and field details.
- **Time policy:** naive ISO datetimes are interpreted as Houston local time (`America/Chicago`).
- Return events sorted by `start`.

### Weather

- **Default location:** latitude **29.76**, longitude **-95.36** (Houston, Texas). All events share this forecast; `location` text does not change coordinates.
- Use Open-Meteo `GET /v1/forecast` with `timezone=America/Chicago`.
- Request hourly `temperature_2m`, `precipitation`, `weather_code`, `wind_speed_10m`.
- **Wind-speed unit contract:** always pass `wind_speed_unit=ms`. Parsed wind values are meters per second.
- Match event windows as half-open intervals **`[start, end)`** against hourly buckets.
- Aggregate worst-case conditions across overlapping hours: maximum precipitation, maximum wind, minimum and maximum temperature, and highest-severity WMO weather code.

### Advice (Rule-Based, No LLM)

Pure functions accept structured weather and event data; no I/O inside the advice engine.

| Priority | rule_id | Condition |
|----------|---------|-----------|
| 0 | `forecast_unavailable` | No overlapping hourly forecast |
| 1 | `severe_weather` | WMO code in `{65, 82, 95, 96, 99}` |
| 2 | `rain_travel` | Rain detected + travel-class location |
| 3 | `rain_gear` | Rain detected + non-travel, non-online location |
| 4 | `extreme_heat` | `max_temperature_c >= 35.0` |
| 5 | `cold_weather` | `min_temperature_c <= 5.0` |
| 6 | `strong_wind` | `max_wind_speed_ms >= 14.0` |
| 7 | `normal` | No rules 1-6 matched |

**Rain detection thresholds:**

- Precipitation `>= 0.1` mm in any overlapping hour, **and/or**
- WMO weather code in `{51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82}`.

**Location heuristics:**

- **Online/remote:** location text matches online keywords (e.g. `Online`, `Zoom`, `Remote`). Rain advice must not recommend public transit.
- **Travel:** location text indicates commuting or transit (e.g. `Metro`, `Bus`, `Transit`, `Airport`, `Commute`). Rain triggers bus/transit + umbrella advice.
- **Physical:** all other locations. Rain triggers umbrella/gear advice only.

**Combination rules:**

- `forecast_unavailable` blocks all other rules.
- `rain_travel` and `rain_gear` are mutually exclusive.
- Multiple applicable rules output sorted by priority, then `rule_id`.

### REPL Commands

| Command | Behavior |
|---------|----------|
| `help` | List commands and brief descriptions |
| `events` | Show validated calendar events |
| `weather` | Show Houston hourly forecast |
| `advice` | Weather-aware advice per event |
| `reload` | Reload calendar and refetch weather |
| `quit` / `exit` | Exit gracefully |

Unknown commands show a helpful message without terminating the REPL.

## Non-Functional Requirements

- Python 3.10+
- Runtime dependencies: `httpx` and `rich`; `pytest` for dev.
- On Windows, include conditional runtime dependency `tzdata; platform_system == 'Windows'` so `America/Chicago` IANA timezone data is available at install time.
- Rich confined to CLI/presentation layer only.
- Core modules must not import CLI or Rich.
- Network failures produce controlled errors, not tracebacks.
- Never substitute current weather for events outside forecast range.
- Unit tests deterministic; no live network in tests.

## Missing-Data Policy

| Scenario | Behavior |
|----------|----------|
| No hourly overlap with event window | `forecast_unavailable` advice only |
| Partial overlap | Aggregate using overlapping hours only |
| Missing optional forecast fields | Skip rules that require the missing field |
| Network failure | Raise `WeatherFetchError`; REPL continues |
| Invalid calendar JSON or event | Raise `CalendarError` with event index and field |

## Success Criteria

- All REPL commands work as specified.
- Advice includes bus + umbrella for rainy travel events in automated tests.
- Online events in rain do not receive bus advice in automated tests.
- `pytest -q` passes with full test-plan coverage.
- Architecture separates core logic from CLI presentation.

## Acceptance Criteria

- [x] `python -m assistant` launches REPL
- [x] `events`, `weather`, `advice`, `reload`, `help`, `quit`/`exit` behave per spec
- [x] Wind speeds interpreted as m/s with `wind_speed_unit=ms` on every request
- [x] Advice engine has no I/O (verified by AST and capsys tests)
- [x] Event windows use half-open `[start, end)` matching
- [x] Rain travel advice includes bus/public transit and umbrella in automated tests
- [x] Online event exclusion works in automated tests
- [x] Full test suite passes (`305 passed in 1.06s`)
- [x] README, PRD, and `docs/rules.md` align with implementation
