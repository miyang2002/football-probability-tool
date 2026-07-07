import asyncio

import httpx
import pytest

from app.main import app
from app.data.repository import PredictionRepository
from app.routes import get_repository


@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    yield
    app.dependency_overrides.clear()


def override_repository(tmp_path) -> PredictionRepository:
    repository = PredictionRepository(str(tmp_path / "snapshots.sqlite3"))

    async def dependency_override():
        return repository

    app.dependency_overrides[get_repository] = dependency_override
    return repository


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


def test_snapshot_endpoint_persists_analysis(tmp_path):
    override_repository(tmp_path)

    response = asyncio.run(request("POST", "/api/matches/wc-001/snapshots"))

    assert response.status_code == 200
    payload = response.json()
    assert payload["snapshot_id"] == 1
    assert payload["match_id"] == "wc-001"

    listed = asyncio.run(request("GET", "/api/matches/wc-001/snapshots"))

    assert listed.status_code == 200
    rows = listed.json()
    assert len(rows) == 1
    assert rows[0]["id"] == 1
    assert rows[0]["payload"]["match"]["match_id"] == "wc-001"


def test_snapshot_endpoints_return_404_for_unknown_match(tmp_path):
    override_repository(tmp_path)

    save_response = asyncio.run(request("POST", "/api/matches/nope/snapshots"))
    list_response = asyncio.run(request("GET", "/api/matches/nope/snapshots"))

    assert save_response.status_code == 404
    assert list_response.status_code == 404
