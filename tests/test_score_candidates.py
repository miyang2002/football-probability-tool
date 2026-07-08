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
    quotes = [
        q("1-0", 6.5),
        q("home_other", 35, "胜其它"),
        q("draw_other", 120, "平其它"),
        q("away_other", 80, "负其它"),
    ]
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
