from app.data.team_info import MissingTeamInfoProvider, TeamInfoProvider, team_model_weight
from app.domain import (
    DecisionOption,
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


def official_quotes(odds: list[OddsQuote], market: str) -> list[OddsQuote]:
    return [quote for quote in odds if quote.market == market and quote.source == "sporttery"]


def quote_label(quote: OddsQuote) -> str:
    return quote.selection_label or quote.selection


def selection_label(market: str, selection: str) -> str:
    if market in MARKET_SELECTION_LABELS and selection in MARKET_SELECTION_LABELS[market]:
        return MARKET_SELECTION_LABELS[market][selection]
    if market == "total_goals":
        return f"{selection}球" if selection != "7" else "7+球"
    return selection


def decision_option_from_line(line: ModelAdviceLine | None) -> DecisionOption | None:
    if line is None or line.selection is None:
        return None
    return DecisionOption(
        selection=line.selection,
        label=line.selection_label or line.label,
        probability=line.probability,
        decimal_odds=line.decimal_odds,
        payout_if_hit_2=line.payout_if_hit_2,
        source=line.source,
    )


def sorted_model_options(
    market: str,
    probabilities: dict[str, float],
    quotes: list[OddsQuote],
    limit: int,
) -> list[DecisionOption]:
    quote_by_selection = {quote.selection: quote for quote in quotes}
    candidate_selections = set(quote_by_selection) if quotes else set(probabilities)
    candidates = [
        (selection, probabilities[selection])
        for selection in candidate_selections
        if selection in probabilities
    ]
    ordered = sorted(candidates, key=lambda item: item[1], reverse=True)[:limit]
    options = []
    for selection, probability in ordered:
        quote = quote_by_selection.get(selection)
        decimal_odds = quote.decimal_odds if quote else None
        options.append(
            DecisionOption(
                selection=selection,
                label=quote_label(quote) if quote else selection_label(market, selection),
                probability=probability,
                decimal_odds=decimal_odds,
                payout_if_hit_2=payout_if_hit_2(decimal_odds),
                source=quote.source if quote else None,
            )
        )
    return options


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
    if missing_info or not probabilities:
        return plain_missing_team_line(market, missing_info)
    selection, probability = max(probabilities.items(), key=lambda item: item[1])
    label = selection_label(market, selection)
    return ModelAdviceLine(
        source="team_info",
        label=f"球队资料模型看好{label}",
        selection=selection,
        selection_label=label,
        probability=probability,
        confidence_label="中",
        rank=1,
        reasons=["根据当前球队资料模型得到的参考方向。"],
    )


def combine_lines(
    official: ModelAdviceLine | None,
    team: ModelAdviceLine | None,
    official_weight: float,
    team_weight: float,
) -> ModelAdviceLine:
    chosen = official or (team if team and team.selection else None)
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
    official: ModelAdviceLine | None,
    team: ModelAdviceLine | None,
    combined: ModelAdviceLine,
    best_return: ModelAdviceLine | None,
    advice_label: str,
) -> str:
    if official and official.decimal_odds and official.payout_if_hit_2 is not None:
        official_text = (
            f"体彩更看好{official.selection_label}，赔率{official.decimal_odds:.2f}，"
            f"2元一注中出返还{official.payout_if_hit_2:.2f}元。"
        )
    else:
        official_text = "体彩赔率参考不足。"
    if team and team.selection:
        team_text = f"球队资料模型看好{team.selection_label or team.label}。"
    else:
        team_text = "球队资料缺失。"
    if best_return and best_return.payout_if_hit_2 is not None:
        return_text = f"回报参考{best_return.selection_label}，2元一注中出返还{best_return.payout_if_hit_2:.2f}元。"
    else:
        return_text = "回报参考不足。"
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
        probabilities = model_probabilities.get(market, {})
        official = market_favorite(market, quotes)
        team = top_team_line(market, probabilities, snapshot.missing_info)
        best_return = best_return_reference(market, quotes, probabilities)
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
        combined = combine_lines(official, team, official_weight, team_weight)
        advice_level, advice_label = advice_level_and_label(combined, missing, market == "score")
        summary = summary_for_market(official, team, combined, best_return, advice_label)
        model_suggestions = sorted_model_options(market, probabilities, quotes, limit=3 if market == "score" else 1)
        market_favorite_option = decision_option_from_line(official)
        best_return_option = decision_option_from_line(best_return)
        decisions.append(
            MarketDecision(
                market=market,
                market_label=market_label(market),
                official_model=official,
                team_model=team,
                combined_model=combined,
                model_weights=ModelWeights(official=official_weight, team=team_weight),
                score_candidates=score_candidates,
                model_suggestions=model_suggestions,
                market_favorite=market_favorite_option,
                best_return=best_return_option,
                missing_info=missing,
                model_selection=model_suggestions[0].selection if model_suggestions else None,
                model_selection_label=model_suggestions[0].label if model_suggestions else None,
                model_probability=model_suggestions[0].probability if model_suggestions else None,
                odds_selection=official.selection if official else None,
                odds_selection_label=official.selection_label if official else None,
                odds_decimal=official.decimal_odds if official else None,
                odds_probability=official.probability if official else None,
                edge=None,
                expected_value=None,
                advice_level=advice_level,
                advice_label=advice_label,
                summary=summary,
                reasons=[summary],
                warnings=missing,
            )
        )
    return decisions
