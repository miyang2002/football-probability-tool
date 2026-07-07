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


def test_match_analysis_endpoint_returns_visualization_payload():
    payload = get_json("/api/matches/wc-001/analysis")

    assert payload["match"]["match_id"] == "wc-001"
    assert payload["winner_probabilities"]
    assert payload["score_probabilities"]
    assert payload["top_scores"]
    assert payload["recommendations"]
    assert "泊松分布" in payload["score_method_summary"]
    assert "胜平负赔率" in payload["odds_basis_summary"]
    assert payload["top_scores"][0]["outcome_label"] in {"主胜", "平局", "客胜"}
    assert payload["top_scores"][0]["odds_value_label"]
    assert "赔率" in payload["top_scores"][0]["explanation"]


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
