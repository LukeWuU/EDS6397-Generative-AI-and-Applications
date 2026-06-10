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

- Runtime dependencies: `httpx` and `rich`.
- Development dependency: `pytest` in the `dev` optional group.
- On Windows, `pyproject.toml` declares `tzdata; platform_system == 'Windows'` so `America/Chicago` IANA timezone support is available when the package is installed.

## Testing Rules

- Use pytest; no live network in unit tests.
- Inject loaders, fetchers, transports, services, consoles, and scripted REPL input for tests.
- Cover rain->bus, online exclusion, severe-over-rain ordering, `[start, end)` boundaries, calendar validation, service atomic reload, and REPL unknown/exit behavior.
- AST-based guards confirm `advice_engine` has no I/O; capsys tests supplement but do not replace AST checks.

## Error Handling

- Raise typed errors: `CalendarError`, `WeatherFetchError`.
- REPL catches expected errors and shows Rich panels - no user-facing tracebacks.

## Agent Checklist (Final Status)

- [x] Keep `advice_engine` pure
- [x] Pass `wind_speed_unit=ms` on every Open-Meteo request
- [x] Do not import Rich outside `cli/`
- [x] Add tests before marking each phase complete
- [x] Update `docs/steering-evidence.md` from real observations
- [x] Do not fabricate Vibe Report incidents

## Final Compliance Summary

- Core modules do not import CLI or Rich.
- `assistant_service.py` contains orchestration only.
- `formatter.py` and `repl.py` contain presentation only.
- Unit tests use injected or mocked dependencies with no live network.
- Expected errors are user-facing without traceback exposure in the REPL.
- Verified full test suite: `305 passed in 1.06s`.

## Steering Evidence

Record real steering notes in `docs/steering-evidence.md`. Do not invent Builder Hammer or vibe-drift stories.
