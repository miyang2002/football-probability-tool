import re

from app.data.providers import build_match_official_diagnostic
from app.domain import (
    DecisionOption,
    MatchAnalysis,
    MatchInput,
    MarketDecision,
    MarketProbability,
    OddsQuote,
    OfficialOddsDiagnostics,
    PickRecommendation,
    ScoreProbability,
    SelectedParlayAnalysis,
    StrategyName,
)
from app.model.odds import expected_value, implied_probability
from app.model.combined_advice import build_market_decisions
from app.model.parlay import build_odds_parlays
from app.model.recommendations import build_recommendations, market_label, price_value_label, selection_label
from app.model.score_model import (
    aggregate_score_matrix,
    estimate_expected_goals,
    half_time_probabilities,
    poisson_score_matrix,
    top_scorelines,
)


OUTCOME_LABELS = {"home": "主胜", "draw": "平局", "away": "客胜"}
DECISION_MARKETS = ("winner", "handicap_winner", "score", "total_goals", "half_full")
DECISION_ADVICE_LABELS = {"stable": "建议", "small": "小额参考", "balanced": "谨慎", "avoid": "放弃"}
MARKET_SELECTION_LABELS = {
    "winner": {"home": "主胜", "draw": "平局", "away": "客胜"},
    "handicap_winner": {"home": "让球主胜", "draw": "让球平", "away": "让球客胜"},
    "half_full": {
        "home_home": "胜胜",
        "home_draw": "胜平",
        "home_away": "胜负",
        "draw_home": "平胜",
        "draw_draw": "平平",
        "draw_away": "平负",
        "away_home": "负胜",
        "away_draw": "负平",
        "away_away": "负负",
    },
}


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
                f"旧概率字段给到 {outcome_probability:.1%}，判断为：{value_label}。"
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
                    f"页面推荐不使用这个比分概率，只看体彩比分赔率；{odds_text}"
                ),
            )
        )

    return enriched


def score_method_summary(home_xg: float, away_xg: float) -> str:
    del home_xg, away_xg
    return (
        "比分、总进球和半全场建议只看体彩赔率；赔率越低，代表体彩这一组数字里市场越偏向该选项。"
    )


def odds_basis_summary(odds: list[OddsQuote]) -> str:
    if any(quote.market == "winner" and quote.source == "sporttery" for quote in odds):
        return "当前接入体彩官方赔率；页面推荐只根据体彩赔率和赔率变化生成。"
    return "当前没有体彩官方赔率；不会用示例赔率或旧概率字段冒充真实推荐。"


def official_market_quotes(odds: list[OddsQuote], market: str) -> list[OddsQuote]:
    return [quote for quote in odds if quote.market == market and quote.source == "sporttery"]


def normalized_market_probabilities(quotes: list[OddsQuote]) -> dict[str, float]:
    inverse = {quote.selection: implied_probability(quote.decimal_odds) for quote in quotes}
    total = sum(inverse.values())
    if total <= 0:
        return {}
    return {selection: probability / total for selection, probability in inverse.items()}


def quote_display_label(quote: OddsQuote) -> str:
    return quote.selection_label or selection_label(quote.selection)


def market_selection_label(market: str, selection: str) -> str:
    if market in MARKET_SELECTION_LABELS and selection in MARKET_SELECTION_LABELS[market]:
        return MARKET_SELECTION_LABELS[market][selection]
    if market == "score":
        return selection
    if market == "total_goals":
        return f"{selection}球" if selection != "7+" else "7+球"
    return selection_label(selection)


def payout_if_hit_2(decimal_odds: float | None) -> float | None:
    if decimal_odds is None:
        return None
    return round(decimal_odds * 2, 2)


def option_from_selection(
    market: str,
    selection: str,
    probability: float | None,
    quote: OddsQuote | None = None,
) -> DecisionOption:
    decimal_odds = quote.decimal_odds if quote else None
    return DecisionOption(
        selection=selection,
        label=quote_display_label(quote) if quote else market_selection_label(market, selection),
        probability=probability,
        decimal_odds=decimal_odds,
        payout_if_hit_2=payout_if_hit_2(decimal_odds),
        source=quote.source if quote else None,
    )


def sorted_model_options(
    market: str,
    probabilities: dict[str, float],
    quotes: list[OddsQuote],
    limit: int = 1,
) -> list[DecisionOption]:
    quote_by_selection = {quote.selection: quote for quote in quotes}
    candidate_selections = set(quote_by_selection) if quotes else set(probabilities)
    candidates = [
        (selection, probabilities[selection])
        for selection in candidate_selections
        if selection in probabilities
    ]
    ordered = sorted(candidates, key=lambda item: item[1], reverse=True)[:limit]
    return [
        option_from_selection(market, selection, probability, quote_by_selection.get(selection))
        for selection, probability in ordered
    ]


def odds_decision(quotes: list[OddsQuote]) -> tuple[OddsQuote, float] | None:
    normalized = normalized_market_probabilities(quotes)
    if not normalized:
        return None
    best = max(quotes, key=lambda quote: normalized.get(quote.selection, 0.0))
    return best, normalized[best.selection]


def market_favorite_option(market: str, quotes: list[OddsQuote]) -> DecisionOption | None:
    favorite = odds_decision(quotes)
    if favorite is None:
        return None
    quote, probability = favorite
    return option_from_selection(market, quote.selection, probability, quote)


def best_return_option(
    market: str,
    probabilities: dict[str, float],
    quotes: list[OddsQuote],
) -> DecisionOption | None:
    if not quotes or not probabilities:
        return None
    candidates = [
        (quote, probabilities[quote.selection] * quote.decimal_odds)
        for quote in quotes
        if quote.selection in probabilities
    ]
    if not candidates:
        return None
    quote, _ = max(candidates, key=lambda item: item[1])
    return option_from_selection(market, quote.selection, probabilities.get(quote.selection), quote)


def total_goal_probabilities(scores: list[ScoreProbability]) -> dict[str, float]:
    probabilities = {str(total): 0.0 for total in range(7)}
    probabilities["7+"] = 0.0
    for score in scores:
        total = score.home_goals + score.away_goals
        key = str(total) if total <= 6 else "7+"
        probabilities[key] += score.probability
    return probabilities


def score_probabilities(scores: list[ScoreProbability]) -> dict[str, float]:
    return {f"{score.home_goals}-{score.away_goals}": score.probability for score in scores}


def handicap_line_from_match(match: MatchInput) -> float | None:
    for note in match.context.notes:
        match_result = re.search(r"让球\s*([+-]?\d+(?:\.\d+)?)", note)
        if match_result:
            return float(match_result.group(1))
    return None


def handicap_winner_probabilities(scores: list[ScoreProbability], line: float | None) -> dict[str, float]:
    if line is None:
        return {}
    probabilities = {"home": 0.0, "draw": 0.0, "away": 0.0}
    for score in scores:
        adjusted_home = score.home_goals + line
        if adjusted_home > score.away_goals:
            probabilities["home"] += score.probability
        elif adjusted_home == score.away_goals:
            probabilities["draw"] += score.probability
        else:
            probabilities["away"] += score.probability
    return probabilities


def half_full_probabilities(
    half_time: list[MarketProbability],
    full_time: list[MarketProbability],
) -> dict[str, float]:
    half = {item.selection: item.probability for item in half_time}
    full = {item.selection: item.probability for item in full_time}
    probabilities: dict[str, float] = {}
    for half_selection in ("home", "draw", "away"):
        for full_selection in ("home", "draw", "away"):
            key = f"{half_selection}_{full_selection}"
            probabilities[key] = half.get(half_selection, 0.0) * full.get(full_selection, 0.0)
    total = sum(probabilities.values())
    if total <= 0:
        return probabilities
    return {selection: probability / total for selection, probability in probabilities.items()}


def advice_for_decision(
    model_suggestions: list[DecisionOption],
    market_favorite: DecisionOption | None,
    best_return: DecisionOption | None,
    missing_info: list[str],
) -> tuple[str, str]:
    if missing_info:
        return "avoid", "放弃"
    if not model_suggestions:
        return "balanced", "谨慎"
    top_model = model_suggestions[0]
    favorite_matches = market_favorite is not None and top_model.selection == market_favorite.selection
    return_matches = best_return is not None and top_model.selection == best_return.selection
    if favorite_matches and return_matches:
        return "stable", "建议"
    if favorite_matches or return_matches:
        return "small", "小额参考"
    return "balanced", "谨慎"


def decision_summary(
    market_label_text: str,
    model_suggestions: list[DecisionOption],
    market_favorite: DecisionOption | None,
    best_return: DecisionOption | None,
    advice_label: str,
    missing_info: list[str],
) -> str:
    if missing_info:
        return f"{market_label_text}缺少官方赔率，市场建议和2元返还无法准确计算。"
    if not model_suggestions:
        return f"{market_label_text}旧概率字段不足，只能看市场赔率，建议谨慎。"
    top_model = model_suggestions[0]
    if market_favorite and best_return and top_model.selection == market_favorite.selection == best_return.selection:
        return f"旧概率字段、市场热度和赔率回报都指向{top_model.label}，综合建议：{advice_label}。"
    if market_favorite and top_model.selection != market_favorite.selection:
        return f"旧概率字段看好{top_model.label}，市场更支持{market_favorite.label}，两边存在分歧，综合建议：{advice_label}。"
    return f"旧概率字段和赔率参考部分一致，综合建议：{advice_label}。"


def build_decision_summary(
    market: str,
    model_suggestions: list[DecisionOption],
    probabilities: dict[str, float],
    quotes: list[OddsQuote],
    missing_info: list[str] | None = None,
) -> MarketDecision:
    current_market_label = market_label(market)
    missing = list(missing_info or [])
    if not quotes:
        missing.append(f"官方{current_market_label}赔率缺失，会影响市场建议准确性")
    favorite = market_favorite_option(market, quotes)
    best_return = best_return_option(market, probabilities, quotes)
    advice_level, advice_label = advice_for_decision(model_suggestions, favorite, best_return, missing)
    summary = decision_summary(current_market_label, model_suggestions, favorite, best_return, advice_label, missing)
    reasons = []
    if model_suggestions:
        reasons.append("旧概率字段建议：" + " / ".join(option.label for option in model_suggestions))
    if favorite:
        reasons.append(f"市场最看好：{favorite.label}，2元一注返还 {favorite.payout_if_hit_2:.2f} 元。")
    if best_return:
        reasons.append(f"赔率回报最好：{best_return.label}，2元一注返还 {best_return.payout_if_hit_2:.2f} 元。")

    return MarketDecision(
        market=market,
        market_label=current_market_label,
        model_suggestions=model_suggestions,
        market_favorite=favorite,
        best_return=best_return,
        missing_info=missing,
        model_selection=model_suggestions[0].selection if model_suggestions else None,
        model_selection_label=model_suggestions[0].label if model_suggestions else None,
        model_probability=model_suggestions[0].probability if model_suggestions else None,
        odds_selection=favorite.selection if favorite else None,
        odds_selection_label=favorite.label if favorite else None,
        odds_decimal=favorite.decimal_odds if favorite else None,
        odds_probability=favorite.probability if favorite else None,
        edge=None,
        expected_value=None,
        advice_level=advice_level,
        advice_label=advice_label,
        summary=summary,
        reasons=reasons,
        warnings=missing,
    )


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


def analyze_match(match: MatchInput) -> MatchAnalysis:
    home_xg, away_xg = estimate_expected_goals(match)
    matrix = poisson_score_matrix(home_xg, away_xg, max_goals=8)
    markets = aggregate_score_matrix(matrix)
    enriched_matrix = enrich_score_probabilities(matrix, markets["winner"], match.odds)
    half_time = half_time_probabilities(home_xg, away_xg)
    match_label = f"{match.home.name} vs {match.away.name}"
    del match_label
    recommendations: list[PickRecommendation] = []
    decision_comparisons = build_decision_comparisons(match, markets, enriched_matrix, half_time, match.odds)

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
        decision_comparisons=decision_comparisons,
        data_quality=match.context.data_quality,
    )


def collect_best_picks(matches: list[MatchInput]) -> list[PickRecommendation]:
    picks: list[PickRecommendation] = []
    for match in matches:
        analysis = analyze_match(match)
        picks.extend(analysis.recommendations)
    return picks


def build_parlay_recommendations(matches: list[MatchInput], strategy: StrategyName):
    return build_odds_parlays(matches, strategy=strategy, max_legs=4)


def build_selected_parlay_analysis(
    matches: list[MatchInput],
    selected_match_ids: list[str],
    strategy: StrategyName,
    stake: float = 2.0,
) -> SelectedParlayAnalysis:
    selected_set = set(selected_match_ids)
    selected_matches = [match for match in matches if match.match_id in selected_set]
    ordered_matches = sorted(selected_matches, key=lambda match: selected_match_ids.index(match.match_id))
    return SelectedParlayAnalysis(
        selected_match_ids=[match.match_id for match in ordered_matches],
        stake=stake,
        winner_parlays=build_odds_parlays(ordered_matches, strategy=strategy, max_legs=4, stake=stake),
        score_parlays=[],
    )


def analysis_payload(match: MatchInput) -> dict:
    return analyze_match(match).model_dump()


def build_official_odds_diagnostics(provider, window: str = "next") -> OfficialOddsDiagnostics:
    if hasattr(provider, "official_odds_diagnostics"):
        return provider.official_odds_diagnostics(window=window)

    matches = provider.list_matches(window=window)
    diagnostics = [build_match_official_diagnostic(match) for match in matches]
    return OfficialOddsDiagnostics(status=provider.status(), match_count=len(diagnostics), matches=diagnostics)
