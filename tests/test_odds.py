from app.model.odds import expected_value, implied_probability, normalize_market_probabilities


def test_implied_probability_from_decimal_odds():
    assert round(implied_probability(2.5), 4) == 0.4


def test_normalize_market_probabilities_removes_overround():
    normalized = normalize_market_probabilities({"home": 2.0, "draw": 3.2, "away": 4.0})

    assert round(sum(normalized.values()), 6) == 1.0
    assert normalized["home"] > normalized["away"]


def test_expected_value_uses_model_probability_and_decimal_odds():
    assert round(expected_value(0.55, 2.1), 4) == 0.155
