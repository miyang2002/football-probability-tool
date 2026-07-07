# Live Football Data Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add live China Sports Lottery fixture and odds ingestion with upcoming-match filtering, refresh status, and frontend auto-refresh.

**Architecture:** Keep the existing FastAPI/static frontend shape. Add provider-level parsing, cache, source status, and route dependency injection so tests stay offline while runtime can use the live source. Extend existing domain models with optional odds metadata without breaking current payloads.

**Tech Stack:** Python 3.10, FastAPI, Pydantic 2, pytest, stdlib `urllib`, vanilla JavaScript.

---

## File Structure

- Modify `app/domain.py`: add odds movement metadata and feed status models.
- Modify `app/data/providers.py`: add Sporttery parser, cached live provider, provider factory, and upcoming filters.
- Modify `app/routes.py`: use provider dependency, add feed status, support match windows.
- Modify `app/services.py`: no broad change expected; recommendations consume updated odds.
- Modify `app/static/index.html`: add feed status and window controls.
- Modify `app/static/app.js`: poll live data, render odds movement, pass window query.
- Modify `app/static/styles.css`: style status, odds rows, and movement badges.
- Modify `README.md`: document live provider environment variables and warning.
- Add `tests/test_live_provider.py`: offline parser/cache/filter tests.
- Modify API/static tests for new provider dependency and UI markers.

## Tasks

### Task 1: Domain Metadata

- [ ] Write tests proving `OddsQuote` accepts optional source/update/movement fields and feed status serializes.
- [ ] Implement optional metadata fields in `app/domain.py`.
- [ ] Run domain tests and commit.

### Task 2: Sporttery Provider

- [ ] Write tests with injected Sporttery JSON for parsing fixtures, HAD odds, trend flags, kickoff conversion, and upcoming filtering.
- [ ] Implement parser, cache, headers, fallback, and provider factory in `app/data/providers.py`.
- [ ] Run data/provider tests and commit.

### Task 3: API Routing

- [ ] Write tests for `/api/matches?window=next`, `/api/feed/status`, unknown match handling, and sample override.
- [ ] Replace global provider with dependency-backed configured provider.
- [ ] Run API tests and commit.

### Task 4: Frontend Auto Refresh

- [ ] Write static tests for feed status UI, window controls, auto-refresh interval, and odds movement classes.
- [ ] Implement UI controls and polling in `index.html`, `app.js`, and `styles.css`.
- [ ] Run static tests and commit.

### Task 5: Documentation And Verification

- [ ] Update README with `FOOTBALL_DATA_PROVIDER=sporttery` and `SPORTTERY_REFRESH_SECONDS`.
- [ ] Run full tests with `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q`.
- [ ] Start the local app in sporttery mode and verify `/api/matches`, `/api/feed/status`, selected analysis, and parlays.
- [ ] Stop verification server and confirm clean git status.
