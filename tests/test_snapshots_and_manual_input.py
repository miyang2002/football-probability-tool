import asyncio

import httpx

from app.main import app


async def request(method: str, path: str, **kwargs):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.request(method, path, **kwargs)


def test_manual_analysis_accepts_match_payload():
    match = asyncio.run(request("GET", "/api/matches")).json()[0]
    match["context"]["home_injury_impact"] = 0.12

    response = asyncio.run(request("POST", "/api/analyze", json=match))

    assert response.status_code == 200
    payload = response.json()
    assert payload["match"]["context"]["home_injury_impact"] == 0.12
    assert payload["winner_probabilities"]


def test_snapshot_endpoint_persists_analysis():
    response = asyncio.run(request("POST", "/api/matches/wc-001/snapshots"))

    assert response.status_code == 200
    payload = response.json()
    assert payload["snapshot_id"] >= 1
