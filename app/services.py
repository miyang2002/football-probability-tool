from app.domain import MatchAnalysis, MatchInput, OddsQuote, PickRecommendation, ScoreProbability, SelectedParlayAnalysis, StrategyName
from app.model.odds import expected_value, implied_probability
from app.model.parlay import build_parlays, build_score_parlays, build_selected_winner_parlays
from app.model.recommendations import build_recommendations, price_value_label
from app.model.score_model import (
    aggregate_score_matrix,
    estimate_expected_goals,
    half_time_probabilities,
    poisson_score_matrix,
    top_scorelines,
)


OUTCOME_LABELS = {"home": "主胜", "draw": "平局", "away": "客胜"}


def score_outcome(score: ScoreProbability) -> str:
    if score.home_goals > score.away_goals:
        return "home"
    if score.home_goals < score.away_goals:
        return "away"
    return "draw"


def enrich_score_probabilities(
    scores: list[ScoreProbability],
    winner_probabilities: list,
    odds: list[OddsQuote],
) -> list[ScoreProbability]:
    winner_probability_by_outcome = {item.selection: item.probability for item in winner_probabilities}
    odds_by_outcome = {quote.selection: quote.decimal_odds for quote in odds if quote.market == "winner"}
    enriched: list[ScoreProbability] = []

    for score in scores:
        outcome = score_outcome(score)
        outcome_label = OUTCOME_LABELS[outcome]
        outcome_probability = winner_probability_by_outcome.get(outcome)
        decimal_odds = odds_by_outcome.get(outcome)
        value_label = "没有赔率，无法判断"
        odds_text = "目前没有对应胜平负赔率，不能判断赔率是否支持这个比分方向。"
        if decimal_odds is not None and outcome_probability is not None:
            implied = implied_probability(decimal_odds)
            edge = outcome_probability - implied
            ev = expected_value(outcome_probability, decimal_odds)
            value_label = price_value_label(ev, edge)
            odds_text = (
                f"{outcome_label}赔率 {decimal_odds:.2f}，赔率反推概率约 {implied:.1%}，"
                f"模型给到 {outcome_probability:.1%}，判断为：{value_label}。"
            )

        enriched.append(
            ScoreProbability(
                home_goals=score.home_goals,
                away_goals=score.away_goals,
                probability=score.probability,
                outcome=outcome,
                outcome_label=outcome_label,
                related_odds=decimal_odds,
                odds_value_label=value_label,
                explanation=(
                    f"{score.home_goals}-{score.away_goals} 属于{outcome_label}方向。"
                    f"比分概率来自预期进球的泊松分布模型；{odds_text}"
                ),
            )
        )

    return enriched


def score_method_summary(home_xg: float, away_xg: float) -> str:
    return (
        f"先估算两队预期进球为 {home_xg:.2f} - {away_xg:.2f}，"
        "再用泊松分布计算每一种比分出现的概率。"
    )


def odds_basis_summary(odds: list[OddsQuote]) -> str:
    if any(quote.market == "winner" for quote in odds):
        return "当前接入胜平负赔率；比分本身由数学模型计算，赔率用于判断主胜、平局、客胜方向是否划算。"
    return "当前没有可用胜平负赔率；比分只反映数学模型结果，暂时不能做赔率划算度判断。"


def analyze_match(match: MatchInput) -> MatchAnalysis:
    home_xg, away_xg = estimate_expected_goals(match)
    matrix = poisson_score_matrix(home_xg, away_xg, max_goals=8)
    markets = aggregate_score_matrix(matrix)
    enriched_matrix = enrich_score_probabilities(matrix, markets["winner"], match.odds)
    half_time = half_time_probabilities(home_xg, away_xg)
    recommendation_markets = markets["winner"] + markets["over_under"]
    match_label = f"{match.home.name} vs {match.away.name}"
    recommendations = build_recommendations(match.match_id, recommendation_markets, match.odds, match.context, match_label)

    return MatchAnalysis(
        match=match,
        expected_home_goals=home_xg,
        expected_away_goals=away_xg,
        score_method_summary=score_method_summary(home_xg, away_xg),
        odds_basis_summary=odds_basis_summary(match.odds),
        winner_probabilities=markets["winner"],
        half_time_probabilities=half_time,
        total_goal_probabilities=markets["total_goals"],
        over_under_probabilities=markets["over_under"],
        score_probabilities=enriched_matrix,
        top_scores=top_scorelines(enriched_matrix),
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


def build_selected_parlay_analysis(
    matches: list[MatchInput],
    selected_match_ids: list[str],
    strategy: StrategyName,
    stake: float = 2.0,
) -> SelectedParlayAnalysis:
    selected_set = set(selected_match_ids)
    selected_matches = [match for match in matches if match.match_id in selected_set]
    ordered_matches = sorted(selected_matches, key=lambda match: selected_match_ids.index(match.match_id))
    analyses = [analyze_match(match) for match in ordered_matches]
    winner_picks = [
        pick
        for analysis in analyses
        for pick in analysis.recommendations
        if pick.market == "winner"
    ]

    return SelectedParlayAnalysis(
        selected_match_ids=[match.match_id for match in ordered_matches],
        stake=stake,
        winner_parlays=build_selected_winner_parlays(winner_picks, strategy=strategy, max_legs=4, stake=stake),
        score_parlays=build_score_parlays(analyses, strategy=strategy, max_legs=4, stake=stake),
    )


def analysis_payload(match: MatchInput) -> dict:
    return analyze_match(match).model_dump()
