import pytest
from pydantic import ValidationError

from app.domain import (
    MarketProbability,
    MatchAnalysis,
    MatchContext,
    MatchInput,
    DecisionOption,
    MarketDecision,
    OfficialMarketDiagnostic,
    OfficialOddsMatchDiagnostic,
    OddsQuote,
    ParlayLeg,
    ParlayRecommendation,
    PickRecommendation,
    ScoreProbability,
    SourceStatus,
    TeamInput,
)


def test_match_input_accepts_core_fields():
    match = MatchInput(
        match_id="m1",
        competition="World Cup",
        kickoff_utc="2026-07-08T19:00:00Z",
        home=TeamInput(name="France", attack_rating=1.25, defense_rating=0.88),
        away=TeamInput(name="Brazil", attack_rating=1.18, defense_rating=0.93),
        neutral_venue=True,
        context=MatchContext(home_injury_impact=0.08, away_injury_impact=0.03, data_quality=0.82),
        odds=[
            OddsQuote(market="winner", selection="home", decimal_odds=2.15),
            OddsQuote(market="winner", selection="draw", decimal_odds=3.20),
            OddsQuote(market="winner", selection="away", decimal_odds=3.40),
        ],
    )

    assert match.home.name == "France"
    assert match.context.data_quality == 0.82
    assert match.odds[0].decimal_odds == 2.15


def test_official_market_diagnostic_accepts_available_market_with_quotes():
    diagnostic = OfficialMarketDiagnostic(
        market="score",
        label="比分",
        status="available",
        odds_count=2,
        odds=[
            OddsQuote(
                market="score",
                selection="2-1",
                selection_label="2-1",
                decimal_odds=9.0,
                source="sporttery",
                raw_selection="0102",
            )
        ],
        warnings=[],
    )

    assert diagnostic.market == "score"
    assert diagnostic.status == "available"
    assert diagnostic.odds[0].selection_label == "2-1"
    assert diagnostic.odds[0].raw_selection == "0102"


def test_official_odds_match_diagnostic_lists_missing_markets():
    diagnostic = OfficialOddsMatchDiagnostic(
        match_id="sporttery-2040427",
        home_name="阿根廷",
        away_name="埃及",
        kickoff_utc="2026-07-07T16:00:00Z",
        competition="世界杯",
        markets=[
            OfficialMarketDiagnostic(market="winner", label="胜平负", status="available", odds_count=3),
            OfficialMarketDiagnostic(market="score", label="比分", status="missing", odds_count=0),
        ],
    )

    assert diagnostic.missing_markets == ["score"]


def test_market_decision_accepts_model_and_odds_recommendations():
    decision = MarketDecision(
        market="winner",
        market_label="胜平负",
        model_suggestions=[
            DecisionOption(
                selection="home",
                label="主胜",
                probability=0.58,
                decimal_odds=1.8,
                payout_if_hit_2=3.6,
            )
        ],
        market_favorite=DecisionOption(selection="home", label="主胜", decimal_odds=1.8, payout_if_hit_2=3.6),
        best_return=DecisionOption(selection="draw", label="平局", decimal_odds=3.3, payout_if_hit_2=6.6),
        model_selection="home",
        model_selection_label="主胜",
        model_probability=0.58,
        odds_selection="home",
        odds_selection_label="主胜",
        odds_decimal=1.8,
        odds_probability=0.54,
        edge=0.04,
        expected_value=0.044,
        advice_level="balanced",
        advice_label="小额参考",
        summary="模型和赔率方向一致。",
        reasons=["模型推荐主胜。"],
        warnings=[],
    )

    assert decision.model_selection_label == "主胜"
    assert decision.odds_selection_label == "主胜"
    assert decision.advice_label == "小额参考"
    assert decision.model_suggestions[0].payout_if_hit_2 == 3.6
    assert decision.market_favorite.label == "主胜"
    assert decision.best_return.label == "平局"


def test_context_defaults_are_conservative():
    context = MatchContext()

    assert context.home_injury_impact == 0.0
    assert context.away_injury_impact == 0.0
    assert context.lineup_uncertainty == 0.2
    assert context.data_quality == 0.7


@pytest.mark.parametrize("field", ["attack_rating", "defense_rating"])
def test_team_input_rejects_non_positive_ratings(field):
    data = {"name": "France", "attack_rating": 1.25, "defense_rating": 0.88}
    data[field] = 0.0

    with pytest.raises(ValidationError):
        TeamInput(**data)


def test_odds_quote_rejects_decimal_odds_at_even_money():
    with pytest.raises(ValidationError):
        OddsQuote(market="winner", selection="home", decimal_odds=1.0)


def test_match_context_rejects_data_quality_above_one():
    with pytest.raises(ValidationError):
        MatchContext(data_quality=1.5)


def test_market_probability_rejects_probability_above_one():
    with pytest.raises(ValidationError):
        MarketProbability(market="winner", selection="home", probability=1.2)


def test_market_probability_rejects_unknown_market():
    with pytest.raises(ValidationError):
        MarketProbability(market="corners", selection="over_9.5", probability=0.5)


def test_match_context_notes_are_isolated_between_instances():
    first = MatchContext()
    second = MatchContext()

    first.notes.append("lineup pending")

    assert second.notes == []


def test_match_input_odds_are_isolated_between_instances():
    home = TeamInput(name="France", attack_rating=1.25, defense_rating=0.88)
    away = TeamInput(name="Brazil", attack_rating=1.18, defense_rating=0.93)
    first = MatchInput(match_id="m1", competition="World Cup", kickoff_utc="2026-07-08T19:00:00Z", home=home, away=away)
    second = MatchInput(match_id="m2", competition="World Cup", kickoff_utc="2026-07-09T19:00:00Z", home=home, away=away)

    first.odds.append(OddsQuote(market="winner", selection="home", decimal_odds=2.15))

    assert second.odds == []


def test_market_probability_accepts_over_under_market():
    probability = MarketProbability(market="over_under", selection="over_2.5", probability=0.55)

    assert probability.market == "over_under"


def test_score_probability_rejects_negative_goals():
    with pytest.raises(ValidationError):
        ScoreProbability(home_goals=-1, away_goals=0, probability=0.1)


def test_score_probability_rejects_negative_probability():
    with pytest.raises(ValidationError):
        ScoreProbability(home_goals=1, away_goals=0, probability=-0.1)


def test_pick_recommendation_rejects_impossible_probability_fields():
    base = {
        "match_id": "m1",
        "market": "winner",
        "selection": "home",
        "model_probability": 0.55,
        "implied_probability": 0.5,
        "confidence": 0.6,
        "risk": "medium",
        "reasons": [],
        "warnings": [],
    }

    for field in ["model_probability", "implied_probability", "confidence"]:
        data = {**base, field: 1.2}
        with pytest.raises(ValidationError):
            PickRecommendation(**data)


def test_pick_recommendation_rejects_unknown_market():
    with pytest.raises(ValidationError):
        PickRecommendation(
            match_id="m1",
            market="corners",
            selection="over_9.5",
            model_probability=0.55,
            confidence=0.6,
            risk="medium",
            reasons=[],
            warnings=[],
        )


def test_pick_recommendation_rejects_decimal_odds_at_even_money():
    with pytest.raises(ValidationError):
        PickRecommendation(
            match_id="m1",
            market="winner",
            selection="home",
            model_probability=0.55,
            decimal_odds=1.0,
            confidence=0.6,
            risk="medium",
            reasons=[],
            warnings=[],
        )


def test_pick_recommendation_rejects_edge_above_one():
    with pytest.raises(ValidationError):
        PickRecommendation(
            match_id="m1",
            market="winner",
            selection="home",
            model_probability=0.55,
            edge=1.2,
            confidence=0.6,
            risk="medium",
            reasons=[],
            warnings=[],
        )


def test_pick_recommendation_rejects_expected_value_below_total_loss():
    with pytest.raises(ValidationError):
        PickRecommendation(
            match_id="m1",
            market="winner",
            selection="home",
            model_probability=0.55,
            expected_value=-1.1,
            confidence=0.6,
            risk="medium",
            reasons=[],
            warnings=[],
        )


def test_pick_recommendation_allows_negative_edge_and_expected_value():
    pick = PickRecommendation(
        match_id="m1",
        market="winner",
        selection="home",
        model_probability=0.4,
        decimal_odds=2.0,
        implied_probability=0.5,
        edge=-0.1,
        expected_value=-0.2,
        confidence=0.6,
        risk="medium",
        reasons=[],
        warnings=[],
    )

    assert pick.edge == -0.1
    assert pick.expected_value == -0.2


def test_match_analysis_rejects_negative_expected_goals():
    match = MatchInput(
        match_id="m1",
        competition="World Cup",
        kickoff_utc="2026-07-08T19:00:00Z",
        home=TeamInput(name="France", attack_rating=1.25, defense_rating=0.88),
        away=TeamInput(name="Brazil", attack_rating=1.18, defense_rating=0.93),
    )

    with pytest.raises(ValidationError):
        MatchAnalysis(
            match=match,
            expected_home_goals=-0.1,
            expected_away_goals=1.0,
            winner_probabilities=[],
            half_time_probabilities=[],
            total_goal_probabilities=[],
            over_under_probabilities=[],
            score_probabilities=[],
            top_scores=[],
            recommendations=[],
            data_quality=0.8,
        )


def test_match_analysis_rejects_data_quality_above_one():
    match = MatchInput(
        match_id="m1",
        competition="World Cup",
        kickoff_utc="2026-07-08T19:00:00Z",
        home=TeamInput(name="France", attack_rating=1.25, defense_rating=0.88),
        away=TeamInput(name="Brazil", attack_rating=1.18, defense_rating=0.93),
    )

    with pytest.raises(ValidationError):
        MatchAnalysis(
            match=match,
            expected_home_goals=1.2,
            expected_away_goals=1.0,
            winner_probabilities=[],
            half_time_probabilities=[],
            total_goal_probabilities=[],
            over_under_probabilities=[],
            score_probabilities=[],
            top_scores=[],
            recommendations=[],
            data_quality=1.5,
        )


def test_parlay_leg_rejects_probability_above_one():
    with pytest.raises(ValidationError):
        ParlayLeg(
            match_id="m1",
            label="France win",
            market="winner",
            selection="home",
            probability=1.2,
            decimal_odds=2.0,
            edge=-0.05,
            risk="medium",
        )


def test_parlay_leg_rejects_even_money_odds():
    with pytest.raises(ValidationError):
        ParlayLeg(
            match_id="m1",
            label="France win",
            market="winner",
            selection="home",
            probability=0.55,
            decimal_odds=1.0,
            edge=-0.05,
            risk="medium",
        )


def test_parlay_leg_allows_negative_edge():
    leg = ParlayLeg(
        match_id="m1",
        label="France win",
        market="winner",
        selection="home",
        probability=0.55,
        decimal_odds=2.0,
        edge=-0.05,
        risk="medium",
    )

    assert leg.edge == -0.05


def test_parlay_leg_rejects_unknown_market():
    with pytest.raises(ValidationError):
        ParlayLeg(
            match_id="m1",
            label="Corners over",
            market="corners",
            selection="over_9.5",
            probability=0.55,
            decimal_odds=2.0,
            edge=0.04,
            risk="medium",
        )


def test_parlay_leg_accepts_over_under_market():
    leg = ParlayLeg(
        match_id="m1",
        label="Over 2.5",
        market="over_under",
        selection="over_2.5",
        probability=0.55,
        decimal_odds=2.0,
        edge=0.04,
        risk="medium",
    )

    assert leg.market == "over_under"


def test_parlay_recommendation_rejects_combined_probability_above_one():
    with pytest.raises(ValidationError):
        ParlayRecommendation(
            strategy="balanced",
            leg_count=2,
            legs=[],
            combined_probability=1.2,
            combined_odds=2.5,
            expected_value=-0.1,
            risk="medium",
            explanation="Too much probability",
        )


def test_parlay_recommendation_rejects_combined_odds_at_even_money():
    with pytest.raises(ValidationError):
        ParlayRecommendation(
            strategy="balanced",
            leg_count=2,
            legs=[],
            combined_probability=0.4,
            combined_odds=1.0,
            expected_value=-0.1,
            risk="medium",
            explanation="No payout",
        )


def test_parlay_recommendation_allows_negative_expected_value():
    recommendation = ParlayRecommendation(
        strategy="balanced",
        leg_count=2,
        legs=[],
        combined_probability=0.4,
        combined_odds=2.0,
        expected_value=-0.2,
        risk="medium",
        explanation="Negative edge parlay",
    )

    assert recommendation.expected_value == -0.2


def test_odds_quote_accepts_live_source_metadata():
    quote = OddsQuote(
        market="winner",
        selection="home",
        decimal_odds=1.72,
        source="sporttery",
        updated_at="2026-07-07T12:07:51Z",
        previous_decimal_odds=1.69,
        movement="up",
    )

    assert quote.source == "sporttery"
    assert quote.previous_decimal_odds == 1.69
    assert quote.movement == "up"


def test_source_status_serializes_refresh_state():
    status = SourceStatus(
        source="sporttery",
        healthy=True,
        using_fallback=False,
        last_attempt_at="2026-07-07T12:08:01Z",
        last_success_at="2026-07-07T12:08:00Z",
        refresh_seconds=30,
        message="Live odds loaded",
    )

    payload = status.model_dump()

    assert payload["source"] == "sporttery"
    assert payload["healthy"] is True
    assert payload["refresh_seconds"] == 30
