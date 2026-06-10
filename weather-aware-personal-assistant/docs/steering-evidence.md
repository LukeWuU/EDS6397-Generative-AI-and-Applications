# Steering Evidence Log

**Important:** Update sections marked `(placeholder)` only from real events during or after implementation. Do not fabricate incidents.

## Approved Planning Prompt

The user requested a detailed implementation plan for "Don't Code, Orchestrate: The Weather-Aware Personal Assistant" with:

- Python CLI REPL personal assistant
- Open-Meteo weather (no API key)
- Local `calendar.json` events
- Deterministic rule-based advice (no LLM)
- Modular architecture with PRD, rules, tests, README, and Vibe Report
- Exceptional (Architect) rubric alignment

## Corrective Planning Decisions

1. **Weather location:** Houston default coords only (`29.76`, `-95.36`); event `location` is text for advice heuristics, not geocoding.
2. **Event timing:** Worst conditions across full event window `[start, end)` (half-open), not start-time only.
3. **Advice module path:** Single `advice_engine.py` module - no `advice/` package.
4. **Dependencies:** `httpx` + `rich` runtime; conditional `tzdata; platform_system == 'Windows'` for `America/Chicago` IANA timezone support on Windows; `pytest` dev; no `requests`.
5. **REPL commands:** Minimal set - `help`, `events`, `weather`, `advice`, `reload`, `quit`/`exit`.
6. **Wind unit:** Require `wind_speed_unit=ms`; threshold `14.0` m/s for strong wind.
7. **Rain codes:** Expanded to `{51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82}` including freezing precipitation.
8. **No-I/O tests:** AST import/call guards plus capsys; substring check supplemental only.

## Vibe Drift Observations

During the first Build handoff, the Agent ignored the explicit Phase 1-only boundary and implemented the full eight-phase plan, ran tests, and created installation artifacts. The workspace was restored to an earlier checkpoint, residual caches and package metadata were removed, the file tree was audited, and a narrowly scoped Agent prompt was then used to create only the six missing Phase 1 files.

## Builder Hammer Incidents

No manual source-code logic repair has occurred yet. Manual terminal commands were used only to remove generated caches and package metadata after the scope violation described above.

## Most Successful Steering Prompt

`(placeholder - record after implementation which corrective prompt worked best)`
