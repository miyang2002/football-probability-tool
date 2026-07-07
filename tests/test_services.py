from types import SimpleNamespace

from app.domain import PickRecommendation
from app.services import collect_best_picks


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
