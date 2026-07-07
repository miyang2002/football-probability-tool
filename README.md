# Football Probability Tool

Local personal-use football probability analysis website.

## Features

- Match dashboard with sample football fixtures.
- Win/draw/loss probability analysis.
- Scoreline probability heatmap.
- Total-goals and over/under distributions.
- Half-time win/draw/loss estimates.
- Model-versus-odds recommendation engine.
- Conservative, balanced, and return-seeking parlay recommendations.
- Prediction snapshot storage for review and backtesting.

## Run

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000`.

## Test

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q
```

## Data Sources

Version 1 runs with deterministic sample data and accepts environment-configured API keys through provider modules. Use manual analysis input or replace `SampleDataProvider` with an API-backed provider when stable data access is configured.

## Risk Note

The site is an analysis assistant. It shows probabilities, expected value, and risk, and it does not guarantee match outcomes.
