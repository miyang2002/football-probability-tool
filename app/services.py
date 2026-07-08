from app.data.providers import build_match_official_diagnostic
from app.domain import (
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
from app.model.parlay import build_parlays, build_score_parlays, build_selected_winner_parlays
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
                    f"比分概率来自预期进球模型参考；{odds_text}"
                ),
            )
        )

    return enriched


def score_method_summary(home_xg: float, away_xg: float) -> str:
    return (
        f"模型参考：先估算两队预期进球为 {home_xg:.2f} - {away_xg:.2f}，"
        "再生成比分和进球数排序；这些结果只作参考，需要结合官方赔率判断。"
    )


def odds_basis_summary(odds: list[OddsQuote]) -> str:
    if any(quote.market == "winner" and quote.source == "sporttery" for quote in odds):
        return "当前接入体彩官方胜平负赔率；综合建议会分开展示模型推荐和赔率推荐。"
    return "当前没有体彩官方胜平负赔率；模型结果只作参考，不能判断官方赔率是否划算。"


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


def model_probability_decision(market: str, probabilities: list[MarketProbability]) -> tuple[str, str, float] | None:
    if not probabilities:
        return None
    best = max(probabilities, key=lambda item: item.probability)
    return best.selection, selection_label(best.selection), best.probability


def score_probability_decision(scores: list[ScoreProbability]) -> tuple[str, str, float] | None:
    if not scores:
        return None
    best = max(scores, key=lambda item: item.probability)
    selection = f"{best.home_goals}-{best.away_goals}"
    return selection, selection, best.probability


def odds_decision(quotes: list[OddsQuote]) -> tuple[OddsQuote, float] | None:
    normalized = normalized_market_probabilities(quotes)
    if not normalized:
        return None
    best = max(quotes, key=lambda quote: normalized.get(quote.selection, 0.0))
    return best, normalized[best.selection]


def build_decision_summary(
    market: str,
    model: tuple[str, str, float] | None,
    odds: tuple[OddsQuote, float] | None,
    quotes: list[OddsQuote],
) -> MarketDecision:
    current_market_label = market_label(market)
    model_selection = model[0] if model else None
    model_label = model[1] if model else None
    model_probability = model[2] if model else None
    odds_quote = odds[0] if odds else None
    odds_probability = odds[1] if odds else None
    quote_by_selection = {quote.selection: quote for quote in quotes}
    probability_by_selection = normalized_market_probabilities(quotes)
    compared_quote = quote_by_selection.get(model_selection or "")
    compared_odds_probability = probability_by_selection.get(model_selection or "")

    edge = None
    ev = None
    if model_probability is not None and compared_quote is not None and compared_odds_probability is not None:
        edge = model_probability - compared_odds_probability
        ev = expected_value(model_probability, compared_quote.decimal_odds)

    reasons: list[str] = []
    warnings: list[str] = []
    if model:
        reasons.append(f"模型推荐：{model_label}，概率 {model_probability:.1%}。")
    else:
        warnings.append(f"当前模型暂不支持{current_market_label}独立判断。")
    if odds_quote:
        reasons.append(
            f"赔率推荐：{quote_display_label(odds_quote)}，官方赔率 {odds_quote.decimal_odds:.2f}，"
            f"赔率反推约 {odds_probability:.1%}。"
        )
    else:
        warnings.append(f"缺少体彩官方{current_market_label}赔率。")
    if model and odds_quote and model_selection != odds_quote.selection:
        warnings.append("模型推荐和赔率推荐不一致，需要谨慎。")
    if compared_quote and compared_quote is not odds_quote:
        reasons.append(f"模型推荐项对应官方赔率 {compared_quote.decimal_odds:.2f}。")
    if edge is not None:
        reasons.append(f"模型比赔率反推高 {edge:.1%}。")
    if ev is not None:
        reasons.append(f"按2元一注长期理论盈亏约 {ev * 2:+.2f} 元。")

    if not odds_quote:
        advice_level = "missing"
        advice_label = "缺官方赔率"
        summary = f"{current_market_label}缺少体彩官方赔率，只能看模型参考，不给投注建议。"
    elif not model:
        advice_level = "missing"
        advice_label = "只看赔率不推荐"
        summary = f"{current_market_label}目前只有赔率方向，没有模型校验，不建议单独采用。"
    elif ev is not None and edge is not None and ev >= 0.05 and edge >= 0.03:
        advice_level = "small"
        advice_label = "小额尝试"
        summary = f"{current_market_label}模型和赔率存在正向差异，可小额观察。"
    elif model_selection == odds_quote.selection and ev is not None and ev >= -0.03:
        advice_level = "stable"
        advice_label = "稳健参考"
        summary = f"{current_market_label}模型和赔率方向一致，可作为重点参考。"
    elif ev is not None and ev >= 0:
        advice_level = "balanced"
        advice_label = "均衡参考"
        summary = f"{current_market_label}模型认为回报基本合理，但需结合临场信息。"
    else:
        advice_level = "avoid"
        advice_label = "放弃"
        summary = f"{current_market_label}赔率回报不支持模型方向，不建议强行选择。"

    return MarketDecision(
        market=market,
        market_label=current_market_label,
        model_selection=model_selection,
        model_selection_label=model_label,
        model_probability=model_probability,
        odds_selection=odds_quote.selection if odds_quote else None,
        odds_selection_label=quote_display_label(odds_quote) if odds_quote else None,
        odds_decimal=odds_quote.decimal_odds if odds_quote else None,
        odds_probability=odds_probability,
        edge=edge,
        expected_value=ev,
        advice_level=advice_level,
        advice_label=advice_label,
        summary=summary,
        reasons=reasons,
        warnings=warnings,
    )


def build_decision_comparisons(
    markets: dict[str, list[MarketProbability]],
    scores: list[ScoreProbability],
    odds: list[OddsQuote],
) -> list[MarketDecision]:
    model_by_market = {
        "winner": model_probability_decision("winner", markets["winner"]),
        "score": score_probability_decision(scores),
        "total_goals": model_probability_decision("total_goals", markets["total_goals"]),
        "handicap_winner": None,
        "half_full": None,
    }
    decisions: list[MarketDecision] = []
    for market in DECISION_MARKETS:
        quotes = official_market_quotes(odds, market)
        decisions.append(build_decision_summary(market, model_by_market[market], odds_decision(quotes), quotes))
    return decisions


def analyze_match(match: MatchInput) -> MatchAnalysis:
    home_xg, away_xg = estimate_expected_goals(match)
    matrix = poisson_score_matrix(home_xg, away_xg, max_goals=8)
    markets = aggregate_score_matrix(matrix)
    enriched_matrix = enrich_score_probabilities(matrix, markets["winner"], match.odds)
    half_time = half_time_probabilities(home_xg, away_xg)
    recommendation_markets = markets["winner"] + markets["over_under"]
    match_label = f"{match.home.name} vs {match.away.name}"
    recommendations = build_recommendations(match.match_id, recommendation_markets, match.odds, match.context, match_label)
    decision_comparisons = build_decision_comparisons(markets, enriched_matrix, match.odds)

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


def build_official_odds_diagnostics(provider, window: str = "next") -> OfficialOddsDiagnostics:
    if hasattr(provider, "official_odds_diagnostics"):
        return provider.official_odds_diagnostics(window=window)

    matches = provider.list_matches(window=window)
    diagnostics = [build_match_official_diagnostic(match) for match in matches]
    return OfficialOddsDiagnostics(status=provider.status(), match_count=len(diagnostics), matches=diagnostics)
