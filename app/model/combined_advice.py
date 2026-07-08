from app.domain import (
    DecisionOption,
    MarketDecision,
    MatchInput,
    ModelAdviceLine,
    OddsQuote,
    ScoreCandidate,
    ScoreProbability,
)
from app.model.official_odds_model import normalized_official_probabilities, payout_if_hit_2
from app.model.recommendations import market_label


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
    return quote.selection_label or selection_label(quote.market, quote.selection)


def selection_label(market: str, selection: str) -> str:
    if market in MARKET_SELECTION_LABELS and selection in MARKET_SELECTION_LABELS[market]:
        return MARKET_SELECTION_LABELS[market][selection]
    if market == "total_goals":
        return f"{selection}球" if selection != "7" else "7+球"
    return selection


def probability_text(probability: float | None) -> str:
    if probability is None:
        return "无法折算"
    return f"{probability:.1%}"


def movement_text(quote: OddsQuote) -> str:
    direction = {
        "down": "赔率下降，说明这个方向的回报变低，市场更偏向它",
        "up": "赔率上升，说明这个方向的回报变高，市场支持变弱",
        "flat": "赔率暂时没有明显变化",
        None: "暂时没有赔率变化记录",
    }.get(quote.movement, "暂时没有赔率变化记录")
    if quote.previous_decimal_odds is not None:
        return f"{direction}，从 {quote.previous_decimal_odds:.2f} 到 {quote.decimal_odds:.2f}"
    return direction


def decision_option_from_quote(quote: OddsQuote, probability: float | None = None) -> DecisionOption:
    return DecisionOption(
        selection=quote.selection,
        label=quote_label(quote),
        probability=probability,
        decimal_odds=quote.decimal_odds,
        payout_if_hit_2=payout_if_hit_2(quote.decimal_odds),
        source=quote.source,
    )


def favorite_quote(quotes: list[OddsQuote]) -> tuple[OddsQuote, float] | None:
    probabilities = normalized_official_probabilities(quotes)
    if not probabilities:
        return None
    quote_by_selection = {quote.selection: quote for quote in quotes}
    selection = max(probabilities, key=probabilities.get)
    quote = quote_by_selection[selection]
    return quote, probabilities[selection]


def highest_return_quote(quotes: list[OddsQuote]) -> tuple[OddsQuote, float | None] | None:
    if not quotes:
        return None
    probabilities = normalized_official_probabilities(quotes)
    quote = max(quotes, key=lambda item: item.decimal_odds)
    return quote, probabilities.get(quote.selection)


def confidence_label(market: str, quote: OddsQuote, probability: float) -> str:
    if market == "score":
        return "娱乐"
    if quote.decimal_odds <= 1.45 or probability >= 0.62:
        return "较稳"
    if quote.decimal_odds <= 2.25 or probability >= 0.42:
        return "中等"
    return "偏谨慎"


def advice_level_and_label(market: str, quote: OddsQuote, probability: float) -> tuple[str, str]:
    if market == "score":
        return "small", "娱乐参考"
    if market == "half_full":
        return "balanced", "谨慎参考"
    if quote.decimal_odds <= 1.45 or probability >= 0.62:
        return "stable", "可作串关胆"
    if quote.decimal_odds <= 2.25 or probability >= 0.42:
        return "small", "可以参考"
    return "balanced", "谨慎参考"


def official_line(market: str, quote: OddsQuote, probability: float) -> ModelAdviceLine:
    label = quote_label(quote)
    return ModelAdviceLine(
        source="official_odds",
        label=f"体彩最看好{label}",
        selection=quote.selection,
        selection_label=label,
        probability=probability,
        decimal_odds=quote.decimal_odds,
        payout_if_hit_2=payout_if_hit_2(quote.decimal_odds),
        confidence_label=confidence_label(market, quote, probability),
        rank=1,
        reasons=[
            f"体彩{market_label(market)}最低赔率是{label} {quote.decimal_odds:.2f}。",
            f"按这一组赔率折算，占比约{probability_text(probability)}。",
            movement_text(quote),
        ],
    )


def score_candidates_from_quotes(quotes: list[OddsQuote], limit: int = 5) -> list[ScoreCandidate]:
    probabilities = normalized_official_probabilities(quotes)
    quote_rows = sorted(
        [(quote, probabilities.get(quote.selection, 0.0)) for quote in quotes],
        key=lambda item: item[1],
        reverse=True,
    )[:limit]
    candidates: list[ScoreCandidate] = []
    for rank, (quote, probability) in enumerate(quote_rows, start=1):
        label = quote_label(quote)
        payout = payout_if_hit_2(quote.decimal_odds)
        candidates.append(
            ScoreCandidate(
                selection=quote.selection,
                label=label,
                official_option_label=label,
                official_probability=probability,
                decimal_odds=quote.decimal_odds,
                payout_if_hit_2=payout,
                confidence_label=confidence_label("score", quote, probability),
                rank=rank,
                reason=(
                    f"体彩比分赔率{quote.decimal_odds:.2f}，折算占比约{probability_text(probability)}，"
                    f"2元一注中出返还{payout:.2f}元。"
                ),
            )
        )
    return candidates


def missing_decision(market: str) -> MarketDecision:
    label = market_label(market)
    missing = [f"体彩{label}赔率缺失"]
    summary = f"没有抓到体彩{label}赔率；这项暂时不推荐，等赔率数据刷新后再看。"
    return MarketDecision(
        market=market,
        market_label=label,
        official_model=None,
        team_model=None,
        combined_model=None,
        model_weights=None,
        score_candidates=[],
        model_suggestions=[],
        market_favorite=None,
        best_return=None,
        missing_info=missing,
        model_selection=None,
        model_selection_label=None,
        model_probability=None,
        odds_selection=None,
        odds_selection_label=None,
        odds_decimal=None,
        odds_probability=None,
        edge=None,
        expected_value=None,
        advice_level="missing",
        advice_label="赔率缺失",
        summary=summary,
        reasons=[summary],
        warnings=missing,
    )


def build_decision_for_market(market: str, quotes: list[OddsQuote]) -> MarketDecision:
    favorite = favorite_quote(quotes)
    if favorite is None:
        return missing_decision(market)

    favorite, favorite_probability = favorite
    official = official_line(market, favorite, favorite_probability)
    return_quote = highest_return_quote(quotes)
    best_return = decision_option_from_quote(*return_quote) if return_quote else None
    market_favorite = decision_option_from_quote(favorite, favorite_probability)
    advice_level, advice_label = advice_level_and_label(market, favorite, favorite_probability)
    favorite_payout = payout_if_hit_2(favorite.decimal_odds)
    return_text = ""
    if best_return and best_return.decimal_odds and best_return.payout_if_hit_2 is not None:
        return_text = (
            f"最高返还是{best_return.label}，赔率{best_return.decimal_odds:.2f}，"
            f"2元中出返还{best_return.payout_if_hit_2:.2f}元。"
        )
    summary = (
        f"体彩{market_label(market)}最低赔率是{quote_label(favorite)} {favorite.decimal_odds:.2f}，"
        f"折算占比约{probability_text(favorite_probability)}，2元一注中出返还{favorite_payout:.2f}元。"
        f"{movement_text(favorite)}。{return_text}综合买法：{quote_label(favorite)}，{advice_label}。"
    )
    reasons = [*official.reasons]
    if return_text:
        reasons.append(return_text)
    reasons.append(f"综合买法：{quote_label(favorite)}，{advice_label}。")
    return MarketDecision(
        market=market,
        market_label=market_label(market),
        official_model=official,
        team_model=None,
        combined_model=None,
        model_weights=None,
        score_candidates=score_candidates_from_quotes(quotes, limit=5) if market == "score" else [],
        model_suggestions=[],
        market_favorite=market_favorite,
        best_return=best_return,
        missing_info=[],
        model_selection=None,
        model_selection_label=None,
        model_probability=None,
        odds_selection=favorite.selection,
        odds_selection_label=quote_label(favorite),
        odds_decimal=favorite.decimal_odds,
        odds_probability=favorite_probability,
        edge=None,
        expected_value=None,
        advice_level=advice_level,
        advice_label=advice_label,
        summary=summary,
        reasons=reasons,
        warnings=[],
    )


def build_market_decisions(
    match: MatchInput,
    model_probabilities: dict[str, dict[str, float]],
    score_matrix: list[ScoreProbability],
    team_provider=None,
) -> list[MarketDecision]:
    del model_probabilities, score_matrix, team_provider
    return [build_decision_for_market(market, official_quotes(match.odds, market)) for market in DECISION_MARKETS]
