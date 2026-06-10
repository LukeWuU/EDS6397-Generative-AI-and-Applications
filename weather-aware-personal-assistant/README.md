# Weather-Aware Personal Assistant

**Phase 1 status:** This project is currently at the scaffolding and documentation stage. The REPL, weather fetching, advice engine, and automated tests are **not implemented yet**. The sections below describe **planned behavior** for later phases.

A modular Python CLI REPL that will read local calendar events, fetch Houston hourly weather from [Open-Meteo](https://open-meteo.com/), and produce **deterministic, rule-based** advice - no LLM required.

## Setup

Requires **Python 3.10+**.

Runtime dependencies are `httpx` and `rich`. On Windows, `pyproject.toml` also declares a conditional runtime dependency, `tzdata; platform_system == 'Windows'`, so `America/Chicago` IANA timezone support is available when the package is installed.

```bash
cd weather-aware-personal-assistant
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux
pip install -e ".[dev]"
```

## Planned Run (not yet implemented)

In a later phase, this command will launch the interactive REPL:

```bash
python -m assistant
```

Today, `python -m assistant` prints a placeholder message only.

### Planned REPL Commands

| Command | Planned description |
|---------|---------------------|
| `help` | Show available commands |
| `events` | List validated calendar events |
| `weather` | Houston hourly forecast (next 24 hours) |
| `advice` | Weather-aware advice for each event |
| `reload` | Reload `calendar.json` and refetch weather |
| `quit` / `exit` | Exit the assistant |

### Planned Example Session

```text
assistant> help
assistant> events
assistant> weather
assistant> advice
assistant> quit
```

## Planned Testing (not yet implemented)

In a later phase, this command will run the automated test suite:

```bash
pytest -q
```

The test plan calls for injected weather data and no live network access in unit tests. No test modules exist yet.

## Planned Architecture

```text
CLI (repl.py, formatter.py)  -- Rich presentation only
        |
assistant_service.py         -- orchestration
        |
calendar_loader.py  weather_client.py  weather_window.py  advice_engine.py
        |
models.py, config.py
```

Dependency direction: `CLI -> assistant_service -> core modules`.

- **Weather (planned):** Open-Meteo for Houston (`29.76`, `-95.36`), `wind_speed_unit=ms`.
- **Advice (planned):** Pure functions in `advice_engine.py`; rain + travel -> bus/transit + umbrella.
- **Time (planned):** `America/Chicago`; event windows `[start, end)`.

## Current Project Layout (Phase 1)

```text
weather-aware-personal-assistant/
|- calendar.json
|- pyproject.toml
|- specs/PRD.md
|- docs/rules.md
|- docs/steering-evidence.md
|- src/assistant/
|  |- __init__.py
|  |- __main__.py
|  `- cli/
|     `- __init__.py
`- tests/
   `- conftest.py
```

Additional modules listed in the planned architecture will be added in later phases.

## Calendar Format

```json
{
  "events": [
    {
      "title": "Team Standup",
      "start": "2026-06-10T09:00:00",
      "end": "2026-06-10T09:30:00",
      "location": "Office Building A"
    }
  ]
}
```

Naive datetimes are interpreted as Houston local time. Update event dates to stay within the 7-day forecast window for live demos.

## Vibe Report

*(To be completed after implementation; see `docs/steering-evidence.md` for real notes.)*

### Where did the AI's vibe drift?

See `docs/steering-evidence.md` for the recorded Phase 1 handoff observation.

### When was the Builder Hammer used?

See `docs/steering-evidence.md`. No manual source-code logic repair has occurred yet.

### What was the most successful steering prompt?

(Placeholder until later phases.)
