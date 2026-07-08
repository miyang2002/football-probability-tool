from types import SimpleNamespace

from app.domain import MatchContext, MatchInput, OddsQuote, PickRecommendation, TeamInput
from app.services import analyze_match, build_selected_parlay_analysis, collect_best_picks


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
    assert all(decision.advice_label in {"可作串关胆", "可以参考", "谨慎参考", "娱乐参考", "赔率缺失"} for decision in decisions.values())
    assert decisions["winner"].official_model.selection == "home"
    assert [option.label for option in decisions["winner"].model_suggestions] == ["主胜", "平局", "客胜"]
    assert decisions["winner"].team_model is None
    assert decisions["winner"].combined_model is None
    assert decisions["winner"].model_weights is None
    assert decisions["handicap_winner"].official_model.selection == "away"
    assert [option.label for option in decisions["handicap_winner"].model_suggestions] == ["让球客胜", "让球主胜", "让球平"]
    assert decisions["score"].official_model.selection == "1-0"
    assert [option.label for option in decisions["score"].model_suggestions] == ["1-0", "2-0", "2-1"]
    assert len(decisions["score"].score_candidates) == 3
    assert decisions["total_goals"].official_model.selection == "2"
    assert [option.label for option in decisions["total_goals"].model_suggestions] == ["2球", "3球", "4球"]
    assert decisions["half_full"].official_model.selection == "home_home"
    assert [option.label for option in decisions["half_full"].model_suggestions] == ["胜胜", "平胜", "平平"]
    assert all(
        option.probability is not None
        for decision in decisions.values()
        for option in decision.model_suggestions
    )
    assert decisions["score"].market_favorite.payout_if_hit_2 == 11.6
    assert decisions["score"].best_return.payout_if_hit_2 is not None
    assert "官方胜平负赔率缺失" not in decisions["winner"].missing_info
    assert decisions["winner"].missing_info == []
    assert "体彩" in decisions["winner"].summary
    assert "球队" not in decisions["winner"].summary
    assert "模型" not in decisions["winner"].summary


def test_analysis_returns_official_odds_only_score_candidates():
    match = MatchInput(
        match_id="m-score",
        competition="世界杯",
        kickoff_utc="2026-07-10T04:00:00Z",
        home=TeamInput(name="法国", attack_rating=1.18, defense_rating=0.92),
        away=TeamInput(name="摩洛哥", attack_rating=0.91, defense_rating=1.05),
        context=MatchContext(data_quality=0.80, notes=["让球 -1"]),
        odds=[
            OddsQuote(market="winner", selection="home", decimal_odds=1.40, source="sporttery", selection_label="主胜"),
            OddsQuote(market="winner", selection="draw", decimal_odds=3.85, source="sporttery", selection_label="平局"),
            OddsQuote(market="winner", selection="away", decimal_odds=6.45, source="sporttery", selection_label="客胜"),
            OddsQuote(market="handicap_winner", selection="home", decimal_odds=2.55, source="sporttery", selection_label="让球主胜"),
            OddsQuote(market="handicap_winner", selection="draw", decimal_odds=3.35, source="sporttery", selection_label="让球平"),
            OddsQuote(market="handicap_winner", selection="away", decimal_odds=2.30, source="sporttery", selection_label="让球客胜"),
            OddsQuote(market="score", selection="1-0", decimal_odds=6.5, source="sporttery", selection_label="1-0"),
            OddsQuote(market="score", selection="2-0", decimal_odds=6.25, source="sporttery", selection_label="2-0"),
            OddsQuote(market="score", selection="home_other", decimal_odds=35.0, source="sporttery", selection_label="胜其它"),
            OddsQuote(market="score", selection="draw_other", decimal_odds=120.0, source="sporttery", selection_label="平其它"),
            OddsQuote(market="score", selection="away_other", decimal_odds=80.0, source="sporttery", selection_label="负其它"),
            OddsQuote(market="total_goals", selection="1", decimal_odds=4.20, source="sporttery", selection_label="1球"),
            OddsQuote(market="total_goals", selection="2", decimal_odds=3.20, source="sporttery", selection_label="2球"),
            OddsQuote(market="total_goals", selection="3", decimal_odds=3.80, source="sporttery", selection_label="3球"),
            OddsQuote(market="half_full", selection="home_home", decimal_odds=2.40, source="sporttery", selection_label="胜胜"),
            OddsQuote(market="half_full", selection="draw_home", decimal_odds=4.40, source="sporttery", selection_label="平胜"),
        ],
    )

    analysis = analyze_match(match)
    decisions = {decision.market: decision for decision in analysis.decision_comparisons}
    score_decision = decisions["score"]

    assert score_decision.official_model is not None
    assert score_decision.team_model is None
    assert score_decision.combined_model is None
    assert score_decision.model_weights is None
    assert score_decision.score_candidates
    assert any(candidate.selection == "home_other" for candidate in score_decision.score_candidates)
    assert all(candidate.team_probability is None for candidate in score_decision.score_candidates)
    assert all(candidate.combined_probability is None for candidate in score_decision.score_candidates)
    assert all(candidate.official_probability is not None for candidate in score_decision.score_candidates)
    assert "球队近况未抓到" not in score_decision.missing_info
    assert "2元" in score_decision.summary
    assert "模型" not in score_decision.summary


def test_different_score_odds_produce_different_official_score_recommendations():
    base = MatchInput(
        match_id="m-a",
        competition="世界杯",
        kickoff_utc="2026-07-10T04:00:00Z",
        home=TeamInput(name="A", attack_rating=1.0, defense_rating=1.0),
        away=TeamInput(name="B", attack_rating=1.0, defense_rating=1.0),
        context=MatchContext(notes=["让球 0"]),
        odds=[
            OddsQuote(market="winner", selection="home", decimal_odds=2.2, source="sporttery", selection_label="主胜"),
            OddsQuote(market="winner", selection="draw", decimal_odds=3.0, source="sporttery", selection_label="平局"),
            OddsQuote(market="winner", selection="away", decimal_odds=3.1, source="sporttery", selection_label="客胜"),
            OddsQuote(market="score", selection="1-0", decimal_odds=5.0, source="sporttery", selection_label="1-0"),
            OddsQuote(market="score", selection="2-1", decimal_odds=9.0, source="sporttery", selection_label="2-1"),
            OddsQuote(market="score", selection="draw_other", decimal_odds=100.0, source="sporttery", selection_label="平其它"),
        ],
    )
    changed = base.model_copy(
        update={
            "match_id": "m-b",
            "odds": [
                quote.model_copy(update={"decimal_odds": 4.5}) if quote.market == "score" and quote.selection == "2-1" else quote
                for quote in base.odds
            ],
        }
    )

    first_score = next(decision for decision in analyze_match(base).decision_comparisons if decision.market == "score")
    second_score = next(decision for decision in analyze_match(changed).decision_comparisons if decision.market == "score")

    assert first_score.official_model.selection == "1-0"
    assert second_score.official_model.selection == "2-1"


def test_selected_parlays_use_only_real_official_odds_from_all_markets():
    first = MatchInput(
        match_id="m1",
        competition="世界杯",
        kickoff_utc="2026-07-10T04:00:00Z",
        home=TeamInput(name="法国", attack_rating=1.0, defense_rating=1.0),
        away=TeamInput(name="摩洛哥", attack_rating=1.0, defense_rating=1.0),
        odds=[
            OddsQuote(market="winner", selection="home", decimal_odds=1.42, source="sporttery", selection_label="主胜", movement="down"),
            OddsQuote(market="winner", selection="draw", decimal_odds=3.85, source="sporttery", selection_label="平局"),
            OddsQuote(market="winner", selection="away", decimal_odds=6.45, source="sporttery", selection_label="客胜"),
            OddsQuote(market="handicap_winner", selection="home", decimal_odds=2.20, source="sporttery", selection_label="让球主胜"),
            OddsQuote(market="handicap_winner", selection="draw", decimal_odds=3.30, source="sporttery", selection_label="让球平"),
            OddsQuote(market="handicap_winner", selection="away", decimal_odds=2.80, source="sporttery", selection_label="让球客胜"),
            OddsQuote(market="score", selection="1-0", decimal_odds=5.80, source="sporttery", selection_label="1-0"),
            OddsQuote(market="score", selection="2-0", decimal_odds=6.20, source="sporttery", selection_label="2-0"),
            OddsQuote(market="score", selection="1-1", decimal_odds=7.00, source="sporttery", selection_label="1-1"),
            OddsQuote(market="total_goals", selection="2", decimal_odds=3.10, source="sporttery", selection_label="2球"),
            OddsQuote(market="total_goals", selection="3", decimal_odds=3.60, source="sporttery", selection_label="3球"),
            OddsQuote(market="total_goals", selection="4", decimal_odds=5.00, source="sporttery", selection_label="4球"),
            OddsQuote(market="half_full", selection="home_home", decimal_odds=2.30, source="sporttery", selection_label="胜胜"),
            OddsQuote(market="half_full", selection="draw_home", decimal_odds=4.20, source="sporttery", selection_label="平胜"),
            OddsQuote(market="half_full", selection="draw_draw", decimal_odds=6.80, source="sporttery", selection_label="平平"),
        ],
    )
    second = MatchInput(
        match_id="m2",
        competition="世界杯",
        kickoff_utc="2026-07-11T04:00:00Z",
        home=TeamInput(name="阿根廷", attack_rating=1.0, defense_rating=1.0),
        away=TeamInput(name="埃及", attack_rating=1.0, defense_rating=1.0),
        odds=[
            OddsQuote(market="winner", selection="home", decimal_odds=1.28, source="sporttery", selection_label="主胜", movement="flat"),
            OddsQuote(market="winner", selection="draw", decimal_odds=4.80, source="sporttery", selection_label="平局"),
            OddsQuote(market="winner", selection="away", decimal_odds=9.00, source="sporttery", selection_label="客胜"),
            OddsQuote(market="handicap_winner", selection="home", decimal_odds=1.95, source="sporttery", selection_label="让球主胜"),
            OddsQuote(market="handicap_winner", selection="draw", decimal_odds=3.40, source="sporttery", selection_label="让球平"),
            OddsQuote(market="handicap_winner", selection="away", decimal_odds=3.05, source="sporttery", selection_label="让球客胜"),
            OddsQuote(market="score", selection="2-0", decimal_odds=5.50, source="sporttery", selection_label="2-0"),
            OddsQuote(market="score", selection="1-0", decimal_odds=6.10, source="sporttery", selection_label="1-0"),
            OddsQuote(market="score", selection="2-1", decimal_odds=7.20, source="sporttery", selection_label="2-1"),
            OddsQuote(market="total_goals", selection="2", decimal_odds=3.10, source="sporttery", selection_label="2球"),
            OddsQuote(market="total_goals", selection="3", decimal_odds=3.40, source="sporttery", selection_label="3球"),
            OddsQuote(market="total_goals", selection="4", decimal_odds=4.80, source="sporttery", selection_label="4球"),
            OddsQuote(market="half_full", selection="home_home", decimal_odds=2.05, source="sporttery", selection_label="胜胜"),
            OddsQuote(market="half_full", selection="draw_home", decimal_odds=4.00, source="sporttery", selection_label="平胜"),
            OddsQuote(market="half_full", selection="draw_draw", decimal_odds=7.20, source="sporttery", selection_label="平平"),
        ],
    )

    payload = build_selected_parlay_analysis([first, second], ["m1", "m2"], "conservative")

    assert payload.winner_parlays
    assert payload.score_parlays == []
    markets = {parlay.legs[0].market for parlay in payload.winner_parlays}
    assert {"winner", "handicap_winner", "score", "total_goals", "half_full"}.issubset(markets)
    winner_parlay = next(parlay for parlay in payload.winner_parlays if parlay.legs[0].market == "winner")
    assert winner_parlay.combined_odds == 1.42 * 1.28
    assert winner_parlay.payout_if_hit_2 == winner_parlay.combined_odds * 2
    for parlay in payload.winner_parlays:
        leg_odds_product = 1.0
        for leg in parlay.legs:
            leg_odds_product *= leg.decimal_odds
        assert parlay.combined_odds == leg_odds_product
        assert parlay.payout_if_hit_2 == leg_odds_product * 2
        assert parlay.payout_if_hit_2 > max(leg.decimal_odds * 2 for leg in parlay.legs)
    assert all(leg.value_label in {"体彩低赔方向", "体彩均衡方向", "体彩高回报方向"} for parlay in payload.winner_parlays for leg in parlay.legs)
    assert all("真实赔率" in parlay.explanation for parlay in payload.winner_parlays)
    assert all("模型" not in parlay.explanation for parlay in payload.winner_parlays)
    forbidden = ["模型", "理论", "概率", "折算", "风险", "盈亏", "回报不够"]
    combined_text = " ".join(
        text
        for parlay in payload.winner_parlays
        for text in [parlay.explanation, parlay.value_label, *parlay.reasons, *parlay.warnings]
    )
    for word in forbidden:
        assert word not in combined_text
