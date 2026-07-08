from app.data.team_info import MissingTeamInfoProvider, team_model_weight
from app.domain import MatchInput, TeamInput


def match() -> MatchInput:
    return MatchInput(
        match_id="m1",
        competition="世界杯",
        kickoff_utc="2026-07-10T04:00:00Z",
        home=TeamInput(name="法国", attack_rating=1.1, defense_rating=0.9),
        away=TeamInput(name="摩洛哥", attack_rating=0.9, defense_rating=1.0),
    )


def test_missing_team_info_provider_returns_visible_missing_information():
    snapshot = MissingTeamInfoProvider().snapshot(match())

    assert snapshot.match_id == "m1"
    assert snapshot.quality == 0.0
    assert "球队近况未抓到" in snapshot.missing_info
    assert "伤停信息缺失" in snapshot.missing_info
    assert all(fact.affects_model is False for fact in snapshot.facts)


def test_team_model_weight_is_dynamic_from_quality():
    missing = MissingTeamInfoProvider().snapshot(match())

    assert team_model_weight(missing) == 0.0
