# Agent and Development Rules

## Assistant Persona

- Friendly, concise, and practical.
- Never invent weather data; only use fetched or injected forecast values.
- Explain advice briefly when the formatter presents results; the advice engine itself emits fixed message templates only.

## Architecture Constraints

### Dependency Direction

```text
CLI (repl, formatter) -> assistant_service -> core modules
core modules must NOT import cli/ or rich
```

Core modules: `config.py`, `models.py`, `calendar_loader.py`, `weather_client.py`, `weather_window.py`, `advice_engine.py`.

### Pure Advice Engine

`advice_engine.py` must be:

- Stateless and deterministic
- Implemented with pure functions
- Free of `print()`, `input()`, `open()`, network calls, file reads, Rich, and httpx
- Verified by AST import/call guards and capsys output tests

### HTTP Client

- Use **httpx** only. Do not add `requests`.

### Presentation

- **Rich** is allowed only in `src/assistant/cli/`.
- Formatting logic lives in `formatter.py`; command dispatch in `repl.py`.

### Configuration

- Houston coordinates, timezone, thresholds, and paths live in `config.py` only.
- No scattered magic numbers in advice or weather modules.

### Dependencies and Timezones

- Runtime dependencies: `httpx`, `rich`, and `pytest` (dev optional group).
- On Windows, `pyproject.toml` must declare `tzdata; platform_system == 'Windows'` so `America/Chicago` IANA timezone support is available when the package is installed.

## Testing Rules

- Use pytest; no live network in unit tests.
- Inject `http_get` or service-level fetchers for weather tests.
- Cover rain->bus, online exclusion, severe-over-rain ordering, `[start, end)` boundaries, calendar validation, and REPL unknown/exit behavior.
- AST-based guards confirm `advice_engine` has no I/O; capsys tests supplement but do not replace AST checks.

## Error Handling

- Raise typed errors: `CalendarError`, `WeatherFetchError`.
- REPL catches expected errors and shows Rich panels - no user-facing tracebacks.

## Agent Checklist (Later Phases)

- [ ] Keep `advice_engine` pure before adding CLI polish
- [ ] Pass `wind_speed_unit=ms` on every Open-Meteo request
- [ ] Do not import Rich outside `cli/`
- [ ] Add tests before marking a phase complete
- [ ] Update `docs/steering-evidence.md` only from real observations
- [ ] Do not fabricate Vibe Report incidents

## Steering Evidence

Record real steering notes in `docs/steering-evidence.md`. Do not invent Builder Hammer or vibe-drift stories.
