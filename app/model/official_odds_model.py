from app.domain import ModelAdviceLine, OddsQuote
from app.model.odds import implied_probability


def payout_if_hit_2(decimal_odds: float | None) -> float | None:
    if decimal_odds is None:
        return None
    return round(decimal_odds * 2, 2)


def quote_label(quote: OddsQuote) -> str:
    return quote.selection_label or quote.selection


def normalized_official_probabilities(quotes: list[OddsQuote]) -> dict[str, float]:
    raw = {quote.selection: implied_probability(quote.decimal_odds) for quote in quotes if quote.decimal_odds > 1}
    total = sum(raw.values())
    if total <= 0:
        return {}
    return {selection: probability / total for selection, probability in raw.items()}


def market_favorite(market: str, quotes: list[OddsQuote]) -> ModelAdviceLine | None:
    probabilities = normalized_official_probabilities(quotes)
    if not probabilities:
        return None
    quote_by_selection = {quote.selection: quote for quote in quotes}
    selection = max(probabilities, key=probabilities.get)
    quote = quote_by_selection[selection]
    label = quote_label(quote)
    return ModelAdviceLine(
        source="official_odds",
        label=f"体彩更看好{label}",
        selection=quote.selection,
        selection_label=label,
        probability=probabilities[selection],
        decimal_odds=quote.decimal_odds,
        payout_if_hit_2=payout_if_hit_2(quote.decimal_odds),
        confidence_label="中",
        rank=1,
        reasons=[f"{label}在{market}玩法中市场概率最高。"],
    )


def best_return_reference(
    market: str,
    quotes: list[OddsQuote],
    model_probabilities: dict[str, float],
    min_probability_ratio: float = 0.35,
) -> ModelAdviceLine | None:
    if not quotes or not model_probabilities:
        return None
    max_probability = max(model_probabilities.values()) if model_probabilities else 0.0
    if max_probability <= 0:
        return None
    quote_by_selection = {quote.selection: quote for quote in quotes}
    candidates = []
    for selection, probability in model_probabilities.items():
        quote = quote_by_selection.get(selection)
        if quote is None or probability < max_probability * min_probability_ratio:
            continue
        candidates.append((quote, probability, probability * quote.decimal_odds))
    if not candidates:
        return None
    quote, probability, _ = max(candidates, key=lambda item: item[2])
    label = quote_label(quote)
    return ModelAdviceLine(
        source="official_odds",
        label=f"回报参考{label}",
        selection=quote.selection,
        selection_label=label,
        probability=probability,
        decimal_odds=quote.decimal_odds,
        payout_if_hit_2=payout_if_hit_2(quote.decimal_odds),
        confidence_label="中",
        rank=None,
        reasons=[f"{label}在模型候选中2元返还更高。"],
    )


def official_model_line(market: str, quotes: list[OddsQuote]) -> ModelAdviceLine | None:
    return market_favorite(market, quotes)
