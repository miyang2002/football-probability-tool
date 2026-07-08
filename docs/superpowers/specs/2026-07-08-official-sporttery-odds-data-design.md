# Official Sporttery Odds Data Design

## Goal

Build the first-stage data foundation for a local-first football analysis workstation by verifying and parsing official China Sports Lottery odds for five football markets: win/draw/loss, handicap win/draw/loss, correct score, total goals, and half-time/full-time. This phase proves official data availability and completeness before changing the recommendation model or rebuilding the main interface.

## Scope

This phase focuses only on official odds data. It must not use third-party odds as substitutes, must not show model-theoretical odds as real odds, and must not change the betting recommendation rules beyond exposing data completeness. If an official market is missing for a match, the system records that market as missing and excludes it from recommendation and parlay eligibility.

The five official markets are:

- `had`: 胜平负
- `hhad`: 让球胜平负
- `crs`: 比分
- `ttg`: 总进球数
- `hafu`: 半全场

## Data Source

The primary source remains the official China Sports Lottery calculator API behind the public mobile calculator page at `https://m.sporttery.cn/mjc/jsq/zqspf/`. The provider should request the existing calculator endpoint with all required pool codes:

```text
https://webapi.sporttery.cn/gateway/uniform/football/getMatchCalculatorV1.qry?channel=c&poolCode=had,hhad,crs,ttg,hafu
```

Requests must keep browser-like headers and an official Sporttery referer. The implementation should support overriding the endpoint through `SPORTTERY_ENDPOINT` for diagnostics, but the default must be the official endpoint.

## Provider Behavior

The local provider remains the source of truth for real analysis. It refreshes official odds automatically and keeps the last successful cache when refresh fails. Default refresh should move to 60 seconds for official data validation, while the UI keeps a manual refresh button.

For each match, the provider should return:

- Match metadata: ID, league, kickoff time, home team, away team.
- Market availability: available, missing, suspended, or malformed.
- Market odds: normalized selections with official decimal odds, update time, previous odds, movement, source, and raw selection key.
- Missing data list: exactly which markets were not available or could not be parsed.
- Data quality flags: official odds completeness, parse warnings, and last successful refresh time.

## Normalized Market Shape

The existing `OddsQuote` model should remain backward compatible, but data parsing should normalize all five official markets into the same structure:

- `market`: one of `winner`, `handicap_winner`, `score`, `total_goals`, `half_full`
- `selection`: stable internal key such as `home`, `draw`, `away`, `home_-1`, `2-1`, `3`, `home_home`
- `selection_label`: Chinese display label such as `主胜`, `让球主胜`, `2-1`, `3球`, `胜胜`
- `decimal_odds`: official decimal odds
- `source`: `sporttery`
- `updated_at`
- `previous_decimal_odds`
- `movement`
- `raw_selection`

The parser must preserve raw market payload snippets in diagnostic output only, not in the normal public recommendation payload.

## Diagnostic API

Add a local diagnostic endpoint for validating official market coverage before recommendation work:

```text
GET /api/official-odds/diagnostics?window=next
```

The response should include:

- Feed status and refresh timestamps.
- Count of upcoming matches.
- Per-match market coverage for all five markets.
- Per-market odds count and parse warning count.
- A compact list of odds for each market.
- Missing markets per match.

This endpoint is for local validation and UI diagnostics. It should not require authentication because the app is local-first for this phase.

## Diagnostic UI

Add a simple data completeness view to the existing frontend, not a full redesign. It should show:

- Overall official data status.
- A table of upcoming matches.
- Five market columns: 胜平负, 让球胜平负, 比分, 总进球, 半全场.
- Each cell shows `已抓到`, `缺失`, `暂停`, or `解析异常`.
- Expanding a match shows the official odds items for each market.
- Missing markets are listed plainly, for example `缺少：比分、半全场`.

This view is not the final workstation UI. It exists to prove whether official data is complete enough for the next phase.

## Recommendation Rules For This Phase

Recommendation and parlay behavior should remain conservative:

- Markets with official odds can be marked as eligible for later analysis.
- Markets without official odds must be marked as unavailable.
- No model-theoretical odds should be used as real odds.
- No third-party odds should be used.
- The current recommendation UI can continue to exist, but this phase does not attempt to make all five markets produce final advice.

## Error Handling

If the official endpoint fails:

- Keep and display the last successful official cache.
- Mark current refresh as failed.
- Do not replace official odds with sample or third-party odds in diagnostic output.
- If no official cache exists, the diagnostic UI shows no official data and lists the fetch error.

If only some markets parse:

- Return all successfully parsed markets.
- Mark failed markets as `解析异常`.
- Include parse warnings with enough detail for debugging.

## Testing

Tests must not hit the real network. They should use fixture payloads that include all five market payload shapes and edge cases:

- All five markets present.
- Some markets missing.
- Suspended or empty odds.
- Odds movement from previous cache.
- Malformed odds value.
- Diagnostic endpoint response shape.

Existing sample provider tests should remain stable. Sporttery parser tests should prove that each official pool code maps to the normalized market shape.

## Success Criteria

This phase is complete when local diagnostics can show, for upcoming official matches, whether each of the five official markets is available and can list the parsed official odds. It is also complete when missing or malformed official data is visible instead of silently replaced by model-theoretical or third-party values.

Only after this data layer is verified should the project move to recommendation redesign, model calibration, parlay workstation UI, and backtesting.
