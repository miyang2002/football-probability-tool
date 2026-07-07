from app.domain import MarketProbability, MatchContext, OddsQuote
from app.model.recommendations import build_recommendations


def test_recommendation_calculates_edge_and_expected_value():
    markets = [
        MarketProbability(market="winner", selection="home", probability=0.56),
        MarketProbability(market="winner", selection="draw", probability=0.24),
        MarketProbability(market="winner", selection="away", probability=0.20),
    ]
    odds = [
        OddsQuote(market="winner", selection="home", decimal_odds=2.1),
        OddsQuote(market="winner", selection="draw", decimal_odds=3.3),
        OddsQuote(market="winner", selection="away", decimal_odds=4.2),
    ]

    picks = build_recommendations("m1", markets, odds, MatchContext(data_quality=0.85))

    assert picks[0].selection == "home"
    assert picks[0].expected_value is not None
    assert picks[0].expected_value > 0
    assert picks[0].risk in {"low", "medium", "high"}


def test_low_data_quality_adds_warning():
    markets = [MarketProbability(market="winner", selection="home", probability=0.54)]
    odds = [OddsQuote(market="winner", selection="home", decimal_odds=2.0)]

    picks = build_recommendations("m1", markets, odds, MatchContext(data_quality=0.45))

    assert any("Data quality" in warning for warning in picks[0].warnings)


def test_missing_odds_keeps_pick_without_price_metrics():
    markets = [MarketProbability(market="winner", selection="home", probability=0.54)]

    picks = build_recommendations("m1", markets, [], MatchContext())

    assert picks[0].decimal_odds is None
    assert picks[0].implied_probability is None
    assert picks[0].edge is None
    assert picks[0].expected_value is None
    assert any("No odds available" in warning for warning in picks[0].warnings)


def test_negative_edge_and_expected_value_are_allowed():
    markets = [MarketProbability(market="winner", selection="home", probability=0.40)]
    odds = [OddsQuote(market="winner", selection="home", decimal_odds=2.0)]

    picks = build_recommendations("m1", markets, odds, MatchContext())

    assert picks[0].edge is not None
    assert picks[0].edge < 0
    assert picks[0].expected_value is not None
    assert picks[0].expected_value < 0


def test_confidence_is_bounded():
    markets = [MarketProbability(market="winner", selection="home", probability=1.0)]

    picks = build_recommendations("m1", markets, [], MatchContext(data_quality=1.0))

    assert picks[0].confidence == 0.95


def test_sorting_keeps_negative_expected_value_below_unknown_value():
    markets = [
        MarketProbability(market="winner", selection="home", probability=0.55),
        MarketProbability(market="winner", selection="draw", probability=0.60),
        MarketProbability(market="winner", selection="away", probability=0.01),
    ]
    odds = [
        OddsQuote(market="winner", selection="home", decimal_odds=2.1),
        OddsQuote(market="winner", selection="away", decimal_odds=2.0),
    ]

    picks = build_recommendations("m1", markets, odds, MatchContext())

    assert [pick.selection for pick in picks] == ["home", "draw", "away"]
