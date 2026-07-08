from types import SimpleNamespace

from app.domain import MatchContext, MatchInput, OddsQuote, PickRecommendation, TeamInput
from app.services import analyze_match, collect_best_picks


def pick(match_id: str, selection: str, probability: float, edge: float | None) -> PickRecommendation:
    odds = 2.2 if edge is not None else None
    return PickRecommendation(
        match_id=match_id,
        market="winner",
        selection=selection,
        model_probability=probability,
        decimal_odds=odds,
        implied_probability=(1 / odds) if odds else None,
        edge=edge,
        expected_value=(probability * odds - 1) if odds else None,
        confidence=probability,
        risk="medium",
        reasons=["test"],
        warnings=[],
    )


def test_collect_best_picks_includes_later_priced_eligible_recommendations(monkeypatch):
    def fake_analyze_match(match):
        return SimpleNamespace(
            recommendations=[
                pick(match.match_id, "away", 0.40, 0.12),
                pick(match.match_id, "home", 0.55, 0.08),
            ]
        )

    monkeypatch.setattr("app.services.analyze_match", fake_analyze_match)

    picks = collect_best_picks([SimpleNamespace(match_id="m1"), SimpleNamespace(match_id="m2")])

    assert [item.selection for item in picks] == ["away", "home", "away", "home"]


def test_analysis_builds_five_plain_market_decisions_with_payouts():
    match = MatchInput(
        match_id="m1",
        competition="世界杯",
        kickoff_utc="2026-07-10T04:00:00Z",
        home=TeamInput(name="法国", attack_rating=1.28, defense_rating=0.88),
        away=TeamInput(name="摩洛哥", attack_rating=0.92, defense_rating=0.95),
        context=MatchContext(data_quality=0.85, notes=["让球 -1"]),
        odds=[
            OddsQuote(market="winner", selection="home", decimal_odds=1.40, source="sporttery", selection_label="主胜"),
            OddsQuote(market="winner", selection="draw", decimal_odds=3.85, source="sporttery", selection_label="平局"),
            OddsQuote(market="winner", selection="away", decimal_odds=6.45, source="sporttery", selection_label="客胜"),
            OddsQuote(market="handicap_winner", selection="home", decimal_odds=2.55, source="sporttery", selection_label="让球主胜"),
            OddsQuote(market="handicap_winner", selection="draw", decimal_odds=3.35, source="sporttery", selection_label="让球平"),
            OddsQuote(market="handicap_winner", selection="away", decimal_odds=2.30, source="sporttery", selection_label="让球客胜"),
            OddsQuote(market="score", selection="1-0", decimal_odds=5.80, source="sporttery", selection_label="1-0"),
            OddsQuote(market="score", selection="2-0", decimal_odds=6.50, source="sporttery", selection_label="2-0"),
            OddsQuote(market="score", selection="2-1", decimal_odds=8.50, source="sporttery", selection_label="2-1"),
            OddsQuote(market="total_goals", selection="2", decimal_odds=3.60, source="sporttery", selection_label="2球"),
            OddsQuote(market="total_goals", selection="3", decimal_odds=3.80, source="sporttery", selection_label="3球"),
            OddsQuote(market="total_goals", selection="4", decimal_odds=5.20, source="sporttery", selection_label="4球"),
            OddsQuote(market="half_full", selection="home_home", decimal_odds=2.10, source="sporttery", selection_label="胜胜"),
            OddsQuote(market="half_full", selection="draw_home", decimal_odds=4.80, source="sporttery", selection_label="平胜"),
            OddsQuote(market="half_full", selection="draw_draw", decimal_odds=7.00, source="sporttery", selection_label="平平"),
        ],
    )

    analysis = analyze_match(match)
    decisions = {decision.market: decision for decision in analysis.decision_comparisons}

    assert set(decisions) == {"winner", "handicap_winner", "score", "total_goals", "half_full"}
    assert all(decision.advice_label in {"建议", "小额参考", "谨慎", "放弃"} for decision in decisions.values())
    assert decisions["winner"].model_suggestions
    assert decisions["handicap_winner"].model_suggestions
    assert decisions["score"].model_suggestions
    assert len(decisions["score"].model_suggestions) == 3
    assert decisions["total_goals"].model_suggestions
    assert decisions["half_full"].model_suggestions
    assert decisions["score"].market_favorite.payout_if_hit_2 == 11.6
    assert decisions["score"].best_return.payout_if_hit_2 is not None
    assert decisions["winner"].missing_info == []
