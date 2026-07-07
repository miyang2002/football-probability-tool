from math import isfinite


def implied_probability(decimal_odds: float) -> float:
    if not isfinite(decimal_odds) or decimal_odds <= 1:
        raise ValueError("decimal_odds must be finite and greater than 1")
    return 1.0 / decimal_odds


def normalize_market_probabilities(selection_odds: dict[str, float]) -> dict[str, float]:
    raw = {selection: implied_probability(odds) for selection, odds in selection_odds.items()}
    total = sum(raw.values())
    if total <= 0:
        raise ValueError("market must contain at least one valid odds quote")
    return {selection: probability / total for selection, probability in raw.items()}


def expected_value(model_probability: float, decimal_odds: float) -> float:
    if not isfinite(model_probability) or not 0 <= model_probability <= 1:
        raise ValueError("model_probability must be finite and between 0 and 1")
    if not isfinite(decimal_odds) or decimal_odds <= 1:
        raise ValueError("decimal_odds must be finite and greater than 1")
    return model_probability * decimal_odds - 1.0
