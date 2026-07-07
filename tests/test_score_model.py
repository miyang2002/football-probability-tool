import pytest

from app.model.score_model import (
    aggregate_score_matrix,
    estimate_expected_goals,
    half_time_probabilities,
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


def test_score_matrix_accepts_zero_expected_goals():
    matrix = poisson_score_matrix(0.0, 0.0, max_goals=3)

    assert len(matrix) == 16
    assert matrix[0].home_goals == 0
    assert matrix[0].away_goals == 0
    assert matrix[0].probability == 1.0


@pytest.mark.parametrize(
    ("home_xg", "away_xg", "max_goals"),
    [
        (-0.01, 1.0, 8),
        (1.0, -0.01, 8),
        (float("nan"), 1.0, 8),
        (1.0, float("inf"), 8),
        (1.0, 1.0, 0),
        (1.0, 1.0, -1),
    ],
)
def test_score_matrix_rejects_invalid_inputs(home_xg, away_xg, max_goals):
    with pytest.raises(ValueError):
        poisson_score_matrix(home_xg, away_xg, max_goals=max_goals)


def test_aggregates_include_winner_and_totals():
    matrix = poisson_score_matrix(1.45, 1.1, max_goals=8)
    markets = aggregate_score_matrix(matrix)

    winner = {(item.market, item.selection): item.probability for item in markets["winner"]}
    totals = {(item.market, item.selection): item.probability for item in markets["total_goals"]}

    assert round(sum(winner.values()), 6) == 1.0
    assert ("total_goals", "0") in totals
    assert ("over_under", "over_2.5") in {(item.market, item.selection) for item in markets["over_under"]}


def test_aggregates_keep_probability_partitions_in_bounds():
    matrix = poisson_score_matrix(0.01, 100.0, max_goals=20)
    markets = aggregate_score_matrix(matrix)

    for group in markets.values():
        for probability in group:
            assert 0.0 <= probability.probability <= 1.0

    assert round(sum(item.probability for item in markets["winner"]), 6) == 1.0
    assert round(sum(item.probability for item in markets["total_goals"]), 6) == 1.0


def test_half_time_probabilities_sum_to_one():
    half_time = half_time_probabilities(1.45, 1.1)

    assert round(sum(item.probability for item in half_time), 6) == 1.0


def test_top_scorelines_are_sorted():
    matrix = poisson_score_matrix(1.45, 1.1, max_goals=8)
    top = top_scorelines(matrix, limit=3)

    assert len(top) == 3
    assert top[0].probability >= top[1].probability >= top[2].probability
