import pytest

from app.domain import PickRecommendation
from app.model.parlay import build_parlays


def pick(match_id: str, probability: float, odds: float, edge: float, risk: str) -> PickRecommendation:
    return PickRecommendation(
        match_id=match_id,
        match_label=f"{match_id}主队 vs {match_id}客队",
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
        value_label="赔率偏划算",
        plain_summary="模型认为主胜有优势。",
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
    assert parlays[0].strategy_label == "均衡"
    assert parlays[0].probability_label.startswith("预计命中")
    assert parlays[0].value_label in {"赔率组合偏划算", "赔率组合一般", "赔率组合回报不够"}
    assert parlays[0].payout_if_hit_100 == pytest.approx(parlays[0].combined_odds * 100)
    assert parlays[0].expected_profit_100 == pytest.approx(parlays[0].expected_value * 100)
    assert parlays[0].strongest_leg is not None
    assert parlays[0].weakest_leg is not None
    assert any("最稳一关" in reason for reason in parlays[0].reasons)
    assert "EV" not in parlays[0].explanation


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


def test_empty_picks_return_no_parlays():
    assert build_parlays([], strategy="balanced", max_legs=4) == []


def test_one_eligible_pick_returns_no_parlays():
    picks = [pick("m1", 0.62, 1.9, 0.09, "low")]

    assert build_parlays(picks, strategy="balanced", max_legs=4) == []


def test_fewer_unique_matches_than_requested_returns_available_leg_counts():
    picks = [
        pick("m1", 0.62, 1.9, 0.09, "low"),
        pick("m2", 0.59, 2.0, 0.08, "medium"),
        pick("m3", 0.55, 2.2, 0.07, "medium"),
    ]

    parlays = build_parlays(picks, strategy="balanced", max_legs=6)

    assert [item.leg_count for item in parlays] == [2, 3]


@pytest.mark.parametrize("strategy", ["", "aggressive", None, []])
def test_invalid_strategy_raises_even_without_eligible_picks(strategy):
    with pytest.raises(ValueError):
        build_parlays([], strategy=strategy, max_legs=4)


@pytest.mark.parametrize("max_legs", [1, 7, 2.5, True])
def test_invalid_max_legs_raises(max_legs):
    with pytest.raises(ValueError):
        build_parlays([pick("m1", 0.62, 1.9, 0.09, "low"), pick("m2", 0.59, 2.0, 0.08, "medium")], max_legs=max_legs)
