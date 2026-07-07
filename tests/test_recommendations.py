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
    assert picks[0].value_label in {"赔率偏划算", "赔率基本合理", "赔率偏低，回报不够"}
    assert "模型认为" in picks[0].plain_summary
    assert "EV" not in picks[0].plain_summary
    assert any("赔率反推概率" in reason for reason in picks[0].reasons)


def test_low_probability_longshot_does_not_become_primary_pick_from_odds_value_only():
    markets = [
        MarketProbability(market="winner", selection="home", probability=0.58),
        MarketProbability(market="winner", selection="draw", probability=0.254),
        MarketProbability(market="winner", selection="away", probability=0.166),
    ]
    odds = [
        OddsQuote(market="winner", selection="home", decimal_odds=1.55),
        OddsQuote(market="winner", selection="draw", decimal_odds=3.80),
        OddsQuote(market="winner", selection="away", decimal_odds=8.00),
    ]

    picks = build_recommendations("arg-egypt", markets, odds, MatchContext(data_quality=0.85))

    assert picks[0].selection == "home"
    assert picks[0].model_probability == 0.58
    assert picks[0].expected_value is not None
    assert picks[0].expected_value < 0
    assert picks[-1].selection == "away"
    assert picks[-1].expected_value is not None
    assert picks[-1].expected_value > 0


def test_priced_winner_pick_outranks_unpriced_model_market_for_primary_recommendation():
    markets = [
        MarketProbability(market="winner", selection="home", probability=0.43),
        MarketProbability(market="winner", selection="draw", probability=0.26),
        MarketProbability(market="winner", selection="away", probability=0.31),
        MarketProbability(market="over_under", selection="over_1.5", probability=0.74),
    ]
    odds = [
        OddsQuote(market="winner", selection="home", decimal_odds=2.22),
        OddsQuote(market="winner", selection="draw", decimal_odds=3.20),
        OddsQuote(market="winner", selection="away", decimal_odds=3.10),
    ]

    picks = build_recommendations("m1", markets, odds, MatchContext(data_quality=0.85))

    assert picks[0].market == "winner"
    assert picks[0].selection == "home"
    assert picks[0].decimal_odds == 2.22
    assert picks[0].value_label != "没有赔率，无法判断"
    assert any(pick.market == "over_under" and pick.decimal_odds is None for pick in picks)


def test_low_data_quality_adds_warning():
    markets = [MarketProbability(market="winner", selection="home", probability=0.54)]
    odds = [OddsQuote(market="winner", selection="home", decimal_odds=2.0)]

    picks = build_recommendations("m1", markets, odds, MatchContext(data_quality=0.45))

    assert any("数据质量偏低" in warning for warning in picks[0].warnings)


def test_high_tactical_uncertainty_adds_warning():
    markets = [MarketProbability(market="winner", selection="home", probability=0.54)]
    odds = [OddsQuote(market="winner", selection="home", decimal_odds=2.0)]

    picks = build_recommendations(
        "m1",
        markets,
        odds,
        MatchContext(data_quality=0.8, lineup_uncertainty=0.2, tactical_uncertainty=1.0),
    )

    assert picks[0].risk == "high"
    assert any("战术信息不确定" in warning for warning in picks[0].warnings)


def test_missing_odds_keeps_pick_without_price_metrics():
    markets = [MarketProbability(market="winner", selection="home", probability=0.54)]

    picks = build_recommendations("m1", markets, [], MatchContext())

    assert picks[0].decimal_odds is None
    assert picks[0].implied_probability is None
    assert picks[0].edge is None
    assert picks[0].expected_value is None
    assert picks[0].value_label == "没有赔率，无法判断"
    assert any("没有对应赔率" in warning for warning in picks[0].warnings)


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


def test_sorting_prioritizes_priced_market_before_unpriced_model_pick():
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

    assert [pick.selection for pick in picks] == ["home", "away", "draw"]
