from app.domain import PickRecommendation
from app.model.parlay import build_parlays


def pick(match_id: str, probability: float, odds: float, edge: float, risk: str) -> PickRecommendation:
    return PickRecommendation(
        match_id=match_id,
        market="winner",
        selection="home",
        model_probability=probability,
        decimal_odds=odds,
        implied_probability=1 / odds,
        edge=edge,
        expected_value=probability * odds - 1,
        confidence=probability,
        risk=risk,
        reasons=["test"],
        warnings=[],
    )


def test_balanced_parlay_returns_two_three_and_four_leg_options():
    picks = [
        pick("m1", 0.62, 1.9, 0.09, "low"),
        pick("m2", 0.59, 2.0, 0.08, "medium"),
        pick("m3", 0.55, 2.2, 0.07, "medium"),
        pick("m4", 0.51, 2.5, 0.06, "high"),
    ]

    parlays = build_parlays(picks, strategy="balanced", max_legs=4)

    assert [item.leg_count for item in parlays] == [2, 3, 4]
    assert parlays[0].combined_probability > parlays[-1].combined_probability
    assert parlays[-1].combined_odds > parlays[0].combined_odds


def test_optimizer_uses_strategy_to_change_ordering():
    picks = [
        pick("safe", 0.72, 1.55, 0.07, "low"),
        pick("value", 0.49, 2.75, 0.13, "medium"),
        pick("mid", 0.58, 2.0, 0.08, "medium"),
    ]

    conservative = build_parlays(picks, strategy="conservative", max_legs=2)[0]
    return_seeking = build_parlays(picks, strategy="return_seeking", max_legs=2)[0]

    assert conservative.legs[0].match_id == "safe"
    assert any(leg.match_id == "value" for leg in return_seeking.legs)


def test_optimizer_keeps_only_one_pick_per_match():
    picks = [
        pick("same", 0.72, 1.7, 0.12, "low"),
        pick("same", 0.68, 1.9, 0.11, "low"),
        pick("other", 0.58, 2.0, 0.08, "medium"),
    ]

    parlay = build_parlays(picks, strategy="balanced", max_legs=2)[0]

    assert [leg.match_id for leg in parlay.legs].count("same") == 1
    assert {leg.match_id for leg in parlay.legs} == {"same", "other"}
