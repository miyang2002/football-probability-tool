# Football Probability Tool Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local personal football probability analysis website with single-match probability charts, score simulation, odds value analysis, and selectable parlay recommendations.

**Architecture:** FastAPI serves JSON APIs and static frontend assets. Python modules own domain schemas, probability math, simulation, recommendations, sample/provider data, and SQLite persistence. The frontend is dependency-light vanilla JavaScript with SVG/CSS visualizations so the first version runs reliably in the current environment and can be migrated to React after the model and API stabilize.

**Tech Stack:** Python 3.10, FastAPI, Pydantic 2, pytest, httpx, SQLite, vanilla JavaScript, CSS Grid/Flexbox, SVG, Canvas-free charts.

---

## File Structure

- `requirements.txt`: Documents runtime and test dependencies available in the environment.
- `README.md`: Local run, test, and data-source configuration instructions.
- `app/__init__.py`: Python package marker.
- `app/main.py`: FastAPI app, static file mounting, and route registration.
- `app/domain.py`: Pydantic request/response and internal data models.
- `app/model/odds.py`: Odds conversion, market overround removal, edge, and expected value.
- `app/model/score_model.py`: Poisson score matrix and aggregated match markets.
- `app/model/simulation.py`: Seeded Monte Carlo simulation from expected-goals inputs.
- `app/model/recommendations.py`: Single-match pick generation, confidence, and risk labels.
- `app/model/parlay.py`: Conservative, balanced, and return-seeking parlay optimizer.
- `app/data/sample_data.py`: Deterministic sample matches, teams, odds, and context.
- `app/data/providers.py`: Provider interface and sample provider implementation.
- `app/data/repository.py`: SQLite persistence for prediction snapshots.
- `app/routes.py`: HTTP endpoints for matches, single-match analysis, parlays, and snapshots.
- `app/static/index.html`: Single-page website shell.
- `app/static/styles.css`: Responsive analytical dashboard styling.
- `app/static/app.js`: Browser state management, API calls, and rendering orchestration.
- `app/static/charts.js`: SVG chart helpers for bars, heatmap, distributions, and scatter plot.
- `tests/`: Unit and API tests for the backend and static asset checks.

## Task 1: Project Skeleton And Health Endpoint

**Files:**
- Create: `requirements.txt`
- Create: `README.md`
- Create: `app/__init__.py`
- Create: `app/main.py`
- Create: `tests/test_app_health.py`

- [ ] **Step 1: Write the failing health test**

Create `tests/test_app_health.py`:

```python
from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint_returns_ok():
    client = TestClient(app)

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "football-probability-tool"}
```

- [ ] **Step 2: Run the health test and verify failure**

Run: `pytest tests/test_app_health.py -q`

Expected: FAIL because `app.main` does not exist.

- [ ] **Step 3: Create the minimal app package**

Create `app/__init__.py`:

```python
"""Football probability analysis application."""
```

Create `app/main.py`:

```python
from fastapi import FastAPI


app = FastAPI(title="Football Probability Tool")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "football-probability-tool"}
```

Create `requirements.txt`:

```text
fastapi
uvicorn
pydantic
pytest
httpx
numpy
```

Create `README.md`:

```markdown
# Football Probability Tool

Local personal-use football probability analysis website.

## Run

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000`.

## Test

```bash
pytest -q
```

## Data Sources

Version 1 runs with deterministic sample data and accepts environment-configured API keys through provider modules.
```

- [ ] **Step 4: Run the health test and verify pass**

Run: `pytest tests/test_app_health.py -q`

Expected: `1 passed`.

- [ ] **Step 5: Commit skeleton**

Run:

```bash
git add requirements.txt README.md app tests/test_app_health.py
git commit -m "feat: add app skeleton"
```

Expected: commit succeeds.

## Task 2: Domain Schemas

**Files:**
- Create: `app/domain.py`
- Create: `tests/test_domain.py`

- [ ] **Step 1: Write schema tests**

Create `tests/test_domain.py`:

```python
from app.domain import MatchContext, MatchInput, OddsQuote, TeamInput


def test_match_input_accepts_core_fields():
    match = MatchInput(
        match_id="m1",
        competition="World Cup",
        kickoff_utc="2026-07-08T19:00:00Z",
        home=TeamInput(name="France", attack_rating=1.25, defense_rating=0.88),
        away=TeamInput(name="Brazil", attack_rating=1.18, defense_rating=0.93),
        neutral_venue=True,
        context=MatchContext(home_injury_impact=0.08, away_injury_impact=0.03, data_quality=0.82),
        odds=[
            OddsQuote(market="winner", selection="home", decimal_odds=2.15),
            OddsQuote(market="winner", selection="draw", decimal_odds=3.20),
            OddsQuote(market="winner", selection="away", decimal_odds=3.40),
        ],
    )

    assert match.home.name == "France"
    assert match.context.data_quality == 0.82
    assert match.odds[0].decimal_odds == 2.15


def test_context_defaults_are_conservative():
    context = MatchContext()

    assert context.home_injury_impact == 0.0
    assert context.away_injury_impact == 0.0
    assert context.lineup_uncertainty == 0.2
    assert context.data_quality == 0.7
```

- [ ] **Step 2: Run schema tests and verify failure**

Run: `pytest tests/test_domain.py -q`

Expected: FAIL because `app.domain` does not exist.

- [ ] **Step 3: Implement domain models**

Create `app/domain.py`:

```python
from typing import Literal

from pydantic import BaseModel, Field


MarketName = Literal["winner", "total_goals", "half_time", "score"]
StrategyName = Literal["conservative", "balanced", "return_seeking"]
RiskLevel = Literal["low", "medium", "high"]


class TeamInput(BaseModel):
    name: str
    attack_rating: float = Field(gt=0)
    defense_rating: float = Field(gt=0)
    recent_goals_for: float = Field(default=1.4, ge=0)
    recent_goals_against: float = Field(default=1.2, ge=0)


class MatchContext(BaseModel):
    home_injury_impact: float = Field(default=0.0, ge=0, le=0.5)
    away_injury_impact: float = Field(default=0.0, ge=0, le=0.5)
    lineup_uncertainty: float = Field(default=0.2, ge=0, le=1)
    tactical_uncertainty: float = Field(default=0.2, ge=0, le=1)
    data_quality: float = Field(default=0.7, ge=0, le=1)
    notes: list[str] = Field(default_factory=list)


class OddsQuote(BaseModel):
    market: MarketName
    selection: str
    decimal_odds: float = Field(gt=1)


class MatchInput(BaseModel):
    match_id: str
    competition: str
    kickoff_utc: str
    home: TeamInput
    away: TeamInput
    neutral_venue: bool = True
    context: MatchContext = Field(default_factory=MatchContext)
    odds: list[OddsQuote] = Field(default_factory=list)


class ScoreProbability(BaseModel):
    home_goals: int
    away_goals: int
    probability: float


class MarketProbability(BaseModel):
    market: str
    selection: str
    probability: float


class PickRecommendation(BaseModel):
    match_id: str
    market: str
    selection: str
    model_probability: float
    decimal_odds: float | None = None
    implied_probability: float | None = None
    edge: float | None = None
    expected_value: float | None = None
    confidence: float
    risk: RiskLevel
    reasons: list[str]
    warnings: list[str]


class MatchAnalysis(BaseModel):
    match: MatchInput
    expected_home_goals: float
    expected_away_goals: float
    winner_probabilities: list[MarketProbability]
    half_time_probabilities: list[MarketProbability]
    total_goal_probabilities: list[MarketProbability]
    over_under_probabilities: list[MarketProbability]
    score_probabilities: list[ScoreProbability]
    top_scores: list[ScoreProbability]
    recommendations: list[PickRecommendation]
    data_quality: float


class ParlayRequest(BaseModel):
    strategy: StrategyName = "balanced"
    max_legs: int = Field(default=4, ge=2, le=6)


class ParlayLeg(BaseModel):
    match_id: str
    label: str
    market: str
    selection: str
    probability: float
    decimal_odds: float
    edge: float
    risk: RiskLevel


class ParlayRecommendation(BaseModel):
    strategy: StrategyName
    leg_count: int
    legs: list[ParlayLeg]
    combined_probability: float
    combined_odds: float
    expected_value: float
    risk: RiskLevel
    explanation: str
```

- [ ] **Step 4: Run schema tests and verify pass**

Run: `pytest tests/test_domain.py -q`

Expected: `2 passed`.

- [ ] **Step 5: Commit schemas**

Run:

```bash
git add app/domain.py tests/test_domain.py
git commit -m "feat: add football domain schemas"
```

Expected: commit succeeds.

## Task 3: Odds Math

**Files:**
- Create: `app/model/__init__.py`
- Create: `app/model/odds.py`
- Create: `tests/test_odds.py`

- [ ] **Step 1: Write odds tests**

Create `tests/test_odds.py`:

```python
from app.model.odds import expected_value, implied_probability, normalize_market_probabilities


def test_implied_probability_from_decimal_odds():
    assert round(implied_probability(2.5), 4) == 0.4


def test_normalize_market_probabilities_removes_overround():
    normalized = normalize_market_probabilities({"home": 2.0, "draw": 3.2, "away": 4.0})

    assert round(sum(normalized.values()), 6) == 1.0
    assert normalized["home"] > normalized["away"]


def test_expected_value_uses_model_probability_and_decimal_odds():
    assert round(expected_value(0.55, 2.1), 4) == 0.155
```

- [ ] **Step 2: Run odds tests and verify failure**

Run: `pytest tests/test_odds.py -q`

Expected: FAIL because `app.model.odds` does not exist.

- [ ] **Step 3: Implement odds math**

Create `app/model/__init__.py`:

```python
"""Probability model modules."""
```

Create `app/model/odds.py`:

```python
def implied_probability(decimal_odds: float) -> float:
    if decimal_odds <= 1:
        raise ValueError("decimal_odds must be greater than 1")
    return 1.0 / decimal_odds


def normalize_market_probabilities(selection_odds: dict[str, float]) -> dict[str, float]:
    raw = {selection: implied_probability(odds) for selection, odds in selection_odds.items()}
    total = sum(raw.values())
    if total <= 0:
        raise ValueError("market must contain at least one valid odds quote")
    return {selection: probability / total for selection, probability in raw.items()}


def expected_value(model_probability: float, decimal_odds: float) -> float:
    if not 0 <= model_probability <= 1:
        raise ValueError("model_probability must be between 0 and 1")
    if decimal_odds <= 1:
        raise ValueError("decimal_odds must be greater than 1")
    return model_probability * decimal_odds - 1.0
```

- [ ] **Step 4: Run odds tests and verify pass**

Run: `pytest tests/test_odds.py -q`

Expected: `3 passed`.

- [ ] **Step 5: Commit odds math**

Run:

```bash
git add app/model/__init__.py app/model/odds.py tests/test_odds.py
git commit -m "feat: add odds probability math"
```

Expected: commit succeeds.

## Task 4: Score Model And Market Aggregation

**Files:**
- Create: `app/model/score_model.py`
- Create: `tests/test_score_model.py`

- [ ] **Step 1: Write score-model tests**

Create `tests/test_score_model.py`:

```python
from app.model.score_model import (
    aggregate_score_matrix,
    estimate_expected_goals,
    poisson_score_matrix,
    top_scorelines,
)
from app.domain import MatchContext, MatchInput, TeamInput


def build_match() -> MatchInput:
    return MatchInput(
        match_id="m1",
        competition="World Cup",
        kickoff_utc="2026-07-08T19:00:00Z",
        home=TeamInput(name="France", attack_rating=1.22, defense_rating=0.90),
        away=TeamInput(name="Brazil", attack_rating=1.16, defense_rating=0.95),
        context=MatchContext(data_quality=0.8),
    )


def test_expected_goals_are_positive():
    home_xg, away_xg = estimate_expected_goals(build_match())

    assert home_xg > 0
    assert away_xg > 0


def test_score_matrix_sums_close_to_one():
    matrix = poisson_score_matrix(1.45, 1.1, max_goals=8)

    total = sum(item.probability for item in matrix)
    assert 0.995 <= total <= 1.001


def test_aggregates_include_winner_and_totals():
    matrix = poisson_score_matrix(1.45, 1.1, max_goals=8)
    markets = aggregate_score_matrix(matrix)

    winner = {(item.market, item.selection): item.probability for item in markets["winner"]}
    totals = {(item.market, item.selection): item.probability for item in markets["total_goals"]}

    assert round(sum(winner.values()), 6) == 1.0
    assert ("total_goals", "0") in totals
    assert ("over_under", "over_2.5") in {(item.market, item.selection) for item in markets["over_under"]}


def test_top_scorelines_are_sorted():
    matrix = poisson_score_matrix(1.45, 1.1, max_goals=8)
    top = top_scorelines(matrix, limit=3)

    assert len(top) == 3
    assert top[0].probability >= top[1].probability >= top[2].probability
```

- [ ] **Step 2: Run score-model tests and verify failure**

Run: `pytest tests/test_score_model.py -q`

Expected: FAIL because `app.model.score_model` does not exist.

- [ ] **Step 3: Implement score model**

Create `app/model/score_model.py`:

```python
from math import exp, factorial

from app.domain import MarketProbability, MatchInput, ScoreProbability


def estimate_expected_goals(match: MatchInput) -> tuple[float, float]:
    base_home = 1.35
    base_away = 1.15
    venue_boost = 1.0 if match.neutral_venue else 1.08

    home_xg = base_home * match.home.attack_rating * match.away.defense_rating * venue_boost
    away_xg = base_away * match.away.attack_rating * match.home.defense_rating

    home_xg *= 1.0 - match.context.home_injury_impact
    away_xg *= 1.0 - match.context.away_injury_impact

    uncertainty_drag = 1.0 - (match.context.tactical_uncertainty * 0.04)
    return max(home_xg * uncertainty_drag, 0.05), max(away_xg * uncertainty_drag, 0.05)


def poisson_probability(goals: int, expected_goals: float) -> float:
    return (expected_goals**goals * exp(-expected_goals)) / factorial(goals)


def poisson_score_matrix(home_xg: float, away_xg: float, max_goals: int = 8) -> list[ScoreProbability]:
    raw: list[ScoreProbability] = []
    for home_goals in range(max_goals + 1):
        for away_goals in range(max_goals + 1):
            probability = poisson_probability(home_goals, home_xg) * poisson_probability(away_goals, away_xg)
            raw.append(ScoreProbability(home_goals=home_goals, away_goals=away_goals, probability=probability))

    total = sum(item.probability for item in raw)
    return [
        ScoreProbability(
            home_goals=item.home_goals,
            away_goals=item.away_goals,
            probability=item.probability / total,
        )
        for item in raw
    ]


def aggregate_score_matrix(matrix: list[ScoreProbability]) -> dict[str, list[MarketProbability]]:
    home = sum(item.probability for item in matrix if item.home_goals > item.away_goals)
    draw = sum(item.probability for item in matrix if item.home_goals == item.away_goals)
    away = sum(item.probability for item in matrix if item.home_goals < item.away_goals)

    total_goals: list[MarketProbability] = []
    for total in range(5):
        probability = sum(item.probability for item in matrix if item.home_goals + item.away_goals == total)
        total_goals.append(MarketProbability(market="total_goals", selection=str(total), probability=probability))
    total_goals.append(
        MarketProbability(
            market="total_goals",
            selection="5+",
            probability=sum(item.probability for item in matrix if item.home_goals + item.away_goals >= 5),
        )
    )

    over_under = []
    for line in (1.5, 2.5, 3.5):
        over = sum(item.probability for item in matrix if item.home_goals + item.away_goals > line)
        over_under.append(MarketProbability(market="over_under", selection=f"over_{line}", probability=over))
        over_under.append(MarketProbability(market="over_under", selection=f"under_{line}", probability=1.0 - over))

    return {
        "winner": [
            MarketProbability(market="winner", selection="home", probability=home),
            MarketProbability(market="winner", selection="draw", probability=draw),
            MarketProbability(market="winner", selection="away", probability=away),
        ],
        "total_goals": total_goals,
        "over_under": over_under,
    }


def half_time_probabilities(home_xg: float, away_xg: float) -> list[MarketProbability]:
    half_matrix = poisson_score_matrix(home_xg * 0.45, away_xg * 0.45, max_goals=5)
    return aggregate_score_matrix(half_matrix)["winner"]


def top_scorelines(matrix: list[ScoreProbability], limit: int = 10) -> list[ScoreProbability]:
    return sorted(matrix, key=lambda item: item.probability, reverse=True)[:limit]
```

- [ ] **Step 4: Run score-model tests and verify pass**

Run: `pytest tests/test_score_model.py -q`

Expected: `4 passed`.

- [ ] **Step 5: Commit score model**

Run:

```bash
git add app/model/score_model.py tests/test_score_model.py
git commit -m "feat: add score probability model"
```

Expected: commit succeeds.

## Task 5: Monte Carlo Simulation

**Files:**
- Create: `app/model/simulation.py`
- Create: `tests/test_simulation.py`

- [ ] **Step 1: Write simulation tests**

Create `tests/test_simulation.py`:

```python
from app.model.simulation import run_simulation


def test_simulation_is_seeded_and_counts_trials():
    result_a = run_simulation(1.4, 1.1, trials=1000, seed=7)
    result_b = run_simulation(1.4, 1.1, trials=1000, seed=7)

    assert result_a == result_b
    assert sum(result_a["winner"].values()) == 1000
    assert sum(result_a["total_goals"].values()) == 1000


def test_simulation_returns_probability_maps():
    result = run_simulation(1.4, 1.1, trials=1000, seed=3)

    assert set(result["winner_probability"]) == {"home", "draw", "away"}
    assert round(sum(result["winner_probability"].values()), 6) == 1.0
    assert "1-1" in result["score_probability"]
```

- [ ] **Step 2: Run simulation tests and verify failure**

Run: `pytest tests/test_simulation.py -q`

Expected: FAIL because `app.model.simulation` does not exist.

- [ ] **Step 3: Implement simulation module**

Create `app/model/simulation.py`:

```python
from collections import Counter

import numpy as np


def run_simulation(home_xg: float, away_xg: float, trials: int = 10_000, seed: int = 42) -> dict[str, dict[str, float | int]]:
    rng = np.random.default_rng(seed)
    home_goals = rng.poisson(home_xg, trials)
    away_goals = rng.poisson(away_xg, trials)

    winner_counts: Counter[str] = Counter()
    score_counts: Counter[str] = Counter()
    total_counts: Counter[str] = Counter()

    for home, away in zip(home_goals, away_goals):
        if home > away:
            winner_counts["home"] += 1
        elif home == away:
            winner_counts["draw"] += 1
        else:
            winner_counts["away"] += 1

        score_key = f"{int(home)}-{int(away)}"
        total_key = "5+" if home + away >= 5 else str(int(home + away))
        score_counts[score_key] += 1
        total_counts[total_key] += 1

    def probabilities(counter: Counter[str]) -> dict[str, float]:
        return {key: value / trials for key, value in sorted(counter.items())}

    return {
        "winner": dict(winner_counts),
        "score": dict(score_counts),
        "total_goals": dict(total_counts),
        "winner_probability": probabilities(winner_counts),
        "score_probability": probabilities(score_counts),
        "total_goals_probability": probabilities(total_counts),
    }
```

- [ ] **Step 4: Run simulation tests and verify pass**

Run: `pytest tests/test_simulation.py -q`

Expected: `2 passed`.

- [ ] **Step 5: Commit simulation**

Run:

```bash
git add app/model/simulation.py tests/test_simulation.py
git commit -m "feat: add monte carlo simulation"
```

Expected: commit succeeds.

## Task 6: Single-Match Recommendations

**Files:**
- Create: `app/model/recommendations.py`
- Create: `tests/test_recommendations.py`

- [ ] **Step 1: Write recommendation tests**

Create `tests/test_recommendations.py`:

```python
from app.domain import MarketProbability, MatchContext, OddsQuote
from app.model.recommendations import build_recommendations


def test_recommendation_calculates_edge_and_expected_value():
    markets = [
        MarketProbability(market="winner", selection="home", probability=0.56),
        MarketProbability(market="winner", selection="draw", probability=0.24),
        MarketProbability(market="winner", selection="away", probability=0.20),
    ]
    odds = [
        OddsQuote(market="winner", selection="home", decimal_odds=2.1),
        OddsQuote(market="winner", selection="draw", decimal_odds=3.3),
        OddsQuote(market="winner", selection="away", decimal_odds=4.2),
    ]

    picks = build_recommendations("m1", markets, odds, MatchContext(data_quality=0.85))

    assert picks[0].selection == "home"
    assert picks[0].expected_value is not None
    assert picks[0].expected_value > 0
    assert picks[0].risk in {"low", "medium", "high"}


def test_low_data_quality_adds_warning():
    markets = [MarketProbability(market="winner", selection="home", probability=0.54)]
    odds = [OddsQuote(market="winner", selection="home", decimal_odds=2.0)]

    picks = build_recommendations("m1", markets, odds, MatchContext(data_quality=0.45))

    assert any("Data quality" in warning for warning in picks[0].warnings)
```

- [ ] **Step 2: Run recommendation tests and verify failure**

Run: `pytest tests/test_recommendations.py -q`

Expected: FAIL because `app.model.recommendations` does not exist.

- [ ] **Step 3: Implement recommendation engine**

Create `app/model/recommendations.py`:

```python
from app.domain import MarketProbability, MatchContext, OddsQuote, PickRecommendation, RiskLevel
from app.model.odds import expected_value, implied_probability


def risk_from_context(context: MatchContext, edge: float | None) -> RiskLevel:
    uncertainty = (context.lineup_uncertainty + context.tactical_uncertainty) / 2
    if context.data_quality < 0.55 or uncertainty > 0.55:
        return "high"
    if edge is not None and edge > 0.08 and context.data_quality >= 0.75:
        return "low"
    return "medium"


def confidence_from_probability(probability: float, context: MatchContext) -> float:
    return round(min(0.95, probability * 0.75 + context.data_quality * 0.25), 4)


def build_recommendations(
    match_id: str,
    markets: list[MarketProbability],
    odds: list[OddsQuote],
    context: MatchContext,
) -> list[PickRecommendation]:
    odds_by_key = {(quote.market, quote.selection): quote for quote in odds}
    picks: list[PickRecommendation] = []

    for item in markets:
        quote = odds_by_key.get((item.market, item.selection))
        implied = implied_probability(quote.decimal_odds) if quote else None
        edge = item.probability - implied if implied is not None else None
        ev = expected_value(item.probability, quote.decimal_odds) if quote else None
        risk = risk_from_context(context, edge)

        reasons = [f"Model probability is {item.probability:.1%}."]
        warnings: list[str] = []
        if edge is not None:
            reasons.append(f"Model edge versus raw implied probability is {edge:.1%}.")
        if ev is not None:
            reasons.append(f"Expected value is {ev:.1%}.")
        if context.data_quality < 0.6:
            warnings.append("Data quality is low, so this pick needs manual review.")
        if context.lineup_uncertainty > 0.45:
            warnings.append("Lineup uncertainty is elevated.")

        picks.append(
            PickRecommendation(
                match_id=match_id,
                market=item.market,
                selection=item.selection,
                model_probability=item.probability,
                decimal_odds=quote.decimal_odds if quote else None,
                implied_probability=implied,
                edge=edge,
                expected_value=ev,
                confidence=confidence_from_probability(item.probability, context),
                risk=risk,
                reasons=reasons,
                warnings=warnings,
            )
        )

    return sorted(
        picks,
        key=lambda pick: (
            pick.expected_value if pick.expected_value is not None else -1,
            pick.model_probability,
        ),
        reverse=True,
    )
```

- [ ] **Step 4: Run recommendation tests and verify pass**

Run: `pytest tests/test_recommendations.py -q`

Expected: `2 passed`.

- [ ] **Step 5: Commit recommendations**

Run:

```bash
git add app/model/recommendations.py tests/test_recommendations.py
git commit -m "feat: add single match recommendations"
```

Expected: commit succeeds.

## Task 7: Parlay Optimizer

**Files:**
- Create: `app/model/parlay.py`
- Create: `tests/test_parlay.py`

- [ ] **Step 1: Write parlay tests**

Create `tests/test_parlay.py`:

```python
from app.domain import PickRecommendation
from app.model.parlay import build_parlays


def pick(match_id: str, probability: float, odds: float, edge: float, risk: str) -> PickRecommendation:
    return PickRecommendation(
        match_id=match_id,
        market="winner",
        selection="home",
        model_probability=probability,
        decimal_odds=odds,
        implied_probability=1 / odds,
        edge=edge,
        expected_value=probability * odds - 1,
        confidence=probability,
        risk=risk,
        reasons=["test"],
        warnings=[],
    )


def test_balanced_parlay_returns_two_three_and_four_leg_options():
    picks = [
        pick("m1", 0.62, 1.9, 0.09, "low"),
        pick("m2", 0.59, 2.0, 0.08, "medium"),
        pick("m3", 0.55, 2.2, 0.07, "medium"),
        pick("m4", 0.51, 2.5, 0.06, "high"),
    ]

    parlays = build_parlays(picks, strategy="balanced", max_legs=4)

    assert [item.leg_count for item in parlays] == [2, 3, 4]
    assert parlays[0].combined_probability > parlays[-1].combined_probability
    assert parlays[-1].combined_odds > parlays[0].combined_odds


def test_optimizer_uses_strategy_to_change_ordering():
    picks = [
        pick("safe", 0.72, 1.55, 0.07, "low"),
        pick("value", 0.49, 2.75, 0.13, "medium"),
        pick("mid", 0.58, 2.0, 0.08, "medium"),
    ]

    conservative = build_parlays(picks, strategy="conservative", max_legs=2)[0]
    return_seeking = build_parlays(picks, strategy="return_seeking", max_legs=2)[0]

    assert conservative.legs[0].match_id == "safe"
    assert any(leg.match_id == "value" for leg in return_seeking.legs)
```

- [ ] **Step 2: Run parlay tests and verify failure**

Run: `pytest tests/test_parlay.py -q`

Expected: FAIL because `app.model.parlay` does not exist.

- [ ] **Step 3: Implement parlay optimizer**

Create `app/model/parlay.py`:

```python
from functools import reduce
from operator import mul
from typing import Iterable

from app.domain import ParlayLeg, ParlayRecommendation, PickRecommendation, RiskLevel, StrategyName


RISK_SCORE = {"low": 1.0, "medium": 0.6, "high": 0.25}


def score_pick(pick: PickRecommendation, strategy: StrategyName) -> float:
    probability = pick.model_probability
    edge = max(pick.edge or 0.0, 0.0)
    ev = max(pick.expected_value or -1.0, -1.0)
    odds = pick.decimal_odds or 1.0
    low_risk = RISK_SCORE[pick.risk]

    if strategy == "conservative":
        return probability * 0.60 + edge * 0.25 + low_risk * 0.15
    if strategy == "return_seeking":
        return max(ev, 0.0) * 0.50 + min(odds / 5.0, 1.0) * 0.30 + probability * 0.20
    return probability * 0.40 + edge * 0.40 + low_risk * 0.20


def parlay_risk(legs: Iterable[ParlayLeg]) -> RiskLevel:
    risks = [leg.risk for leg in legs]
    if "high" in risks or len(risks) >= 4:
        return "high"
    if "medium" in risks or len(risks) == 3:
        return "medium"
    return "low"


def build_parlays(
    picks: list[PickRecommendation],
    strategy: StrategyName = "balanced",
    max_legs: int = 4,
) -> list[ParlayRecommendation]:
    eligible = [
        pick
        for pick in picks
        if pick.decimal_odds is not None
        and pick.edge is not None
        and pick.edge > 0
        and pick.model_probability >= 0.45
    ]
    ordered = sorted(eligible, key=lambda item: score_pick(item, strategy), reverse=True)

    results: list[ParlayRecommendation] = []
    for leg_count in range(2, min(max_legs, len(ordered)) + 1):
        selected = ordered[:leg_count]
        legs = [
            ParlayLeg(
                match_id=pick.match_id,
                label=f"{pick.match_id} {pick.market} {pick.selection}",
                market=pick.market,
                selection=pick.selection,
                probability=pick.model_probability,
                decimal_odds=pick.decimal_odds or 1.0,
                edge=pick.edge or 0.0,
                risk=pick.risk,
            )
            for pick in selected
        ]
        combined_probability = reduce(mul, (leg.probability for leg in legs), 1.0)
        combined_odds = reduce(mul, (leg.decimal_odds for leg in legs), 1.0)
        ev = combined_probability * combined_odds - 1.0
        risk = parlay_risk(legs)
        explanation = (
            f"{leg_count}-leg combination selected by {strategy} scoring. "
            f"Combined hit probability is {combined_probability:.1%}; expected value is {ev:.1%}."
        )
        results.append(
            ParlayRecommendation(
                strategy=strategy,
                leg_count=leg_count,
                legs=legs,
                combined_probability=combined_probability,
                combined_odds=combined_odds,
                expected_value=ev,
                risk=risk,
                explanation=explanation,
            )
        )

    return results
```

- [ ] **Step 4: Run parlay tests and verify pass**

Run: `pytest tests/test_parlay.py -q`

Expected: `2 passed`.

- [ ] **Step 5: Commit parlay optimizer**

Run:

```bash
git add app/model/parlay.py tests/test_parlay.py
git commit -m "feat: add parlay optimizer"
```

Expected: commit succeeds.

## Task 8: Sample Data Provider And SQLite Snapshots

**Files:**
- Create: `app/data/__init__.py`
- Create: `app/data/sample_data.py`
- Create: `app/data/providers.py`
- Create: `app/data/repository.py`
- Create: `tests/test_data.py`

- [ ] **Step 1: Write data tests**

Create `tests/test_data.py`:

```python
from app.data.providers import SampleDataProvider
from app.data.repository import PredictionRepository


def test_sample_provider_returns_matches():
    provider = SampleDataProvider()

    matches = provider.list_matches()

    assert len(matches) >= 4
    assert matches[0].match_id
    assert matches[0].odds


def test_repository_saves_prediction_snapshot(tmp_path):
    db_path = tmp_path / "predictions.sqlite3"
    repo = PredictionRepository(str(db_path))

    snapshot_id = repo.save_snapshot("m1", {"winner": {"home": 0.5}})
    rows = repo.list_snapshots("m1")

    assert snapshot_id == 1
    assert rows[0]["match_id"] == "m1"
    assert rows[0]["payload"]["winner"]["home"] == 0.5
```

- [ ] **Step 2: Run data tests and verify failure**

Run: `pytest tests/test_data.py -q`

Expected: FAIL because `app.data.providers` does not exist.

- [ ] **Step 3: Implement sample data and repository**

Create `app/data/__init__.py`:

```python
"""Data providers and local persistence."""
```

Create `app/data/sample_data.py`:

```python
from app.domain import MatchContext, MatchInput, OddsQuote, TeamInput


SAMPLE_MATCHES = [
    MatchInput(
        match_id="wc-001",
        competition="World Cup",
        kickoff_utc="2026-07-08T19:00:00Z",
        home=TeamInput(name="France", attack_rating=1.24, defense_rating=0.89, recent_goals_for=1.8, recent_goals_against=0.8),
        away=TeamInput(name="Brazil", attack_rating=1.20, defense_rating=0.92, recent_goals_for=1.7, recent_goals_against=0.9),
        context=MatchContext(data_quality=0.84, lineup_uncertainty=0.22, tactical_uncertainty=0.18, notes=["Neutral venue", "Both sides have strong attacks"]),
        odds=[
            OddsQuote(market="winner", selection="home", decimal_odds=2.22),
            OddsQuote(market="winner", selection="draw", decimal_odds=3.20),
            OddsQuote(market="winner", selection="away", decimal_odds=3.10),
        ],
    ),
    MatchInput(
        match_id="wc-002",
        competition="World Cup",
        kickoff_utc="2026-07-08T22:00:00Z",
        home=TeamInput(name="Argentina", attack_rating=1.18, defense_rating=0.91, recent_goals_for=1.6, recent_goals_against=0.7),
        away=TeamInput(name="Portugal", attack_rating=1.12, defense_rating=0.98, recent_goals_for=1.5, recent_goals_against=1.0),
        context=MatchContext(data_quality=0.78, lineup_uncertainty=0.30, tactical_uncertainty=0.22, notes=["Set-piece matchup is important"]),
        odds=[
            OddsQuote(market="winner", selection="home", decimal_odds=2.05),
            OddsQuote(market="winner", selection="draw", decimal_odds=3.25),
            OddsQuote(market="winner", selection="away", decimal_odds=3.75),
        ],
    ),
    MatchInput(
        match_id="wc-003",
        competition="World Cup",
        kickoff_utc="2026-07-09T19:00:00Z",
        home=TeamInput(name="Spain", attack_rating=1.14, defense_rating=0.88, recent_goals_for=1.5, recent_goals_against=0.8),
        away=TeamInput(name="Netherlands", attack_rating=1.09, defense_rating=0.97, recent_goals_for=1.4, recent_goals_against=1.1),
        context=MatchContext(data_quality=0.76, lineup_uncertainty=0.28, tactical_uncertainty=0.25, notes=["Spain possession edge", "Transition risk for Netherlands"]),
        odds=[
            OddsQuote(market="winner", selection="home", decimal_odds=2.12),
            OddsQuote(market="winner", selection="draw", decimal_odds=3.10),
            OddsQuote(market="winner", selection="away", decimal_odds=3.65),
        ],
    ),
    MatchInput(
        match_id="wc-004",
        competition="World Cup",
        kickoff_utc="2026-07-09T22:00:00Z",
        home=TeamInput(name="England", attack_rating=1.10, defense_rating=0.90, recent_goals_for=1.4, recent_goals_against=0.7),
        away=TeamInput(name="Germany", attack_rating=1.13, defense_rating=0.99, recent_goals_for=1.6, recent_goals_against=1.1),
        context=MatchContext(data_quality=0.80, lineup_uncertainty=0.24, tactical_uncertainty=0.24, notes=["Low-margin knockout profile"]),
        odds=[
            OddsQuote(market="winner", selection="home", decimal_odds=2.35),
            OddsQuote(market="winner", selection="draw", decimal_odds=3.15),
            OddsQuote(market="winner", selection="away", decimal_odds=3.00),
        ],
    ),
]
```

Create `app/data/providers.py`:

```python
from app.data.sample_data import SAMPLE_MATCHES
from app.domain import MatchInput


class SampleDataProvider:
    def list_matches(self) -> list[MatchInput]:
        return SAMPLE_MATCHES

    def get_match(self, match_id: str) -> MatchInput | None:
        for match in SAMPLE_MATCHES:
            if match.match_id == match_id:
                return match
        return None
```

Create `app/data/repository.py`:

```python
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class PredictionRepository:
    def __init__(self, db_path: str = "data/predictions.sqlite3") -> None:
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_db(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS prediction_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    match_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    payload TEXT NOT NULL
                )
                """
            )

    def save_snapshot(self, match_id: str, payload: dict[str, Any]) -> int:
        created_at = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            cursor = connection.execute(
                "INSERT INTO prediction_snapshots (match_id, created_at, payload) VALUES (?, ?, ?)",
                (match_id, created_at, json.dumps(payload)),
            )
            return int(cursor.lastrowid)

    def list_snapshots(self, match_id: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT id, match_id, created_at, payload FROM prediction_snapshots WHERE match_id = ? ORDER BY id DESC",
                (match_id,),
            ).fetchall()
        return [
            {
                "id": row["id"],
                "match_id": row["match_id"],
                "created_at": row["created_at"],
                "payload": json.loads(row["payload"]),
            }
            for row in rows
        ]
```

- [ ] **Step 4: Run data tests and verify pass**

Run: `pytest tests/test_data.py -q`

Expected: `2 passed`.

- [ ] **Step 5: Commit data layer**

Run:

```bash
git add app/data tests/test_data.py
git commit -m "feat: add sample provider and snapshots"
```

Expected: commit succeeds.

## Task 9: Analysis Service And API Routes

**Files:**
- Create: `app/services.py`
- Create: `app/routes.py`
- Modify: `app/main.py`
- Create: `tests/test_api.py`

- [ ] **Step 1: Write API tests**

Create `tests/test_api.py`:

```python
from fastapi.testclient import TestClient

from app.main import app


def test_matches_endpoint_returns_sample_matches():
    client = TestClient(app)

    response = client.get("/api/matches")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) >= 4
    assert payload[0]["match_id"]


def test_match_analysis_endpoint_returns_visualization_payload():
    client = TestClient(app)

    response = client.get("/api/matches/wc-001/analysis")

    assert response.status_code == 200
    payload = response.json()
    assert payload["match"]["match_id"] == "wc-001"
    assert payload["winner_probabilities"]
    assert payload["score_probabilities"]
    assert payload["top_scores"]
    assert payload["recommendations"]


def test_parlay_endpoint_supports_strategy_parameter():
    client = TestClient(app)

    response = client.get("/api/parlays?strategy=balanced")

    assert response.status_code == 200
    payload = response.json()
    assert payload
    assert payload[0]["strategy"] == "balanced"
```

- [ ] **Step 2: Run API tests and verify failure**

Run: `pytest tests/test_api.py -q`

Expected: FAIL because the endpoints do not exist.

- [ ] **Step 3: Implement analysis service**

Create `app/services.py`:

```python
from app.domain import MatchAnalysis, MatchInput, PickRecommendation, StrategyName
from app.model.parlay import build_parlays
from app.model.recommendations import build_recommendations
from app.model.score_model import (
    aggregate_score_matrix,
    estimate_expected_goals,
    half_time_probabilities,
    poisson_score_matrix,
    top_scorelines,
)


def analyze_match(match: MatchInput) -> MatchAnalysis:
    home_xg, away_xg = estimate_expected_goals(match)
    matrix = poisson_score_matrix(home_xg, away_xg, max_goals=8)
    markets = aggregate_score_matrix(matrix)
    half_time = half_time_probabilities(home_xg, away_xg)
    recommendation_markets = markets["winner"] + markets["over_under"]
    recommendations = build_recommendations(match.match_id, recommendation_markets, match.odds, match.context)

    return MatchAnalysis(
        match=match,
        expected_home_goals=home_xg,
        expected_away_goals=away_xg,
        winner_probabilities=markets["winner"],
        half_time_probabilities=half_time,
        total_goal_probabilities=markets["total_goals"],
        over_under_probabilities=markets["over_under"],
        score_probabilities=matrix,
        top_scores=top_scorelines(matrix),
        recommendations=recommendations,
        data_quality=match.context.data_quality,
    )


def collect_best_picks(matches: list[MatchInput]) -> list[PickRecommendation]:
    picks: list[PickRecommendation] = []
    for match in matches:
        analysis = analyze_match(match)
        if analysis.recommendations:
            picks.append(analysis.recommendations[0])
    return picks


def build_parlay_recommendations(matches: list[MatchInput], strategy: StrategyName):
    return build_parlays(collect_best_picks(matches), strategy=strategy, max_legs=4)
```

- [ ] **Step 4: Implement routes and mount static files**

Create `app/routes.py`:

```python
from fastapi import APIRouter, HTTPException, Query

from app.data.providers import SampleDataProvider
from app.domain import StrategyName
from app.services import analyze_match, build_parlay_recommendations


router = APIRouter()
provider = SampleDataProvider()


@router.get("/api/matches")
def list_matches():
    return provider.list_matches()


@router.get("/api/matches/{match_id}/analysis")
def get_match_analysis(match_id: str):
    match = provider.get_match(match_id)
    if match is None:
        raise HTTPException(status_code=404, detail="Match not found")
    return analyze_match(match)


@router.get("/api/parlays")
def get_parlays(strategy: StrategyName = Query(default="balanced")):
    return build_parlay_recommendations(provider.list_matches(), strategy)
```

Modify `app/main.py`:

```python
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.routes import router


app = FastAPI(title="Football Probability Tool")
app.include_router(router)

STATIC_DIR = Path(__file__).parent / "static"


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "football-probability-tool"}


if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")
```

- [ ] **Step 5: Run API tests and verify pass**

Run: `pytest tests/test_api.py -q`

Expected: `3 passed`.

- [ ] **Step 6: Commit API**

Run:

```bash
git add app/services.py app/routes.py app/main.py tests/test_api.py
git commit -m "feat: add analysis api"
```

Expected: commit succeeds.

## Task 10: Static Frontend Shell And Chart Helpers

**Files:**
- Create: `app/static/index.html`
- Create: `app/static/styles.css`
- Create: `app/static/charts.js`
- Create: `app/static/app.js`
- Create: `tests/test_static_assets.py`

- [ ] **Step 1: Write static asset tests**

Create `tests/test_static_assets.py`:

```python
from pathlib import Path


STATIC = Path("app/static")


def test_frontend_files_exist():
    assert (STATIC / "index.html").exists()
    assert (STATIC / "styles.css").exists()
    assert (STATIC / "app.js").exists()
    assert (STATIC / "charts.js").exists()


def test_index_contains_visual_regions():
    html = (STATIC / "index.html").read_text()

    assert "match-list" in html
    assert "score-heatmap" in html
    assert "parlay-results" in html


def test_chart_helpers_export_functions():
    js = (STATIC / "charts.js").read_text()

    assert "export function renderBars" in js
    assert "export function renderHeatmap" in js
    assert "export function renderScatter" in js
```

- [ ] **Step 2: Run static tests and verify failure**

Run: `pytest tests/test_static_assets.py -q`

Expected: FAIL because frontend files do not exist.

- [ ] **Step 3: Create HTML shell**

Create `app/static/index.html`:

```html
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>足球概率分析工具</title>
    <link rel="stylesheet" href="/static/styles.css" />
  </head>
  <body>
    <header class="topbar">
      <div>
        <h1>足球概率分析</h1>
        <p>胜平负、比分、进球数、半场和串关策略</p>
      </div>
      <button id="refresh-button" class="icon-button" title="刷新比赛">↻</button>
    </header>

    <main class="layout">
      <aside class="sidebar">
        <div class="panel">
          <div class="panel-title">今日比赛</div>
          <div id="match-list" class="match-list"></div>
        </div>
      </aside>

      <section class="content">
        <section class="summary-grid">
          <div class="panel metric-panel">
            <div class="panel-title">模型倾向</div>
            <div id="recommendation-summary"></div>
          </div>
          <div class="panel metric-panel">
            <div class="panel-title">胜平负</div>
            <div id="winner-bars"></div>
          </div>
          <div class="panel metric-panel">
            <div class="panel-title">数据质量</div>
            <div id="data-quality"></div>
          </div>
        </section>

        <section class="analysis-grid">
          <div class="panel wide">
            <div class="panel-title">比分热力图</div>
            <div id="score-heatmap"></div>
          </div>
          <div class="panel">
            <div class="panel-title">最可能比分</div>
            <div id="top-scores"></div>
          </div>
          <div class="panel">
            <div class="panel-title">总进球分布</div>
            <div id="goals-bars"></div>
          </div>
          <div class="panel">
            <div class="panel-title">大小球</div>
            <div id="over-under-bars"></div>
          </div>
          <div class="panel">
            <div class="panel-title">半场胜平负</div>
            <div id="half-time-bars"></div>
          </div>
        </section>

        <section class="panel">
          <div class="parlay-header">
            <div class="panel-title">串关推荐</div>
            <div class="segmented">
              <button data-strategy="conservative">稳健</button>
              <button data-strategy="balanced" class="active">平衡</button>
              <button data-strategy="return_seeking">收益</button>
            </div>
          </div>
          <div id="parlay-scatter"></div>
          <div id="parlay-results" class="parlay-results"></div>
        </section>
      </section>
    </main>

    <script type="module" src="/static/app.js"></script>
  </body>
</html>
```

- [ ] **Step 4: Create responsive CSS**

Create `app/static/styles.css`:

```css
:root {
  color-scheme: light;
  --bg: #f4f7f6;
  --panel: #ffffff;
  --text: #17211f;
  --muted: #66716f;
  --line: #d9e1df;
  --green: #227a5c;
  --blue: #2f5f98;
  --amber: #a06a12;
  --red: #b54444;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

.topbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  padding: 18px 24px;
  border-bottom: 1px solid var(--line);
  background: #fbfcfc;
}

h1 {
  margin: 0;
  font-size: 24px;
  letter-spacing: 0;
}

p {
  margin: 4px 0 0;
  color: var(--muted);
}

.layout {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 16px;
  padding: 16px;
}

.sidebar,
.content {
  min-width: 0;
}

.panel {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 14px;
}

.panel-title {
  margin-bottom: 12px;
  color: var(--muted);
  font-size: 13px;
  font-weight: 700;
  text-transform: uppercase;
}

.match-list {
  display: grid;
  gap: 10px;
}

.match-row {
  width: 100%;
  padding: 12px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #ffffff;
  text-align: left;
  cursor: pointer;
}

.match-row.active {
  border-color: var(--green);
  box-shadow: inset 3px 0 0 var(--green);
}

.summary-grid,
.analysis-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 16px;
}

.analysis-grid .wide {
  grid-column: span 2;
}

.icon-button,
.segmented button {
  min-height: 36px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #ffffff;
  color: var(--text);
  cursor: pointer;
}

.segmented {
  display: flex;
  gap: 6px;
}

.segmented button.active {
  background: var(--green);
  color: white;
  border-color: var(--green);
}

.parlay-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.chart-row {
  display: grid;
  grid-template-columns: 90px 1fr 56px;
  align-items: center;
  gap: 8px;
  margin: 8px 0;
  font-size: 13px;
}

.bar-track {
  height: 12px;
  border-radius: 999px;
  background: #edf1f0;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  border-radius: 999px;
  background: var(--green);
}

.heatmap {
  display: grid;
  grid-template-columns: repeat(9, minmax(28px, 1fr));
  gap: 4px;
}

.heat-cell {
  min-height: 34px;
  border-radius: 6px;
  display: grid;
  place-items: center;
  font-size: 11px;
  color: #10201b;
}

.score-list,
.parlay-results {
  display: grid;
  gap: 8px;
}

.pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  border-radius: 999px;
  background: #edf3f1;
  color: var(--green);
  font-size: 12px;
  font-weight: 700;
}

.parlay-card {
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 12px;
}

svg {
  width: 100%;
  height: auto;
}

@media (max-width: 980px) {
  .layout {
    grid-template-columns: 1fr;
  }

  .summary-grid,
  .analysis-grid {
    grid-template-columns: 1fr;
  }

  .analysis-grid .wide {
    grid-column: span 1;
  }
}
```

- [ ] **Step 5: Create chart helper module**

Create `app/static/charts.js`:

```javascript
export function pct(value) {
  return `${(value * 100).toFixed(1)}%`;
}

export function renderBars(node, rows, color = "var(--green)") {
  node.innerHTML = rows
    .map(
      (row) => `
        <div class="chart-row">
          <div>${row.label}</div>
          <div class="bar-track"><div class="bar-fill" style="width:${Math.max(0, Math.min(100, row.value * 100))}%; background:${color}"></div></div>
          <strong>${pct(row.value)}</strong>
        </div>
      `
    )
    .join("");
}

export function renderHeatmap(node, scores) {
  const maxProbability = Math.max(...scores.map((item) => item.probability));
  const visible = scores.filter((item) => item.home_goals <= 8 && item.away_goals <= 8);
  node.innerHTML = `<div class="heatmap">${visible
    .map((item) => {
      const intensity = item.probability / maxProbability;
      const alpha = 0.12 + intensity * 0.78;
      return `<div class="heat-cell" style="background: rgba(34, 122, 92, ${alpha})" title="${item.home_goals}-${item.away_goals} ${pct(item.probability)}">${item.home_goals}-${item.away_goals}<br>${pct(item.probability)}</div>`;
    })
    .join("")}</div>`;
}

export function renderScatter(node, parlays) {
  const width = 640;
  const height = 220;
  const padding = 28;
  const maxEv = Math.max(0.05, ...parlays.map((item) => item.expected_value));
  const points = parlays
    .map((item) => {
      const x = padding + item.combined_probability * (width - padding * 2);
      const y = height - padding - (Math.max(0, item.expected_value) / maxEv) * (height - padding * 2);
      return `<circle cx="${x}" cy="${y}" r="${7 + item.leg_count}" fill="#2f5f98"><title>${item.leg_count}串1 命中率 ${pct(item.combined_probability)} EV ${pct(item.expected_value)}</title></circle>`;
    })
    .join("");

  node.innerHTML = `
    <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="串关风险收益图">
      <line x1="${padding}" y1="${height - padding}" x2="${width - padding}" y2="${height - padding}" stroke="#d9e1df" />
      <line x1="${padding}" y1="${padding}" x2="${padding}" y2="${height - padding}" stroke="#d9e1df" />
      ${points}
      <text x="${padding}" y="${height - 6}" font-size="12">命中率</text>
      <text x="4" y="${padding}" font-size="12">EV</text>
    </svg>
  `;
}
```

- [ ] **Step 6: Create frontend app module**

Create `app/static/app.js`:

```javascript
import { pct, renderBars, renderHeatmap, renderScatter } from "./charts.js";

const state = {
  matches: [],
  selectedMatchId: null,
  strategy: "balanced",
};

const nodes = {
  matchList: document.querySelector("#match-list"),
  refreshButton: document.querySelector("#refresh-button"),
  recommendationSummary: document.querySelector("#recommendation-summary"),
  winnerBars: document.querySelector("#winner-bars"),
  dataQuality: document.querySelector("#data-quality"),
  scoreHeatmap: document.querySelector("#score-heatmap"),
  topScores: document.querySelector("#top-scores"),
  goalsBars: document.querySelector("#goals-bars"),
  overUnderBars: document.querySelector("#over-under-bars"),
  halfTimeBars: document.querySelector("#half-time-bars"),
  parlayScatter: document.querySelector("#parlay-scatter"),
  parlayResults: document.querySelector("#parlay-results"),
};

async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json();
}

function labelSelection(selection) {
  const labels = {
    home: "主胜",
    draw: "平局",
    away: "客胜",
  };
  return labels[selection] || selection.replace("_", " ");
}

function renderMatches() {
  nodes.matchList.innerHTML = state.matches
    .map(
      (match) => `
        <button class="match-row ${match.match_id === state.selectedMatchId ? "active" : ""}" data-match-id="${match.match_id}">
          <strong>${match.home.name} vs ${match.away.name}</strong>
          <div>${match.competition}</div>
          <span class="pill">数据质量 ${pct(match.context.data_quality)}</span>
        </button>
      `
    )
    .join("");
}

function renderRecommendation(analysis) {
  const pick = analysis.recommendations[0];
  if (!pick) {
    nodes.recommendationSummary.innerHTML = "<p>当前模型不建议强行选择。</p>";
    return;
  }
  nodes.recommendationSummary.innerHTML = `
    <h2>${labelSelection(pick.selection)}</h2>
    <p>市场：${pick.market}</p>
    <p>模型概率：${pct(pick.model_probability)}</p>
    <p>期望值：${pick.expected_value === null ? "无赔率" : pct(pick.expected_value)}</p>
    <p>风险：${pick.risk}</p>
  `;
}

function renderAnalysis(analysis) {
  renderRecommendation(analysis);
  renderBars(
    nodes.winnerBars,
    analysis.winner_probabilities.map((item) => ({ label: labelSelection(item.selection), value: item.probability }))
  );
  nodes.dataQuality.innerHTML = `<div class="pill">${pct(analysis.data_quality)}</div><p>预期进球 ${analysis.expected_home_goals.toFixed(2)} - ${analysis.expected_away_goals.toFixed(2)}</p>`;
  renderHeatmap(nodes.scoreHeatmap, analysis.score_probabilities);
  nodes.topScores.innerHTML = `<div class="score-list">${analysis.top_scores
    .map((item) => `<div><strong>${item.home_goals}-${item.away_goals}</strong> ${pct(item.probability)}</div>`)
    .join("")}</div>`;
  renderBars(nodes.goalsBars, analysis.total_goal_probabilities.map((item) => ({ label: item.selection, value: item.probability })), "var(--blue)");
  renderBars(nodes.overUnderBars, analysis.over_under_probabilities.map((item) => ({ label: item.selection, value: item.probability })), "var(--amber)");
  renderBars(nodes.halfTimeBars, analysis.half_time_probabilities.map((item) => ({ label: labelSelection(item.selection), value: item.probability })), "var(--blue)");
}

function renderParlays(parlays) {
  renderScatter(nodes.parlayScatter, parlays);
  nodes.parlayResults.innerHTML = parlays
    .map(
      (parlay) => `
        <article class="parlay-card">
          <h3>${parlay.leg_count}串1 · ${parlay.risk}</h3>
          <p>命中率 ${pct(parlay.combined_probability)} · 总赔率 ${parlay.combined_odds.toFixed(2)} · EV ${pct(parlay.expected_value)}</p>
          <p>${parlay.explanation}</p>
          ${parlay.legs.map((leg) => `<div>${leg.label} · ${pct(leg.probability)} · ${leg.decimal_odds.toFixed(2)}</div>`).join("")}
        </article>
      `
    )
    .join("");
}

async function loadAnalysis(matchId) {
  const analysis = await fetchJson(`/api/matches/${matchId}/analysis`);
  renderAnalysis(analysis);
}

async function loadParlays() {
  const parlays = await fetchJson(`/api/parlays?strategy=${state.strategy}`);
  renderParlays(parlays);
}

async function loadMatches() {
  state.matches = await fetchJson("/api/matches");
  state.selectedMatchId = state.selectedMatchId || state.matches[0]?.match_id;
  renderMatches();
  if (state.selectedMatchId) {
    await loadAnalysis(state.selectedMatchId);
  }
  await loadParlays();
}

nodes.matchList.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-match-id]");
  if (!button) return;
  state.selectedMatchId = button.dataset.matchId;
  renderMatches();
  await loadAnalysis(state.selectedMatchId);
});

document.querySelectorAll("[data-strategy]").forEach((button) => {
  button.addEventListener("click", async () => {
    document.querySelectorAll("[data-strategy]").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    state.strategy = button.dataset.strategy;
    await loadParlays();
  });
});

nodes.refreshButton.addEventListener("click", loadMatches);

loadMatches().catch((error) => {
  document.body.insertAdjacentHTML("afterbegin", `<div class="panel">加载失败：${error.message}</div>`);
});
```

- [ ] **Step 7: Run static tests and full tests**

Run: `pytest -q`

Expected: all tests pass.

- [ ] **Step 8: Commit frontend shell**

Run:

```bash
git add app/static tests/test_static_assets.py
git commit -m "feat: add visual dashboard frontend"
```

Expected: commit succeeds.

## Task 11: Snapshot Endpoint And Manual Analysis Input

**Files:**
- Modify: `app/routes.py`
- Modify: `app/services.py`
- Create: `tests/test_snapshots_and_manual_input.py`

- [ ] **Step 1: Write endpoint tests**

Create `tests/test_snapshots_and_manual_input.py`:

```python
from fastapi.testclient import TestClient

from app.main import app


def test_manual_analysis_accepts_match_payload():
    client = TestClient(app)
    match = client.get("/api/matches").json()[0]
    match["context"]["home_injury_impact"] = 0.12

    response = client.post("/api/analyze", json=match)

    assert response.status_code == 200
    payload = response.json()
    assert payload["match"]["context"]["home_injury_impact"] == 0.12
    assert payload["winner_probabilities"]


def test_snapshot_endpoint_persists_analysis():
    client = TestClient(app)

    response = client.post("/api/matches/wc-001/snapshots")

    assert response.status_code == 200
    payload = response.json()
    assert payload["snapshot_id"] >= 1
```

- [ ] **Step 2: Run endpoint tests and verify failure**

Run: `pytest tests/test_snapshots_and_manual_input.py -q`

Expected: FAIL because `/api/analyze` and snapshot endpoints do not exist.

- [ ] **Step 3: Add manual analysis helper**

Modify `app/services.py` to keep existing functions and add this function at the end:

```python
def analysis_payload(match: MatchInput) -> dict:
    return analyze_match(match).model_dump()
```

- [ ] **Step 4: Add manual and snapshot routes**

Modify `app/routes.py` to include these imports:

```python
from app.data.repository import PredictionRepository
from app.domain import MatchInput, StrategyName
from app.services import analysis_payload, analyze_match, build_parlay_recommendations
```

Add this module-level repository after the provider:

```python
repository = PredictionRepository()
```

Add these endpoints:

```python
@router.post("/api/analyze")
def analyze_manual_match(match: MatchInput):
    return analyze_match(match)


@router.post("/api/matches/{match_id}/snapshots")
def save_match_snapshot(match_id: str):
    match = provider.get_match(match_id)
    if match is None:
        raise HTTPException(status_code=404, detail="Match not found")
    snapshot_id = repository.save_snapshot(match_id, analysis_payload(match))
    return {"snapshot_id": snapshot_id, "match_id": match_id}


@router.get("/api/matches/{match_id}/snapshots")
def list_match_snapshots(match_id: str):
    return repository.list_snapshots(match_id)
```

- [ ] **Step 5: Run endpoint tests and verify pass**

Run: `pytest tests/test_snapshots_and_manual_input.py -q`

Expected: `2 passed`.

- [ ] **Step 6: Run all tests**

Run: `pytest -q`

Expected: all tests pass.

- [ ] **Step 7: Commit snapshot and manual analysis**

Run:

```bash
git add app/routes.py app/services.py tests/test_snapshots_and_manual_input.py
git commit -m "feat: add manual analysis and snapshots"
```

Expected: commit succeeds.

## Task 12: Final Verification And Local Run

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update README with feature summary**

Modify `README.md`:

```markdown
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
pytest -q
```

## Data Sources

Version 1 runs with deterministic sample data and accepts environment-configured API keys through provider modules. Use manual analysis input or replace `SampleDataProvider` with an API-backed provider when stable data access is configured.

## Risk Note

The site is an analysis assistant. It shows probabilities, expected value, and risk, and it does not guarantee match outcomes.
```

- [ ] **Step 2: Run all automated tests**

Run: `pytest -q`

Expected: all tests pass.

- [ ] **Step 3: Start the local server**

Run: `uvicorn app.main:app --host 127.0.0.1 --port 8000`

Expected: server starts and logs `Uvicorn running on http://127.0.0.1:8000`.

- [ ] **Step 4: Verify API manually in another shell**

Run: `curl -s http://127.0.0.1:8000/api/health`

Expected:

```json
{"status":"ok","service":"football-probability-tool"}
```

- [ ] **Step 5: Verify dashboard loads**

Open `http://127.0.0.1:8000` in a browser. Expected: dashboard shows match list, probability bars, score heatmap, goal charts, half-time chart, and parlay cards.

- [ ] **Step 6: Commit README verification update**

Run:

```bash
git add README.md
git commit -m "docs: add local usage guide"
```

Expected: commit succeeds.

## Self-Review Checklist

- Spec coverage: The plan covers single-match analysis, score distribution, total goals, half-time result, odds comparison, recommendations, three parlay strategies, high-visual dashboard, sample data ingestion, manual input, snapshots, and tests.
- Data-source boundary: The plan implements a deterministic sample provider and preserves a provider boundary for API-backed sources.
- Visualization coverage: The plan includes probability bars, heatmap, total-goals bars, over/under bars, half-time bars, and parlay scatter plot.
- Risk language: Recommendation text presents probabilities, expected value, risk, reasons, and warnings without guaranteeing outcomes.
- Tests: The plan includes model, simulation, recommendation, parlay, data, API, manual input, snapshot, and static asset tests.
