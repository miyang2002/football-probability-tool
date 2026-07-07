# Live Football Data Design

## Goal

Replace static-only match data with a live-capable data layer that pulls upcoming football fixtures and odds from China Sports Lottery where available, filters out started or finished matches, refreshes odds frequently, and falls back to deterministic sample data when the live source is unavailable.

## Data Sources

The primary live source is the China Sports Lottery football calculator JSON endpoint used by the public calculator page:

- `https://webapi.sporttery.cn/gateway/uniform/football/getMatchCalculatorV1.qry?channel=c&poolCode=had,hhad`

The request must send browser-like headers, including a `Referer` for the public calculator page, because direct bare HTTP requests can be blocked by WAF. The first implementation will parse HAD winner odds and HHAD handicap metadata where present. It will not scrape rendered HTML.

The provider is selected with `FOOTBALL_DATA_PROVIDER`:

- `sample`: deterministic local sample data for tests and offline development.
- `sporttery`: live China Sports Lottery provider with sample fallback.
- unset: use `sample` in tests and `sporttery` for local app runs when explicitly documented.

## Filtering

The match list defaults to upcoming matches only. A match is upcoming when its parsed kickoff time is after the current time. China Sports Lottery date/time fields are interpreted in `Asia/Shanghai` and converted to UTC for the existing `kickoff_utc` field.

The API accepts a `window` query parameter:

- `next`: next available match day after now.
- `tomorrow`: local tomorrow only; if empty, the response falls back to `next`.
- `3d`: upcoming matches in the next 3 days.
- `7d`: upcoming matches in the next 7 days.

Parlay recommendations use the same upcoming-only default so started or finished matches are never included by default.

## Odds Refresh

The live provider keeps an in-memory cache. On each request it refreshes from the source if the cache is older than `SPORTTERY_REFRESH_SECONDS`, defaulting to 30 seconds. If refresh fails, it returns the last successful cache. If no successful cache exists, it returns sample data and exposes feed status showing fallback mode.

Odds include optional metadata:

- `source`
- `updated_at`
- `previous_decimal_odds`
- `movement`: `up`, `down`, or `flat`

Movement is derived from China Sports Lottery trend flags when present, and from in-process previous odds when a cached previous value exists.

## API

Existing endpoints remain compatible:

- `GET /api/matches`
- `GET /api/matches/{match_id}/analysis`
- `GET /api/parlays`

New endpoint:

- `GET /api/feed/status`: source name, health, last success, last attempt, refresh seconds, message.

The frontend polls `/api/matches`, selected match analysis, `/api/parlays`, and `/api/feed/status` every 30 seconds. It displays last refresh state and highlights odds movement.

## Testing

Tests must not depend on external network access. Unit tests will inject Sporttery JSON payloads into the parser/provider. API tests will force sample provider mode or override the provider dependency.

## Risk

China Sports Lottery endpoint access can change without notice. The implementation must treat live data as best-effort, expose failures clearly, and keep the site usable through fallback data.
