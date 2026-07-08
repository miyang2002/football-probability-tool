import asyncio

import httpx
import pytest

from app.data.providers import SampleDataProvider
from app.main import app
from app.routes import get_provider


@pytest.fixture(autouse=True)
def use_sample_provider():
    async def provider_override():
        return SampleDataProvider()

    app.dependency_overrides[get_provider] = provider_override
    yield
    app.dependency_overrides.clear()


def get_json(path: str):
    async def request():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(path)
            return response

    response = asyncio.run(request())
    assert response.status_code == 200
    return response.json()


def test_matches_endpoint_returns_sample_matches():
    payload = get_json("/api/matches")

    assert len(payload) >= 4
    assert payload[0]["match_id"]


def test_matches_endpoint_accepts_window_parameter():
    payload = get_json("/api/matches?window=7d")

    assert len(payload) >= 4
    assert payload[0]["match_id"]


def test_feed_status_endpoint_returns_provider_state():
    payload = get_json("/api/feed/status")

    assert payload["source"] == "sample"
    assert payload["healthy"] is True
    assert payload["refresh_seconds"] == 30


def test_official_odds_diagnostics_endpoint_returns_market_coverage():
    payload = get_json("/api/official-odds/diagnostics?window=7d")

    assert payload["status"]["source"]
    assert payload["match_count"] >= 1
    match = payload["matches"][0]
    assert "match_id" in match
    assert "markets" in match
    market_names = {market["market"] for market in match["markets"]}
    market_statuses = {market["market"]: market["status"] for market in match["markets"]}
    assert {"winner", "handicap_winner", "score", "total_goals", "half_full"}.issubset(market_names)
    assert market_statuses["winner"] == "missing"


def test_match_analysis_endpoint_returns_visualization_payload():
    payload = get_json("/api/matches/wc-001/analysis")

    assert payload["match"]["match_id"] == "wc-001"
    assert payload["winner_probabilities"]
    assert payload["score_probabilities"]
    assert payload["decision_comparisons"]
    assert payload["recommendations"]
    assert "模型参考" in payload["score_method_summary"]
    assert "胜平负赔率" in payload["odds_basis_summary"]
    winner_decision = next(item for item in payload["decision_comparisons"] if item["market"] == "winner")
    assert winner_decision["model_selection_label"]
    assert winner_decision["advice_label"]
    assert winner_decision["advice_label"] in {"建议", "小额参考", "谨慎", "放弃"}
    assert "model_suggestions" in winner_decision
    assert "market_favorite" in winner_decision
    assert "best_return" in winner_decision
    assert "missing_info" in winner_decision


def test_match_analysis_endpoint_returns_two_model_advice_and_score_candidates():
    payload = get_json("/api/matches/wc-001/analysis")
    score = next(item for item in payload["decision_comparisons"] if item["market"] == "score")

    assert "official_model" in score
    assert "team_model" in score
    assert "combined_model" in score
    assert "model_weights" in score
    assert "official" in score["model_weights"]
    assert "team" in score["model_weights"]
    assert isinstance(score["score_candidates"], list)
    assert "summary" in score
    assert "球队近况未抓到" in score["missing_info"]


def test_parlay_endpoint_supports_strategy_parameter():
    payload = get_json("/api/parlays?strategy=balanced")

    assert payload
    assert payload[0]["strategy"] == "balanced"
    assert payload[0]["strategy_label"] == "均衡"
    assert payload[0]["probability_label"]
    assert payload[0]["value_label"]
    assert payload[0]["expected_profit_100"] is not None
    assert payload[0]["strongest_leg"]
    assert payload[0]["weakest_leg"]
    assert payload[0]["reasons"]


def test_selected_parlays_endpoint_returns_winner_and_score_combinations_with_two_yuan_returns():
    payload = get_json("/api/selected-parlays?match_ids=wc-001&match_ids=wc-002&match_ids=wc-003&strategy=balanced")

    assert payload["selected_match_ids"] == ["wc-001", "wc-002", "wc-003"]
    assert payload["stake"] == 2
    assert payload["winner_parlays"]
    assert payload["score_parlays"]

    winner = payload["winner_parlays"][0]
    assert winner["leg_count"] == 2
    assert winner["payout_if_hit_2"] == pytest.approx(winner["combined_odds"] * 2)
    assert winner["expected_profit_2"] == pytest.approx(winner["expected_value"] * 2)
    assert {leg["match_id"] for leg in winner["legs"]}.issubset(set(payload["selected_match_ids"]))
    assert all(leg["market"] == "winner" for leg in winner["legs"])
    assert any("2元一注" in reason for reason in winner["reasons"])

    score = payload["score_parlays"][0]
    assert score["leg_count"] == 2
    assert score["payout_if_hit_2"] == pytest.approx(score["combined_odds"] * 2)
    assert score["expected_profit_2"] == pytest.approx(score["expected_value"] * 2)
    assert all(leg["market"] == "score" for leg in score["legs"])
    assert all("-" in leg["selection"] for leg in score["legs"])
    assert any("模型理论赔率" in warning for warning in score["warnings"])
