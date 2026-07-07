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
        picks.extend(analysis.recommendations)
    return picks


def build_parlay_recommendations(matches: list[MatchInput], strategy: StrategyName):
    return build_parlays(collect_best_picks(matches), strategy=strategy, max_legs=4)


def analysis_payload(match: MatchInput) -> dict:
    return analyze_match(match).model_dump()
