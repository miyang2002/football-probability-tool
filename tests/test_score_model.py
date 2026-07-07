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
