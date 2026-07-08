# Probability Model Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the staged full architecture for five-market football advice using official odds, optional team information, correct-score candidate tables, and plain Chinese combined recommendations.

**Architecture:** Add focused model modules for official odds, score candidates, team information, and combined advice, then wire them through `app/services.py` and the existing API payload. Keep the first rollout robust when team/news data is missing: official odds remain usable, missing information is visible, and the UI explains recommendations in plain Chinese.

**Tech Stack:** Python 3.10, FastAPI, Pydantic, existing vanilla HTML/CSS/JS frontend, pytest.

---

## File Structure

- Modify `app/domain.py`: add structured result models for model lines, score candidates, model weights, and team information facts. Keep current fields on `MarketDecision` for backward compatibility while adding the new fields.
- Create `app/model/official_odds_model.py`: normalized market probabilities, official model line selection, market favorite, and return reference.
- Create `app/model/score_candidates.py`: Sporttery score option mapping, grouping concrete model scores into `胜其它/平其它/负其它`, score candidate rows, capped consistency checks, and combined score sorting.
- Create `app/data/team_info.py`: provider protocol and default missing-data provider for team facts, recent form, injuries, motivation, and refresh metadata.
- Create `app/model/combined_advice.py`: five-market advice builder that combines official odds model and team information model into plain Chinese recommendation rows.
- Modify `app/services.py`: replace current `build_decision_comparisons` path with the new combined advice builder while preserving existing analysis payload keys.
- Modify `app/static/app.js`: render five-market conclusion table and expandable score candidate table in plain Chinese.
- Modify `app/static/styles.css`: add table, candidate, and evidence styles.
- Modify tests under `tests/`: add unit and integration coverage for the new models and frontend copy.

## Task 1: Domain Schema For Two-Model Advice

**Files:**
- Modify: `app/domain.py`
- Test: `tests/test_domain.py`

- [ ] **Step 1: Write the failing domain test**

Append to `tests/test_domain.py`:

```python
from app.domain import (
    MarketDecision,
    ModelAdviceLine,
    ModelWeights,
    ScoreCandidate,
    TeamInfoFact,
    TeamInfoSnapshot,
)


def test_market_decision_accepts_two_model_plain_advice_fields():
    official = ModelAdviceLine(
        source="official_odds",
        label="体彩更看好主胜",
        selection="home",
        selection_label="主胜",
        probability=0.62,
        decimal_odds=1.45,
        payout_if_hit_2=2.9,
        confidence_label="中",
        rank=1,
        reasons=["体彩胜平负里主胜赔率最低。"],
    )
    team = ModelAdviceLine(
        source="team_info",
        label="球队资料偏向主胜",
        selection="home",
        selection_label="主胜",
        probability=0.58,
        confidence_label="低",
        rank=1,
        reasons=["球队资料不足，主要参考近期进失球。"],
    )
    score_candidate = ScoreCandidate(
        selection="home_other",
        label="胜其它",
        model_scoreline="4-1",
        official_option_label="胜其它",
        official_probability=0.03,
        team_probability=0.02,
        combined_probability=0.025,
        decimal_odds=35.0,
        payout_if_hit_2=70.0,
        confidence_label="低",
        rank=5,
        support_items=["胜平负支持主胜"],
        conflict_items=[],
        reason="模型比分4-1在体彩中归入胜其它。",
        grouped_scorelines=["4-1", "5-0"],
    )
    decision = MarketDecision(
        market="score",
        market_label="比分",
        official_model=official,
        team_model=team,
        combined_model=official,
        model_weights=ModelWeights(official=0.75, team=0.25),
        score_candidates=[score_candidate],
        missing_info=["伤停信息缺失"],
        advice_level="small",
        advice_label="小额参考",
        summary="综合方案：优先参考主胜方向比分，胜其它仅作娱乐参考。",
    )

    assert decision.official_model.selection_label == "主胜"
    assert decision.team_model.confidence_label == "低"
    assert decision.model_weights.official == 0.75
    assert decision.score_candidates[0].official_option_label == "胜其它"
    assert decision.score_candidates[0].payout_if_hit_2 == 70.0


def test_team_info_snapshot_exposes_missing_sources():
    snapshot = TeamInfoSnapshot(
        match_id="m1",
        facts=[
            TeamInfoFact(
                category="recent_form",
                team="home",
                title="近况未抓到",
                summary="未找到可用近况数据。",
                source_name="system",
                confidence=0.0,
                affects_model=False,
            )
        ],
        quality=0.0,
        missing_info=["球队近况未抓到", "伤停信息缺失"],
    )

    assert snapshot.missing_info == ["球队近况未抓到", "伤停信息缺失"]
    assert snapshot.facts[0].affects_model is False
```

- [ ] **Step 2: Run domain test and verify failure**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest tests/test_domain.py::test_market_decision_accepts_two_model_plain_advice_fields tests/test_domain.py::test_team_info_snapshot_exposes_missing_sources -q
```

Expected: FAIL because `ModelAdviceLine`, `ModelWeights`, `ScoreCandidate`, `TeamInfoFact`, and `TeamInfoSnapshot` are not defined.

- [ ] **Step 3: Add domain models**

Modify `app/domain.py` after `DecisionOption`:

```python
class ModelAdviceLine(BaseModel):
    source: Literal["official_odds", "team_info", "combined"]
    label: str
    selection: str | None = None
    selection_label: str | None = None
    probability: float | None = Field(default=None, ge=0, le=1)
    decimal_odds: float | None = Field(default=None, gt=1)
    payout_if_hit_2: float | None = Field(default=None, ge=0)
    confidence_label: str = "低"
    rank: int | None = Field(default=None, ge=1)
    reasons: list[str] = Field(default_factory=list)


class ModelWeights(BaseModel):
    official: float = Field(ge=0, le=1)
    team: float = Field(ge=0, le=1)


class ScoreCandidate(BaseModel):
    selection: str
    label: str
    model_scoreline: str | None = None
    official_option_label: str | None = None
    official_probability: float | None = Field(default=None, ge=0, le=1)
    team_probability: float | None = Field(default=None, ge=0, le=1)
    combined_probability: float | None = Field(default=None, ge=0, le=1)
    decimal_odds: float | None = Field(default=None, gt=1)
    payout_if_hit_2: float | None = Field(default=None, ge=0)
    confidence_label: str = "低"
    rank: int = Field(ge=1)
    support_items: list[str] = Field(default_factory=list)
    conflict_items: list[str] = Field(default_factory=list)
    reason: str
    grouped_scorelines: list[str] = Field(default_factory=list)


class TeamInfoFact(BaseModel):
    category: Literal["recent_form", "injury", "motivation", "news", "schedule"]
    team: Literal["home", "away", "match"]
    title: str
    summary: str
    source_name: str
    source_url: str | None = None
    updated_at: str | None = None
    confidence: float = Field(ge=0, le=1)
    affects_model: bool = False


class TeamInfoSnapshot(BaseModel):
    match_id: str
    facts: list[TeamInfoFact] = Field(default_factory=list)
    quality: float = Field(ge=0, le=1)
    missing_info: list[str] = Field(default_factory=list)
    updated_at: str | None = None
```

Modify `MarketDecision` in `app/domain.py` by adding these fields before `model_suggestions`:

```python
    official_model: ModelAdviceLine | None = None
    team_model: ModelAdviceLine | None = None
    combined_model: ModelAdviceLine | None = None
    model_weights: ModelWeights | None = None
    score_candidates: list[ScoreCandidate] = Field(default_factory=list)
```

- [ ] **Step 4: Run domain test and verify pass**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest tests/test_domain.py::test_market_decision_accepts_two_model_plain_advice_fields tests/test_domain.py::test_team_info_snapshot_exposes_missing_sources -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/domain.py tests/test_domain.py
git commit -m "feat: add two-model advice domain schema"
```

## Task 2: Official Odds Model

**Files:**
- Create: `app/model/official_odds_model.py`
- Test: `tests/test_official_odds_model.py`

- [ ] **Step 1: Write failing official odds tests**

Create `tests/test_official_odds_model.py`:

```python
import pytest

from app.domain import OddsQuote
from app.model.official_odds_model import (
    best_return_reference,
    market_favorite,
    normalized_official_probabilities,
    official_model_line,
)


def q(market: str, selection: str, odds: float, label: str | None = None) -> OddsQuote:
    return OddsQuote(
        market=market,
        selection=selection,
        decimal_odds=odds,
        source="sporttery",
        selection_label=label or selection,
    )


def test_score_probabilities_include_other_options():
    quotes = [
        q("score", "1-0", 6.5, "1-0"),
        q("score", "2-0", 6.25, "2-0"),
        q("score", "home_other", 35.0, "胜其它"),
        q("score", "draw_other", 120.0, "平其它"),
        q("score", "away_other", 80.0, "负其它"),
    ]

    probabilities = normalized_official_probabilities(quotes)

    assert set(probabilities) == {"1-0", "2-0", "home_other", "draw_other", "away_other"}
    assert sum(probabilities.values()) == pytest.approx(1.0)
    assert probabilities["2-0"] > probabilities["home_other"]


def test_market_favorite_uses_normalized_probability_and_returns_two_yuan_payout():
    quotes = [q("winner", "home", 1.4, "主胜"), q("winner", "draw", 4.0, "平局"), q("winner", "away", 7.0, "客胜")]

    favorite = market_favorite("winner", quotes)

    assert favorite.selection == "home"
    assert favorite.selection_label == "主胜"
    assert favorite.payout_if_hit_2 == 2.8
    assert favorite.probability is not None


def test_best_return_reference_uses_reasonable_model_candidates():
    quotes = [q("score", "1-0", 6.0, "1-0"), q("score", "2-0", 8.0, "2-0"), q("score", "0-2", 60.0, "0-2")]
    model_probabilities = {"1-0": 0.12, "2-0": 0.10, "0-2": 0.01}

    reference = best_return_reference("score", quotes, model_probabilities)

    assert reference.selection == "2-0"
    assert reference.selection_label == "2-0"
    assert reference.payout_if_hit_2 == 16.0


def test_official_model_line_uses_plain_chinese_label():
    quotes = [q("total_goals", "2", 3.4, "2球"), q("total_goals", "3", 3.2, "3球")]

    line = official_model_line("total_goals", quotes)

    assert line.source == "official_odds"
    assert line.selection_label == "3球"
    assert "体彩更看好" in line.label
    assert line.payout_if_hit_2 == 6.4
```

- [ ] **Step 2: Run official odds tests and verify failure**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest tests/test_official_odds_model.py -q
```

Expected: FAIL because `app.model.official_odds_model` does not exist.

- [ ] **Step 3: Implement official odds model**

Create `app/model/official_odds_model.py`:

```python
from app.domain import ModelAdviceLine, OddsQuote
from app.model.odds import implied_probability


def payout_if_hit_2(decimal_odds: float | None) -> float | None:
    if decimal_odds is None:
        return None
    return round(decimal_odds * 2, 2)


def quote_label(quote: OddsQuote) -> str:
    return quote.selection_label or quote.selection


def normalized_official_probabilities(quotes: list[OddsQuote]) -> dict[str, float]:
    raw = {quote.selection: implied_probability(quote.decimal_odds) for quote in quotes if quote.decimal_odds > 1}
    total = sum(raw.values())
    if total <= 0:
        return {}
    return {selection: probability / total for selection, probability in raw.items()}


def market_favorite(market: str, quotes: list[OddsQuote]) -> ModelAdviceLine | None:
    probabilities = normalized_official_probabilities(quotes)
    if not probabilities:
        return None
    quote_by_selection = {quote.selection: quote for quote in quotes}
    selection = max(probabilities, key=probabilities.get)
    quote = quote_by_selection[selection]
    return ModelAdviceLine(
        source="official_odds",
        label=f"体彩更看好{quote_label(quote)}",
        selection=quote.selection,
        selection_label=quote_label(quote),
        probability=probabilities[selection],
        decimal_odds=quote.decimal_odds,
        payout_if_hit_2=payout_if_hit_2(quote.decimal_odds),
        confidence_label="中",
        rank=1,
        reasons=[f"{quote_label(quote)}在{market}玩法中市场概率最高。"],
    )


def best_return_reference(
    market: str,
    quotes: list[OddsQuote],
    model_probabilities: dict[str, float],
    min_probability_ratio: float = 0.35,
) -> ModelAdviceLine | None:
    if not quotes or not model_probabilities:
        return None
    max_probability = max(model_probabilities.values()) if model_probabilities else 0.0
    if max_probability <= 0:
        return None
    quote_by_selection = {quote.selection: quote for quote in quotes}
    candidates = []
    for selection, probability in model_probabilities.items():
        quote = quote_by_selection.get(selection)
        if quote is None or probability < max_probability * min_probability_ratio:
            continue
        candidates.append((quote, probability, probability * quote.decimal_odds))
    if not candidates:
        return None
    quote, probability, _ = max(candidates, key=lambda item: item[2])
    return ModelAdviceLine(
        source="official_odds",
        label=f"回报参考{quote_label(quote)}",
        selection=quote.selection,
        selection_label=quote_label(quote),
        probability=probability,
        decimal_odds=quote.decimal_odds,
        payout_if_hit_2=payout_if_hit_2(quote.decimal_odds),
        confidence_label="中",
        rank=None,
        reasons=[f"{quote_label(quote)}在模型候选中2元返还更高。"],
    )


def official_model_line(market: str, quotes: list[OddsQuote]) -> ModelAdviceLine | None:
    return market_favorite(market, quotes)
```

- [ ] **Step 4: Run official odds tests and verify pass**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest tests/test_official_odds_model.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/model/official_odds_model.py tests/test_official_odds_model.py
git commit -m "feat: add official odds model"
```

## Task 3: Correct Score Candidate Model

**Files:**
- Create: `app/model/score_candidates.py`
- Test: `tests/test_score_candidates.py`

- [ ] **Step 1: Write failing score candidate tests**

Create `tests/test_score_candidates.py`:

```python
import pytest

from app.domain import MarketProbability, OddsQuote, ScoreProbability
from app.model.score_candidates import (
    build_score_candidates,
    score_selection_for_sporttery,
    team_score_probabilities_by_official_option,
)


def score(home: int, away: int, probability: float) -> ScoreProbability:
    return ScoreProbability(home_goals=home, away_goals=away, probability=probability)


def q(selection: str, odds: float, label: str | None = None) -> OddsQuote:
    return OddsQuote(market="score", selection=selection, decimal_odds=odds, source="sporttery", selection_label=label or selection)


def test_missing_concrete_score_maps_to_correct_other_option():
    official = {quote.selection for quote in [q("1-0", 6.5), q("2-0", 6.25), q("home_other", 35, "胜其它")]}

    assert score_selection_for_sporttery(4, 1, official) == "home_other"
    assert score_selection_for_sporttery(4, 4, official) == "draw_other"
    assert score_selection_for_sporttery(1, 5, official) == "away_other"


def test_team_score_distribution_groups_other_scorelines():
    quotes = [q("1-0", 6.5), q("home_other", 35, "胜其它"), q("draw_other", 120, "平其它"), q("away_other", 80, "负其它")]
    matrix = [score(1, 0, 0.12), score(4, 1, 0.03), score(5, 0, 0.02), score(0, 2, 0.04)]

    grouped = team_score_probabilities_by_official_option(matrix, quotes)

    assert grouped["1-0"] == pytest.approx(0.12)
    assert grouped["home_other"] == pytest.approx(0.05)
    assert grouped["away_other"] == pytest.approx(0.04)


def test_build_score_candidates_includes_three_probabilities_and_payouts():
    quotes = [
        q("1-0", 6.5, "1-0"),
        q("2-0", 6.25, "2-0"),
        q("home_other", 35, "胜其它"),
        q("draw_other", 120, "平其它"),
        q("away_other", 80, "负其它"),
    ]
    team_probabilities = {"1-0": 0.12, "2-0": 0.10, "home_other": 0.05}
    winner = [MarketProbability(market="winner", selection="home", probability=0.62)]
    total_goals = {"1": 0.22, "2": 0.31, "3": 0.20, "4": 0.12}

    candidates = build_score_candidates(
        quotes=quotes,
        team_probabilities=team_probabilities,
        winner_probabilities={item.selection: item.probability for item in winner},
        handicap_probabilities={"home": 0.44, "draw": 0.25, "away": 0.31},
        total_goal_probabilities=total_goals,
        half_full_probabilities={"home_home": 0.35},
        official_weight=0.75,
        team_weight=0.25,
    )

    assert candidates[0].combined_probability is not None
    assert candidates[0].payout_if_hit_2 is not None
    assert candidates[0].support_items
    assert any(candidate.selection == "home_other" for candidate in candidates)
    assert all(candidate.rank >= 1 for candidate in candidates)
```

- [ ] **Step 2: Run score candidate tests and verify failure**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest tests/test_score_candidates.py -q
```

Expected: FAIL because `app.model.score_candidates` does not exist.

- [ ] **Step 3: Implement score candidate helpers**

Create `app/model/score_candidates.py`:

```python
from collections import defaultdict

from app.domain import OddsQuote, ScoreCandidate, ScoreProbability
from app.model.official_odds_model import normalized_official_probabilities, payout_if_hit_2


OTHER_LABELS = {
    "home_other": "胜其它",
    "draw_other": "平其它",
    "away_other": "负其它",
}


def score_selection_for_sporttery(home_goals: int, away_goals: int, official_selections: set[str]) -> str:
    concrete = f"{home_goals}-{away_goals}"
    if concrete in official_selections:
        return concrete
    if home_goals > away_goals:
        return "home_other"
    if home_goals == away_goals:
        return "draw_other"
    return "away_other"


def team_score_probabilities_by_official_option(
    scores: list[ScoreProbability],
    quotes: list[OddsQuote],
) -> dict[str, float]:
    official_selections = {quote.selection for quote in quotes}
    grouped: dict[str, float] = defaultdict(float)
    for score in scores:
        selection = score_selection_for_sporttery(score.home_goals, score.away_goals, official_selections)
        grouped[selection] += score.probability
    return dict(grouped)


def score_outcome(selection: str) -> str | None:
    if selection == "home_other":
        return "home"
    if selection == "draw_other":
        return "draw"
    if selection == "away_other":
        return "away"
    if "-" not in selection:
        return None
    home, away = selection.split("-", 1)
    if not home.isdigit() or not away.isdigit():
        return None
    home_goals, away_goals = int(home), int(away)
    if home_goals > away_goals:
        return "home"
    if home_goals < away_goals:
        return "away"
    return "draw"


def score_total_goals(selection: str) -> int | None:
    if "-" not in selection:
        return None
    home, away = selection.split("-", 1)
    if not home.isdigit() or not away.isdigit():
        return None
    return int(home) + int(away)


def confidence_label(probability: float | None, support_count: int, conflict_count: int) -> str:
    if probability is None:
        return "低"
    if probability >= 0.12 and support_count >= 2 and conflict_count == 0:
        return "高"
    if probability >= 0.07 and support_count >= 1:
        return "中"
    return "低"


def consistency_items(
    selection: str,
    winner_probabilities: dict[str, float],
    handicap_probabilities: dict[str, float],
    total_goal_probabilities: dict[str, float],
    half_full_probabilities: dict[str, float],
) -> tuple[list[str], list[str]]:
    support: list[str] = []
    conflict: list[str] = []
    outcome = score_outcome(selection)
    total = score_total_goals(selection)

    if outcome and winner_probabilities:
        top_winner = max(winner_probabilities, key=winner_probabilities.get)
        (support if top_winner == outcome else conflict).append(f"胜平负{'支持' if top_winner == outcome else '不支持'}{selection}")
    if outcome and handicap_probabilities:
        top_handicap = max(handicap_probabilities, key=handicap_probabilities.get)
        (support if top_handicap == outcome else conflict).append(f"让球方向{'支持' if top_handicap == outcome else '有分歧'}")
    if total is not None and total_goal_probabilities:
        top_total = max(total_goal_probabilities, key=total_goal_probabilities.get)
        total_key = str(total) if str(total) in total_goal_probabilities else "7+"
        (support if top_total == total_key else conflict).append(f"总进球{'支持' if top_total == total_key else '更偏向' + top_total + '球'}")
    if outcome and half_full_probabilities:
        top_half_full = max(half_full_probabilities, key=half_full_probabilities.get)
        if top_half_full.endswith(outcome):
            support.append("半全场方向支持")
        else:
            conflict.append("半全场方向有分歧")
    return support, conflict


def capped_consistency_multiplier(support_count: int, conflict_count: int) -> float:
    raw = 1.0 + min(support_count * 0.04, 0.16) - min(conflict_count * 0.05, 0.20)
    return max(0.80, min(1.20, raw))


def build_score_candidates(
    quotes: list[OddsQuote],
    team_probabilities: dict[str, float],
    winner_probabilities: dict[str, float],
    handicap_probabilities: dict[str, float],
    total_goal_probabilities: dict[str, float],
    half_full_probabilities: dict[str, float],
    official_weight: float,
    team_weight: float,
) -> list[ScoreCandidate]:
    official_probabilities = normalized_official_probabilities(quotes)
    quote_by_selection = {quote.selection: quote for quote in quotes}
    selections = set(official_probabilities) | set(team_probabilities)
    rows = []
    for selection in selections:
        quote = quote_by_selection.get(selection)
        label = quote.selection_label if quote and quote.selection_label else OTHER_LABELS.get(selection, selection)
        official_probability = official_probabilities.get(selection)
        team_probability = team_probabilities.get(selection)
        base_probability = 0.0
        if official_probability is not None:
            base_probability += official_probability * official_weight
        if team_probability is not None:
            base_probability += team_probability * team_weight
        support, conflict = consistency_items(
            selection,
            winner_probabilities,
            handicap_probabilities,
            total_goal_probabilities,
            half_full_probabilities,
        )
        combined = max(0.0, min(1.0, base_probability * capped_consistency_multiplier(len(support), len(conflict))))
        rows.append(
            ScoreCandidate(
                selection=selection,
                label=label,
                official_option_label=label,
                official_probability=official_probability,
                team_probability=team_probability,
                combined_probability=combined,
                decimal_odds=quote.decimal_odds if quote else None,
                payout_if_hit_2=payout_if_hit_2(quote.decimal_odds) if quote else None,
                confidence_label=confidence_label(combined, len(support), len(conflict)),
                rank=1,
                support_items=support,
                conflict_items=conflict,
                reason=f"{label}综合参考概率为{combined:.1%}，{len(support)}项支持，{len(conflict)}项分歧。",
                grouped_scorelines=[],
            )
        )
    ordered = sorted(rows, key=lambda row: (row.combined_probability or 0.0), reverse=True)
    return [row.model_copy(update={"rank": index + 1}) for index, row in enumerate(ordered)]
```

- [ ] **Step 4: Run score candidate tests and verify pass**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest tests/test_score_candidates.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/model/score_candidates.py tests/test_score_candidates.py
git commit -m "feat: add correct score candidate model"
```

## Task 4: Team Information Provider Contract

**Files:**
- Create: `app/data/team_info.py`
- Test: `tests/test_team_info.py`

- [ ] **Step 1: Write failing team information tests**

Create `tests/test_team_info.py`:

```python
from app.data.team_info import MissingTeamInfoProvider, team_model_weight
from app.domain import MatchInput, TeamInput


def match() -> MatchInput:
    return MatchInput(
        match_id="m1",
        competition="世界杯",
        kickoff_utc="2026-07-10T04:00:00Z",
        home=TeamInput(name="法国", attack_rating=1.1, defense_rating=0.9),
        away=TeamInput(name="摩洛哥", attack_rating=0.9, defense_rating=1.0),
    )


def test_missing_team_info_provider_returns_visible_missing_information():
    snapshot = MissingTeamInfoProvider().snapshot(match())

    assert snapshot.match_id == "m1"
    assert snapshot.quality == 0.0
    assert "球队近况未抓到" in snapshot.missing_info
    assert "伤停信息缺失" in snapshot.missing_info
    assert all(fact.affects_model is False for fact in snapshot.facts)


def test_team_model_weight_is_dynamic_from_quality():
    missing = MissingTeamInfoProvider().snapshot(match())

    assert team_model_weight(missing) == 0.0
```

- [ ] **Step 2: Run team information tests and verify failure**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest tests/test_team_info.py -q
```

Expected: FAIL because `app.data.team_info` does not exist.

- [ ] **Step 3: Implement missing-data provider contract**

Create `app/data/team_info.py`:

```python
from typing import Protocol

from app.domain import MatchInput, TeamInfoFact, TeamInfoSnapshot


class TeamInfoProvider(Protocol):
    def snapshot(self, match: MatchInput) -> TeamInfoSnapshot:
        ...


class MissingTeamInfoProvider:
    def snapshot(self, match: MatchInput) -> TeamInfoSnapshot:
        return TeamInfoSnapshot(
            match_id=match.match_id,
            facts=[
                TeamInfoFact(
                    category="recent_form",
                    team="match",
                    title="球队近况未抓到",
                    summary="当前没有可用的近5-10场球队资料。",
                    source_name="system",
                    confidence=0.0,
                    affects_model=False,
                ),
                TeamInfoFact(
                    category="injury",
                    team="match",
                    title="伤停信息缺失",
                    summary="当前没有可信伤停来源进入模型。",
                    source_name="system",
                    confidence=0.0,
                    affects_model=False,
                ),
                TeamInfoFact(
                    category="motivation",
                    team="match",
                    title="赛程战意缺失",
                    summary="当前没有可信赛程战意信息进入模型。",
                    source_name="system",
                    confidence=0.0,
                    affects_model=False,
                ),
            ],
            quality=0.0,
            missing_info=["球队近况未抓到", "伤停信息缺失", "赛程战意缺失"],
        )


def team_model_weight(snapshot: TeamInfoSnapshot) -> float:
    if snapshot.quality <= 0:
        return 0.0
    return max(0.10, min(0.45, snapshot.quality * 0.45))
```

- [ ] **Step 4: Run team information tests and verify pass**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest tests/test_team_info.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/data/team_info.py tests/test_team_info.py
git commit -m "feat: add team information provider contract"
```

## Task 5: Combined Five-Market Advice Builder

**Files:**
- Create: `app/model/combined_advice.py`
- Modify: `app/services.py`
- Test: `tests/test_services.py`

- [ ] **Step 1: Write failing service integration tests**

Append to `tests/test_services.py`:

```python
def test_analysis_returns_two_model_fields_and_score_candidates():
    match = MatchInput(
        match_id="m-score",
        competition="世界杯",
        kickoff_utc="2026-07-10T04:00:00Z",
        home=TeamInput(name="法国", attack_rating=1.18, defense_rating=0.92),
        away=TeamInput(name="摩洛哥", attack_rating=0.91, defense_rating=1.05),
        context=MatchContext(data_quality=0.80, notes=["让球 -1"]),
        odds=[
            OddsQuote(market="winner", selection="home", decimal_odds=1.40, source="sporttery", selection_label="主胜"),
            OddsQuote(market="winner", selection="draw", decimal_odds=3.85, source="sporttery", selection_label="平局"),
            OddsQuote(market="winner", selection="away", decimal_odds=6.45, source="sporttery", selection_label="客胜"),
            OddsQuote(market="handicap_winner", selection="home", decimal_odds=2.55, source="sporttery", selection_label="让球主胜"),
            OddsQuote(market="handicap_winner", selection="draw", decimal_odds=3.35, source="sporttery", selection_label="让球平"),
            OddsQuote(market="handicap_winner", selection="away", decimal_odds=2.30, source="sporttery", selection_label="让球客胜"),
            OddsQuote(market="score", selection="1-0", decimal_odds=6.5, source="sporttery", selection_label="1-0"),
            OddsQuote(market="score", selection="2-0", decimal_odds=6.25, source="sporttery", selection_label="2-0"),
            OddsQuote(market="score", selection="home_other", decimal_odds=35.0, source="sporttery", selection_label="胜其它"),
            OddsQuote(market="score", selection="draw_other", decimal_odds=120.0, source="sporttery", selection_label="平其它"),
            OddsQuote(market="score", selection="away_other", decimal_odds=80.0, source="sporttery", selection_label="负其它"),
            OddsQuote(market="total_goals", selection="1", decimal_odds=4.20, source="sporttery", selection_label="1球"),
            OddsQuote(market="total_goals", selection="2", decimal_odds=3.20, source="sporttery", selection_label="2球"),
            OddsQuote(market="total_goals", selection="3", decimal_odds=3.80, source="sporttery", selection_label="3球"),
            OddsQuote(market="half_full", selection="home_home", decimal_odds=2.40, source="sporttery", selection_label="胜胜"),
            OddsQuote(market="half_full", selection="draw_home", decimal_odds=4.40, source="sporttery", selection_label="平胜"),
        ],
    )

    analysis = analyze_match(match)
    decisions = {decision.market: decision for decision in analysis.decision_comparisons}
    score_decision = decisions["score"]

    assert score_decision.official_model is not None
    assert score_decision.team_model is not None
    assert score_decision.combined_model is not None
    assert score_decision.model_weights is not None
    assert score_decision.score_candidates
    assert any(candidate.selection == "home_other" for candidate in score_decision.score_candidates)
    assert "球队近况未抓到" in score_decision.missing_info
    assert "2元" in score_decision.summary


def test_different_score_odds_produce_different_official_score_recommendations():
    base = MatchInput(
        match_id="m-a",
        competition="世界杯",
        kickoff_utc="2026-07-10T04:00:00Z",
        home=TeamInput(name="A", attack_rating=1.0, defense_rating=1.0),
        away=TeamInput(name="B", attack_rating=1.0, defense_rating=1.0),
        context=MatchContext(notes=["让球 0"]),
        odds=[
            OddsQuote(market="winner", selection="home", decimal_odds=2.2, source="sporttery", selection_label="主胜"),
            OddsQuote(market="winner", selection="draw", decimal_odds=3.0, source="sporttery", selection_label="平局"),
            OddsQuote(market="winner", selection="away", decimal_odds=3.1, source="sporttery", selection_label="客胜"),
            OddsQuote(market="score", selection="1-0", decimal_odds=5.0, source="sporttery", selection_label="1-0"),
            OddsQuote(market="score", selection="2-1", decimal_odds=9.0, source="sporttery", selection_label="2-1"),
            OddsQuote(market="score", selection="draw_other", decimal_odds=100.0, source="sporttery", selection_label="平其它"),
        ],
    )
    changed = base.model_copy(
        update={
            "match_id": "m-b",
            "odds": [
                quote.model_copy(update={"decimal_odds": 4.5}) if quote.market == "score" and quote.selection == "2-1" else quote
                for quote in base.odds
            ],
        }
    )

    first_score = next(decision for decision in analyze_match(base).decision_comparisons if decision.market == "score")
    second_score = next(decision for decision in analyze_match(changed).decision_comparisons if decision.market == "score")

    assert first_score.official_model.selection == "1-0"
    assert second_score.official_model.selection == "2-1"
```

- [ ] **Step 2: Run service integration tests and verify failure**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest tests/test_services.py::test_analysis_returns_two_model_fields_and_score_candidates tests/test_services.py::test_different_score_odds_produce_different_official_score_recommendations -q
```

Expected: FAIL because `analyze_match` still returns old decision fields only.

- [ ] **Step 3: Implement combined advice builder**

Create `app/model/combined_advice.py`:

```python
from app.data.team_info import MissingTeamInfoProvider, TeamInfoProvider, team_model_weight
from app.domain import (
    MarketDecision,
    MatchInput,
    ModelAdviceLine,
    ModelWeights,
    OddsQuote,
    ScoreProbability,
)
from app.model.official_odds_model import best_return_reference, market_favorite, payout_if_hit_2
from app.model.recommendations import market_label
from app.model.score_candidates import build_score_candidates, team_score_probabilities_by_official_option


DECISION_MARKETS = ("winner", "handicap_winner", "score", "total_goals", "half_full")


def official_quotes(odds: list[OddsQuote], market: str) -> list[OddsQuote]:
    return [quote for quote in odds if quote.market == market and quote.source == "sporttery"]


def plain_missing_team_line(market: str, missing_info: list[str]) -> ModelAdviceLine:
    return ModelAdviceLine(
        source="team_info",
        label="球队资料缺失",
        selection=None,
        selection_label=None,
        probability=None,
        confidence_label="低",
        reasons=[f"{market_label(market)}暂时没有足够球队资料，综合建议主要依据体彩赔率。", *missing_info],
    )


def top_team_line(market: str, probabilities: dict[str, float], missing_info: list[str]) -> ModelAdviceLine:
    if not probabilities:
        return plain_missing_team_line(market, missing_info)
    selection, probability = max(probabilities.items(), key=lambda item: item[1])
    return ModelAdviceLine(
        source="team_info",
        label=f"球队资料模型看好{selection}",
        selection=selection,
        selection_label=selection,
        probability=probability,
        confidence_label="低" if missing_info else "中",
        rank=1,
        reasons=["根据当前球队资料模型得到的参考方向。"] if not missing_info else [*missing_info],
    )


def combine_lines(
    market: str,
    official: ModelAdviceLine | None,
    team: ModelAdviceLine | None,
    official_weight: float,
    team_weight: float,
) -> ModelAdviceLine:
    chosen = official or team
    if chosen is None:
        return ModelAdviceLine(
            source="combined",
            label="综合暂时没有明确方向",
            confidence_label="低",
            reasons=["官方赔率和球队资料都不足。"],
        )
    return ModelAdviceLine(
        source="combined",
        label=f"综合参考{chosen.selection_label or chosen.label}",
        selection=chosen.selection,
        selection_label=chosen.selection_label,
        probability=chosen.probability,
        decimal_odds=chosen.decimal_odds,
        payout_if_hit_2=chosen.payout_if_hit_2,
        confidence_label=chosen.confidence_label,
        rank=chosen.rank,
        reasons=[f"当前权重：赔率模型{official_weight:.0%}，球队资料模型{team_weight:.0%}。"],
    )


def advice_level_and_label(combined: ModelAdviceLine, missing_info: list[str], is_score: bool) -> tuple[str, str]:
    if is_score and missing_info:
        return "small", "仅作娱乐参考"
    if missing_info:
        return "balanced", "谨慎"
    if combined.confidence_label == "高":
        return "stable", "建议"
    if combined.confidence_label == "中":
        return "small", "小额参考"
    return "balanced", "谨慎"


def summary_for_market(
    market: str,
    official: ModelAdviceLine | None,
    team: ModelAdviceLine | None,
    combined: ModelAdviceLine,
    best_return: ModelAdviceLine | None,
    advice_label: str,
) -> str:
    official_text = f"体彩更看好{official.selection_label}，赔率{official.decimal_odds:.2f}，2元一注中出返还{official.payout_if_hit_2:.2f}元。" if official and official.decimal_odds else "体彩赔率参考不足。"
    team_text = f"球队资料模型看好{team.selection_label or team.label}。" if team and team.selection else "球队资料缺失。"
    return_text = f"回报参考{best_return.selection_label}，2元一注中出返还{best_return.payout_if_hit_2:.2f}元。" if best_return and best_return.payout_if_hit_2 else "回报参考不足。"
    return f"{official_text}{team_text}{return_text}综合方案：{combined.selection_label or combined.label}，{advice_label}。"


def build_market_decisions(
    match: MatchInput,
    model_probabilities: dict[str, dict[str, float]],
    score_matrix: list[ScoreProbability],
    team_provider: TeamInfoProvider | None = None,
) -> list[MarketDecision]:
    snapshot = (team_provider or MissingTeamInfoProvider()).snapshot(match)
    team_weight = team_model_weight(snapshot)
    official_weight = 1.0 - team_weight
    decisions: list[MarketDecision] = []
    for market in DECISION_MARKETS:
        quotes = official_quotes(match.odds, market)
        missing = list(snapshot.missing_info)
        if not quotes:
            missing.append(f"官方{market_label(market)}赔率缺失")
        official = market_favorite(market, quotes)
        team = top_team_line(market, model_probabilities.get(market, {}), snapshot.missing_info)
        best_return = best_return_reference(market, quotes, model_probabilities.get(market, {}))
        score_candidates = []
        if market == "score":
            team_score_probabilities = team_score_probabilities_by_official_option(score_matrix, quotes) if quotes else {}
            score_candidates = build_score_candidates(
                quotes=quotes,
                team_probabilities=team_score_probabilities,
                winner_probabilities=model_probabilities.get("winner", {}),
                handicap_probabilities=model_probabilities.get("handicap_winner", {}),
                total_goal_probabilities=model_probabilities.get("total_goals", {}),
                half_full_probabilities=model_probabilities.get("half_full", {}),
                official_weight=official_weight,
                team_weight=team_weight,
            )
        combined = combine_lines(market, official, team, official_weight, team_weight)
        advice_level, advice_label = advice_level_and_label(combined, missing, market == "score")
        summary = summary_for_market(market, official, team, combined, best_return, advice_label)
        decisions.append(
            MarketDecision(
                market=market,
                market_label=market_label(market),
                official_model=official,
                team_model=team,
                combined_model=combined,
                model_weights=ModelWeights(official=official_weight, team=team_weight),
                score_candidates=score_candidates,
                model_suggestions=[],
                market_favorite=None,
                best_return=None,
                missing_info=missing,
                advice_level=advice_level,
                advice_label=advice_label,
                summary=summary,
                reasons=[summary],
                warnings=missing,
            )
        )
    return decisions
```

- [ ] **Step 4: Wire `app/services.py` to combined advice**

Modify imports in `app/services.py`:

```python
from app.model.combined_advice import build_market_decisions
```

In `build_decision_comparisons`, replace the current loop body with a wrapper that delegates to the new builder:

```python
def build_decision_comparisons(
    match: MatchInput,
    markets: dict[str, list[MarketProbability]],
    scores: list[ScoreProbability],
    half_time: list[MarketProbability],
    odds: list[OddsQuote],
) -> list[MarketDecision]:
    model_probabilities = {
        "winner": {item.selection: item.probability for item in markets["winner"]},
        "handicap_winner": handicap_winner_probabilities(scores, handicap_line_from_match(match)),
        "score": score_probabilities(scores),
        "total_goals": total_goal_probabilities(scores),
        "half_full": half_full_probabilities(half_time, markets["winner"]),
    }
    return build_market_decisions(match, model_probabilities, scores)
```

- [ ] **Step 5: Run service integration tests and fix import/type mismatches**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest tests/test_services.py::test_analysis_returns_two_model_fields_and_score_candidates tests/test_services.py::test_different_score_odds_produce_different_official_score_recommendations -q
```

Expected: PASS.

- [ ] **Step 6: Run model unit tests**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest tests/test_official_odds_model.py tests/test_score_candidates.py tests/test_team_info.py tests/test_services.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add app/model/combined_advice.py app/services.py tests/test_services.py
git commit -m "feat: build combined five-market advice"
```

## Task 6: API Payload Coverage

**Files:**
- Modify: `tests/test_api.py`

- [ ] **Step 1: Add API regression test**

Append to `tests/test_api.py`:

```python
def test_match_analysis_endpoint_returns_two_model_advice_and_score_candidates():
    payload = get_json("/api/matches/m1/analysis")
    score = next(item for item in payload["decision_comparisons"] if item["market"] == "score")

    assert score["official_model"]
    assert score["team_model"]
    assert score["combined_model"]
    assert score["model_weights"]
    assert "official" in score["model_weights"]
    assert "team" in score["model_weights"]
    assert isinstance(score["score_candidates"], list)
    assert "summary" in score
```

- [ ] **Step 2: Run API test**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest tests/test_api.py::test_match_analysis_endpoint_returns_two_model_advice_and_score_candidates -q
```

Expected: PASS if service integration is complete. If fixture data lacks score candidates, add official score quotes with `home_other`, `draw_other`, and `away_other` to the API test fixture used by `get_json`.

- [ ] **Step 3: Run all API tests**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest tests/test_api.py -q
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add tests/test_api.py
git commit -m "test: cover two-model analysis API payload"
```

## Task 7: Frontend Plain Chinese Conclusion Table

**Files:**
- Modify: `app/static/app.js`
- Modify: `app/static/styles.css`
- Test: `tests/test_static_assets.py`

- [ ] **Step 1: Write failing static asset tests**

Append to `tests/test_static_assets.py`:

```python
def test_frontend_renders_two_model_plain_chinese_table():
    app_js = Path("app/static/app.js").read_text(encoding="utf-8")

    assert "赔率模型看好" in app_js
    assert "球队资料模型" in app_js
    assert "综合方案" in app_js
    assert "2元一注中出返还" in app_js
    assert "仅作娱乐参考" in app_js
    assert "score_candidates" in app_js


def test_frontend_rejects_technical_ev_copy_after_redesign():
    app_js = Path("app/static/app.js").read_text(encoding="utf-8")

    forbidden = ["EV", "期望值", "每100元", "模型比赔率", "赔率偏低", "理论盈亏"]
    for word in forbidden:
        assert word not in app_js
```

- [ ] **Step 2: Run static tests and verify failure**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest tests/test_static_assets.py::test_frontend_renders_two_model_plain_chinese_table tests/test_static_assets.py::test_frontend_rejects_technical_ev_copy_after_redesign -q
```

Expected: FAIL because `app.js` still uses old labels and parlay copy contains `理论盈亏`.

- [ ] **Step 3: Replace decision rendering in `app/static/app.js`**

Add helpers near `renderDecisionOption`:

```javascript
function modelLineText(line, fallback) {
  if (!line) return fallback;
  const label = line.selection_label || line.label || "暂无";
  const probability = line.probability == null ? "" : ` · 概率 ${pct(line.probability)}`;
  const odds = line.decimal_odds == null ? "" : ` · 赔率 ${Number(line.decimal_odds).toFixed(2)}`;
  const payout = line.payout_if_hit_2 == null ? "" : ` · 2元一注中出返还 ${Number(line.payout_if_hit_2).toFixed(2)}元`;
  const confidence = line.confidence_label ? ` · 置信度${line.confidence_label}` : "";
  return `${label}${probability}${odds}${payout}${confidence}`;
}

function renderScoreCandidates(candidates) {
  if (!candidates?.length) return "";
  const visible = candidates.slice(0, 5);
  const rows = visible
    .map(
      (candidate) => `
        <tr>
          <td><strong>${escapeHtml(candidate.label)}</strong>${candidate.model_scoreline ? `<small>模型比分 ${escapeHtml(candidate.model_scoreline)}</small>` : ""}</td>
          <td>${candidate.official_probability == null ? "缺失" : pct(candidate.official_probability)}</td>
          <td>${candidate.team_probability == null ? "缺失" : pct(candidate.team_probability)}</td>
          <td>${candidate.combined_probability == null ? "缺失" : pct(candidate.combined_probability)}</td>
          <td>${candidate.decimal_odds == null ? "缺失" : Number(candidate.decimal_odds).toFixed(2)}</td>
          <td>${candidate.payout_if_hit_2 == null ? "无法计算" : `${Number(candidate.payout_if_hit_2).toFixed(2)}元`}</td>
          <td>${escapeHtml(candidate.confidence_label || "低")}</td>
          <td>${escapeHtml(candidate.reason || "")}</td>
        </tr>
      `,
    )
    .join("");
  return `
    <details class="score-candidates">
      <summary>比分候选表</summary>
      <table>
        <thead>
          <tr>
            <th>比分</th>
            <th>赔率概率</th>
            <th>资料概率</th>
            <th>综合概率</th>
            <th>赔率</th>
            <th>2元返还</th>
            <th>置信度</th>
            <th>理由</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    </details>
  `;
}
```

Replace the `.decision-columns` block in `renderDecisionComparison` with:

```javascript
              <div class="decision-columns">
                <div>
                  <span>赔率模型看好</span>
                  <strong>${escapeHtml(modelLineText(decision.official_model, "官方赔率缺失"))}</strong>
                </div>
                <div>
                  <span>球队资料模型</span>
                  <strong>${escapeHtml(modelLineText(decision.team_model, "球队资料缺失"))}</strong>
                </div>
                <div>
                  <span>综合方案</span>
                  <strong>${escapeHtml(decision.advice_label || labelAdviceLevel(decision.advice_level))}</strong>
                  <small>${escapeHtml(decision.summary || "")}</small>
                </div>
              </div>
              ${decision.market === "score" ? renderScoreCandidates(decision.score_candidates || []) : ""}
```

Replace parlay label `2元一注理论盈亏` with `模型参考差值` or remove that stat. The preferred replacement is to remove that stat from the four-card layout and keep only:

```javascript
<div><span>2元一注中出返还</span><strong>${Number(parlay.payout_if_hit_2 || 0).toFixed(1)}元</strong></div>
```

- [ ] **Step 4: Add candidate table CSS**

Append to `app/static/styles.css`:

```css
.score-candidates {
  margin-top: 12px;
}

.score-candidates summary {
  cursor: pointer;
  font-weight: 700;
}

.score-candidates table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 10px;
  font-size: 13px;
}

.score-candidates th,
.score-candidates td {
  border-bottom: 1px solid rgba(15, 23, 42, 0.10);
  padding: 8px 6px;
  text-align: left;
  vertical-align: top;
}

.score-candidates small {
  display: block;
  color: var(--muted);
  margin-top: 2px;
}
```

- [ ] **Step 5: Run static tests and verify pass**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest tests/test_static_assets.py::test_frontend_renders_two_model_plain_chinese_table tests/test_static_assets.py::test_frontend_rejects_technical_ev_copy_after_redesign -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add app/static/app.js app/static/styles.css tests/test_static_assets.py
git commit -m "feat: render plain two-model advice table"
```

## Task 8: Full Verification And Local Smoke Test

**Files:**
- No file changes unless verification exposes a bug.

- [ ] **Step 1: Run full test suite**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q
```

Expected: all tests PASS.

- [ ] **Step 2: Restart local server**

Stop any old uvicorn session for this worktree. Then run:

```bash
env FOOTBALL_DATA_PROVIDER=sporttery SPORTTERY_REFRESH_SECONDS=30 .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Expected: server prints `Uvicorn running on http://127.0.0.1:8000`.

- [ ] **Step 3: Verify analysis payload from local service**

Run:

```bash
.venv/bin/python -c $'import json, urllib.request as u\nmatches=json.loads(u.urlopen("http://127.0.0.1:8000/api/matches?window=3d", timeout=20).read())\nprint("matches", len(matches))\nmid=matches[0]["match_id"]\ndata=json.loads(u.urlopen("http://127.0.0.1:8000/api/matches/"+mid+"/analysis", timeout=20).read())\nfor decision in data["decision_comparisons"]:\n    print(decision["market"], decision.get("official_model", {}).get("selection_label") if decision.get("official_model") else None, decision.get("team_model", {}).get("label") if decision.get("team_model") else None, decision.get("advice_label"), len(decision.get("score_candidates") or []))'
```

Expected: five markets print. Score market prints at least one score candidate when official score odds are available.

- [ ] **Step 4: Manual browser smoke test**

Open `http://127.0.0.1:8000` and press `Ctrl+F5`.

Expected:

- Five-market table appears.
- Score row can expand.
- Score candidates include probabilities, odds, and 2 yuan return.
- Missing team data is visible.
- Main copy uses plain Chinese.
- No main UI copy says `EV`, `期望值`, `每100元`, `模型比赔率`, `赔率偏低`, or `理论盈亏`.

- [ ] **Step 5: Commit any verification fixes**

If fixes were needed:

```bash
git add app tests
git commit -m "fix: polish probability model redesign"
```

If no fixes were needed, skip this commit.

## Task 9: Push And Deployment Check

**Files:**
- No file changes.

- [ ] **Step 1: Check final git status**

Run:

```bash
git status --short --branch
```

Expected: clean working tree on `football-probability-tool-implementation`.

- [ ] **Step 2: Push to GitHub main**

Run:

```bash
git push origin HEAD:main
```

Expected: push succeeds.

- [ ] **Step 3: Tell user how to verify**

Report:

- Local URL: `http://127.0.0.1:8000`
- Browser action: `Ctrl+F5`
- Render will redeploy from GitHub `main`.
- If Render cannot fetch Sporttery due to network/WAF, local mode remains the reliable way to use live official odds.

## Self-Review

Spec coverage:

- Five markets use official model, team model, and combined advice: Task 5, Task 7.
- Correct score includes concrete scores plus `胜其它/平其它/负其它`: Task 2, Task 3.
- Missing concrete model scorelines map to other options: Task 3.
- Team data is optional and missing data is visible: Task 4, Task 5.
- Dynamic official/team weights are exposed: Task 1, Task 4, Task 5, Task 7.
- Plain Chinese copy and rejected terms are tested: Task 7.
- Full verification and local smoke test are included: Task 8.

Placeholder scan:

- The plan contains no unfinished placeholder markers.
- Steps include explicit files, commands, expected results, and code snippets.

Type consistency:

- `ModelAdviceLine`, `ModelWeights`, `ScoreCandidate`, `TeamInfoFact`, and `TeamInfoSnapshot` are introduced in Task 1 before use.
- `score_candidates`, `official_model`, `team_model`, `combined_model`, and `model_weights` are consistently used in backend and frontend tasks.
