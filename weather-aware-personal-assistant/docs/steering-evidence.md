# Steering Evidence Log

## Approved Planning Prompt

The user requested a detailed implementation plan for "Don't Code, Orchestrate: The Weather-Aware Personal Assistant" with:

- Python CLI REPL personal assistant
- Open-Meteo weather (no API key)
- Local `calendar.json` events
- Deterministic rule-based advice (no LLM)
- Modular architecture with PRD, rules, tests, README, and Vibe Report
- Exceptional (Architect) rubric alignment

## Confirmed Architecture Decisions

1. **Weather location:** Houston default coords only (`29.76`, `-95.36`); event `location` is text for advice heuristics, not geocoding.
2. **Event timing:** Worst conditions across full event window `[start, end)` (half-open), not start-time only.
3. **Advice module path:** Single `advice_engine.py` module - no `advice/` package.
4. **Dependencies:** `httpx` + `rich` runtime; conditional `tzdata; platform_system == 'Windows'` for `America/Chicago` IANA timezone support on Windows; `pytest` dev; no `requests`.
5. **REPL commands:** Minimal set - `help`, `events`, `weather`, `advice`, `reload`, `quit`/`exit`.
6. **Wind unit:** Require `wind_speed_unit=ms`; threshold `14.0` m/s for strong wind.
7. **Rain codes:** Expanded to `{51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82}` including freezing precipitation.
8. **No-I/O tests:** AST import/call guards plus capsys; substring check supplemental only.
9. **Service orchestration:** `assistant_service.py` coordinates loader, fetcher, summarizer, and advice generator with dependency injection.
10. **Presentation isolation:** Rich confined to `src/assistant/cli/`.

## Phase-by-Phase Steering Approach

Each implementation phase used the same corrective pattern:

- "Implement Phase N only"
- exact file allowlist
- "Do not create or modify any other file"
- explicit behavioral and architecture contracts
- focused pytest command only
- no full suite, install, application run, commit, push, Multitask, or background worker during the phase
- stop after focused tests pass
- report exact files changed and scope confirmation

After each phase, Git status and focused test results were reviewed before moving on.

## Phase Evidence Table

| Phase | Allowed files | Focused verification | Commit |
|-------|---------------|----------------------|--------|
| 1 | README, PRD, rules, steering evidence, pyproject, calendar.json, package entry-point files | Phase 1 structure and file-boundary review | `fc205d6` |
| 2 | `config.py`, `models.py`, `test_models.py` | `pytest tests/test_models.py -q` | `115afbe` |
| 3 | `calendar_loader.py`, `test_calendar_loader.py` | `pytest tests/test_calendar_loader.py -q` | `f0d08b3` |
| 4 | `weather_client.py`, `test_weather_client.py` | `pytest tests/test_weather_client.py -q` | `95acb78` |
| 5 | `weather_window.py`, `test_weather_window.py` | `pytest tests/test_weather_window.py -q` | `8ec7c2d` |
| 6 | `advice_engine.py`, `test_advice_engine.py` | `pytest tests/test_advice_engine.py -q` | `4476366` |
| 7 | `assistant_service.py`, `test_assistant_service.py` | `pytest tests/test_assistant_service.py -q` | `39ecbeb` |
| 8 | `cli/formatter.py`, `cli/repl.py`, `__main__.py`, `test_repl.py` | `pytest tests/test_repl.py -q` | `c5befcc` |
| 9 | `.gitignore` | file review | `a55c7c0` |
| Final docs | README, PRD, rules, steering evidence | documentation review complete | commit pending |

## Vibe Drift Observations

During the first Build handoff, the agent ignored the explicitly limited Phase 1 scope and attempted to implement the entire multi-phase project, run tests, and create installation artifacts. The workspace had to be restored to an earlier checkpoint, caches and package metadata were removed, and the task was reissued with an exact file allowlist and explicit prohibitions.

Lessons learned:

- broad prompts encourage scope expansion
- phase boundaries must be explicit
- file allowlists and command allowlists improve control
- Git status and focused tests were used after every phase

## Service-Factory and Test-Quality Corrective Pass

During Phase 7 review, `create_default_service` placement and a weak AST forbidden-call test were corrected through a narrowly scoped steering prompt to the AI agent. No manual Python source-code repair was performed by the user.

## Focused-Test Workflow

Each build phase was gated by one focused pytest command against the new module tests only. The full suite was run later for final verification.

Verified final results:

- full automated suite: `305 passed in 1.06s`
- live CLI smoke test: loaded 3 events and 168 hourly weather records; `help`, `events`, `weather`, `advice`, `reload`, and `quit` worked with no traceback

## Builder Hammer Incidents

No manual business-logic or Python source-code repair was used.

Manual terminal commands were used as a limited Builder Hammer to:

- remove `.pytest_cache`, `__pycache__`, `.pyc`, and `.egg-info`
- restore a clean workspace after the first Build scope violation
- inspect, stage, commit, and push approved files
- verify Git status and file boundaries

## Most Successful Steering Prompt

The most successful corrective prompt pattern was:

- "Implement Phase N only"
- exact file allowlist
- "Do not create or modify any other file"
- explicit architecture and behavioral contracts
- focused pytest command only
- no full suite, install, application run, commit, push, Multitask, or background worker
- stop after focused tests pass
- report exact files and scope confirmation

Why it worked:

- reduced ambiguity
- established measurable acceptance criteria
- prevented scope drift
- made every phase independently reviewable
- produced a clear Git history and evidence of orchestration
