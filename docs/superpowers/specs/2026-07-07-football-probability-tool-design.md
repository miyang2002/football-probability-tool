# Football Probability Tool Design

## Goal

Build a personal-use football probability analysis website for World Cup and other football matches. The site should automatically collect match, team, odds, and contextual information where possible, run probability models, simulate match outcomes, and present highly visual analysis for single matches and parlay combinations.

The tool is an analysis assistant, not a guaranteed betting system. Every recommendation must show probability, expected value, risk level, and the reason behind the recommendation.

## Product Scope

Version 1 focuses on:

- Single-match analysis for win/draw/loss, scoreline, total goals, over/under, and half-time result.
- Monte Carlo simulation for match score distribution.
- Odds comparison against model probabilities.
- Parlay recommendation with three selectable strategies: conservative, balanced, and return-seeking.
- Highly visual dashboard views for probability, score, goals, value, and risk.
- Automatic data ingestion where stable APIs are available, with manual override for unreliable or missing data.

Version 1 does not promise fully reliable automatic scraping from every website. If a source is unavailable, the site should degrade to cached data or manual input rather than blocking analysis.

## Users And Workflow

The only intended user is the owner of the local website.

Primary workflow:

1. Open the dashboard and load today's matches.
2. Select a match for single-match analysis.
3. Review model probabilities, score heatmap, total-goals distribution, half-time probabilities, and market odds comparison.
4. Review the generated recommendation and risk explanation.
5. Open parlay recommendations.
6. Choose strategy: conservative, balanced, or return-seeking.
7. Review suggested 2-leg, 3-leg, and 4-leg combinations with probability, total odds, expected value, and risk.
8. Optionally manually adjust injuries, lineup assumptions, or odds before rerunning the model.

## Data Sources

The system uses a layered data-source approach:

- Football data API: fixtures, teams, recent results, scores, standings, and historical match data.
- Odds API: market odds for match winner, totals, and other available markets.
- News/search layer: injuries, projected lineups, manager/tactical context, and important match news.
- Manual override: odds, injuries, expected lineup strength, tactical notes, and match uncertainty.

Recommended source priority:

1. Stable API data when available.
2. Cached previous API data if the current call fails.
3. Search/news summaries for contextual information.
4. Manual entry for missing or questionable fields.

The first implementation should support environment-configured API keys, so free sources can be used first and paid sources can be added by configuration without changing the model layer.

## Core Model

The model pipeline has separate stages:

1. Team strength estimation:
   - Recent form.
   - Historical goal rates.
   - Attack and defense strength.
   - Elo-like rating or external ranking input.
   - Home/neutral venue adjustment.
   - Rest and travel adjustment when data is available.
   - Injury and lineup adjustment.

2. Goal expectation:
   - Estimate expected goals for each team.
   - Apply contextual adjustments for tactical style, injuries, and match importance.

3. Score distribution:
   - Use Poisson or Dixon-Coles style distribution for full-time scorelines.
   - Generate probabilities for common scorelines from 0-0 through at least 5-5.
   - Collapse rare high-score outcomes into an "other" bucket for display.

4. Monte Carlo simulation:
   - Simulate configurable match counts, default 10,000.
   - Produce win/draw/loss, score, total goals, over/under, and half-time estimates.

5. Half-time model:
   - Estimate half-time goal expectations as a fraction of full-match expected goals.
   - Generate half-time win/draw/loss probability.
   - Half-time/full-time combination markets are outside Version 1; Version 1 outputs half-time win/draw/loss only.

6. Odds calibration:
   - Convert decimal odds to implied probability.
   - Remove market overround when all sides of a market are present.
   - Compare model probability with market implied probability.
   - Compute value difference and expected value.

## Recommendation Logic

Single-match recommendations must include:

- Recommended market and pick.
- Model probability.
- Market implied probability when odds are available.
- Expected value.
- Confidence rating.
- Risk level.
- Main supporting reasons.
- Main warnings.

The wording must avoid guaranteed outcomes. Use terms like "model leans", "higher value", "risk is elevated", and "not recommended" instead of certainty.

## Parlay Optimizer

The parlay optimizer generates combinations from eligible single-match picks.

Supported strategy modes:

- Conservative: prioritize high hit probability and low uncertainty.
- Balanced: combine probability, value gap, and risk.
- Return-seeking: prioritize expected value and total odds while keeping minimum probability limits.

Default scoring:

- Conservative score = hit probability 60% + value gap 25% + low risk 15%.
- Balanced score = hit probability 40% + value gap 40% + low risk 20%.
- Return-seeking score = expected value 50% + total odds 30% + hit probability 20%.

The optimizer must show:

- Recommended combination type: 2-leg, 3-leg, 4-leg, or custom.
- Each selected match and market.
- Per-leg probability, odds, value gap, and risk.
- Combined hit probability.
- Combined decimal odds.
- Expected value.
- Risk level.
- Explanation for why the combination was selected.
- Explanation when the model recommends not adding another leg.

The optimizer should avoid combining too many correlated picks from the same match unless the UI clearly labels the correlation risk.

## Visual Design Requirements

The website should be visual-first and dense enough for repeated analysis. It should feel like an analytical tool, not a marketing page.

Single-match page visualizations:

- Win/draw/loss probability bars with model probability and market implied probability side by side.
- Scoreline heatmap where rows are home-team goals and columns are away-team goals.
- Top scoreline list with probability and simulation frequency.
- Total-goals distribution chart for 0, 1, 2, 3, 4, 5+ goals.
- Over/under probability chart for common lines such as 1.5, 2.5, and 3.5.
- Half-time win/draw/loss probability chart.
- Model-vs-market value chart showing probability edge and expected value.
- Risk panel showing data quality, market disagreement, injury uncertainty, and lineup uncertainty.

Parlay page visualizations:

- Strategy selector for conservative, balanced, and return-seeking modes.
- Combination cards for 2-leg, 3-leg, and 4-leg recommendations.
- Risk-return scatter plot where each candidate combination is plotted by hit probability and expected value.
- Combined probability waterfall or stacked view showing how each added leg lowers hit probability.
- Value table with sortable columns for probability, odds, expected value, and risk.
- Clear labels for "recommended", "optional", and "not recommended".

Dashboard visualizations:

- Today's match list with compact probability badges.
- Market edge badges for picks where model probability exceeds market implied probability.
- Data-quality indicator for each match.
- Quick filters for tournament, date, confidence, risk, and value.

## Application Architecture

Recommended architecture:

- Frontend: React or Next.js dashboard.
- Backend: Python FastAPI service.
- Model engine: Python module separated from API routes.
- Data connectors: isolated modules per provider.
- Database: SQLite for local personal use, with storage boundaries that can be moved to Postgres if concurrent multi-user use is needed.
- Background jobs: scheduled sync for fixtures, odds, results, and news.

Boundaries:

- Frontend only renders data and sends analysis requests.
- API layer validates requests and returns normalized responses.
- Data connectors fetch and normalize external data.
- Model engine accepts normalized data and returns deterministic analysis output.
- Recommendation engine converts probabilities and odds into recommendations.
- Storage layer keeps matches, odds snapshots, predictions, simulations, and results for backtesting.

## Data Flow

1. Scheduled sync loads fixtures, teams, odds, and results.
2. Context sync gathers injury, lineup, manager, and tactical notes where available.
3. Normalization converts provider-specific data into internal match, team, odds, and context records.
4. User opens the dashboard and selects a match.
5. Backend builds a match-analysis input object.
6. Model engine estimates expected goals and probability distributions.
7. Simulation engine runs Monte Carlo trials.
8. Recommendation engine compares model probabilities with odds.
9. Frontend renders charts, tables, risk explanations, and suggestions.
10. Prediction and source snapshots are stored for review and backtesting.

## Error Handling And Fallbacks

The site should remain usable when data sources fail.

- If fixture API fails, show cached fixtures and mark data as stale.
- If odds API fails, allow manual odds entry and hide market-value calculations until odds exist.
- If news/search data is missing, show lower data quality and higher uncertainty.
- If model inputs are incomplete, use conservative defaults and show what was assumed.
- If simulation fails, show deterministic probability output and an error message for simulation only.
- If a recommendation is low confidence, show "not recommended" rather than forcing a pick.

## Backtesting

The system should store every generated prediction snapshot before matches start.

The stored prediction history should support these backtesting views:

- Win/draw/loss calibration.
- Scoreline accuracy.
- Over/under accuracy.
- Half-time prediction accuracy.
- Parlay hit rate by strategy.
- Expected value versus actual result.
- Data-source quality versus prediction quality.

For Version 1, storage should be designed to support backtesting even if the full backtesting UI is simple.

## Testing Strategy

Model tests:

- Odds-to-probability conversion.
- Overround removal.
- Poisson score distribution sums to approximately 1.
- Win/draw/loss aggregation from score distribution.
- Total-goals aggregation.
- Monte Carlo output approximates analytical probabilities within tolerance.
- Parlay combined probability and expected value calculations.

API tests:

- Match analysis endpoint validates inputs.
- Missing odds still returns analysis.
- Missing context increases uncertainty.
- Failed provider calls fall back to cached/manual data.

Frontend tests:

- Dashboard renders empty, loading, loaded, and stale-data states.
- Single-match charts handle missing odds and missing context.
- Parlay strategy selector changes recommendation ordering.
- Chart labels and values remain readable on desktop and mobile widths.

## First Version Acceptance Criteria

The first usable version is complete when:

- The site can load a match list from configured data sources or sample data.
- A match detail page shows win/draw/loss, score heatmap, total goals, over/under, and half-time probabilities.
- Monte Carlo simulation can run and display distributions.
- Odds can be fetched or manually entered.
- The site can compare model probabilities with odds and show expected value.
- The recommendation panel explains picks and risks.
- The parlay optimizer supports conservative, balanced, and return-seeking modes.
- Visualizations render clearly on desktop and mobile.
- Core model and parlay calculations have automated tests.
