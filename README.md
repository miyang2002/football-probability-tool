# Football Probability Tool

Local personal-use football probability analysis website.

## Features

- Match dashboard with sample or live China Sports Lottery fixtures.
- Win/draw/loss probability analysis.
- Scoreline probability heatmap.
- Total-goals and over/under distributions.
- Half-time win/draw/loss estimates.
- Model-versus-odds recommendation engine.
- Conservative, balanced, and return-seeking parlay recommendations.
- Prediction snapshot storage for review and backtesting.
- Live odds status, movement indicators, and 30-second browser refresh.

## Run

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000`.

To use live China Sports Lottery fixtures and odds:

```bash
FOOTBALL_DATA_PROVIDER=sporttery SPORTTERY_REFRESH_SECONDS=30 uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## Test

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q
```

## Deploy On Render

This repository includes `render.yaml` for a public Render web service.

1. Push this repository to GitHub.
2. In Render, choose **New +** then **Blueprint**.
3. Connect the GitHub repository.
4. Let Render read `render.yaml`.
5. Create the service and wait for the deploy to finish.
6. Open the generated Render URL.

The Render service uses:

- Instance plan: `free`
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Health check: `/api/health`
- Data source: `FOOTBALL_DATA_PROVIDER=auto`
- China Sports Lottery refresh: `SPORTTERY_REFRESH_SECONDS=30`
- The Odds API refresh: `THE_ODDS_REFRESH_SECONDS=300`
- Optional secret: `THE_ODDS_API_KEY`

No access password is configured. Anyone with the Render URL can open the site.

The free Render instance can sleep when idle. The first request after sleep may take longer, and odds refresh resumes after the service wakes up.

## Data Sources

The default provider is deterministic sample data for offline development and repeatable tests.

Set `FOOTBALL_DATA_PROVIDER=auto` on Render. Auto mode tries China Sports Lottery first, then The Odds API when `THE_ODDS_API_KEY` is configured, and finally sample data if both live sources fail.

China Sports Lottery mode fetches live football fixtures and HAD win/draw/loss odds from the public calculator JSON endpoint. The provider sends browser-like headers, parses upcoming matches only, caches data in memory, and refreshes when the cache is older than `SPORTTERY_REFRESH_SECONDS`.

The Odds API mode fetches deploy-friendly football h2h odds. Add `THE_ODDS_API_KEY` in Render service environment variables. Optional overrides:

- `THE_ODDS_API_SPORT_KEY`, default `soccer_fifa_world_cup`
- `THE_ODDS_API_REGIONS`, default `eu,uk,us`
- `THE_ODDS_API_BOOKMAKER`, default first bookmaker returned with h2h odds

If live sources are blocked or unavailable, the app keeps using the last successful live cache when present. If no live cache exists, it falls back to sample data and shows the feed warning in the top bar.

Some cloud IP ranges can be blocked by the China Sports Lottery WAF. If that happens on Render, the top bar will show the feed warning and the app will continue with cached or sample data.

## Risk Note

The site is an analysis assistant. It shows probabilities, expected value, and risk, and it does not guarantee match outcomes.
