import asyncio

import httpx

from app.main import app


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


def test_match_analysis_endpoint_returns_visualization_payload():
    payload = get_json("/api/matches/wc-001/analysis")

    assert payload["match"]["match_id"] == "wc-001"
    assert payload["winner_probabilities"]
    assert payload["score_probabilities"]
    assert payload["top_scores"]
    assert payload["recommendations"]


def test_parlay_endpoint_supports_strategy_parameter():
    payload = get_json("/api/parlays?strategy=balanced")

    assert payload
    assert payload[0]["strategy"] == "balanced"
