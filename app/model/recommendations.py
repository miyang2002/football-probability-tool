from app.domain import MarketProbability, MatchContext, OddsQuote, PickRecommendation, RiskLevel
from app.model.odds import expected_value, implied_probability


def risk_from_context(context: MatchContext, edge: float | None) -> RiskLevel:
    uncertainty = (context.lineup_uncertainty + context.tactical_uncertainty) / 2
    if context.data_quality < 0.55 or uncertainty > 0.55:
        return "high"
    if edge is not None and edge > 0.08 and context.data_quality >= 0.75:
        return "low"
    return "medium"


def confidence_from_probability(probability: float, context: MatchContext) -> float:
    return round(min(0.95, probability * 0.75 + context.data_quality * 0.25), 4)


def recommendation_sort_key(pick: PickRecommendation) -> tuple[int, float, float]:
    if pick.expected_value is None:
        return (1, pick.model_probability, 0.0)
    if pick.expected_value >= 0:
        return (2, pick.expected_value, pick.model_probability)
    return (0, pick.expected_value, pick.model_probability)


def build_recommendations(
    match_id: str,
    markets: list[MarketProbability],
    odds: list[OddsQuote],
    context: MatchContext,
) -> list[PickRecommendation]:
    odds_by_key = {(quote.market, quote.selection): quote for quote in odds}
    picks: list[PickRecommendation] = []

    for item in markets:
        quote = odds_by_key.get((item.market, item.selection))
        implied = implied_probability(quote.decimal_odds) if quote else None
        edge = item.probability - implied if implied is not None else None
        ev = expected_value(item.probability, quote.decimal_odds) if quote else None
        risk = risk_from_context(context, edge)

        reasons = [f"Model probability is {item.probability:.1%}."]
        warnings: list[str] = []
        if edge is not None:
            reasons.append(f"Model edge versus raw implied probability is {edge:.1%}.")
        if ev is not None:
            reasons.append(f"Expected value is {ev:.1%}.")
        else:
            warnings.append("No odds available; edge and expected value were not calculated.")
        if context.data_quality < 0.6:
            warnings.append("Data quality is low, so this pick needs manual review.")
        if context.lineup_uncertainty > 0.45:
            warnings.append("Lineup uncertainty is elevated.")

        picks.append(
            PickRecommendation(
                match_id=match_id,
                market=item.market,
                selection=item.selection,
                model_probability=item.probability,
                decimal_odds=quote.decimal_odds if quote else None,
                implied_probability=implied,
                edge=edge,
                expected_value=ev,
                confidence=confidence_from_probability(item.probability, context),
                risk=risk,
                reasons=reasons,
                warnings=warnings,
            )
        )

    return sorted(picks, key=recommendation_sort_key, reverse=True)
