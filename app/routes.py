from fastapi import APIRouter, HTTPException, Query

from app.data.providers import SampleDataProvider
from app.data.repository import PredictionRepository
from app.domain import MatchInput, StrategyName
from app.services import analysis_payload, analyze_match, build_parlay_recommendations


router = APIRouter()
provider = SampleDataProvider()
repository = PredictionRepository()


@router.get("/api/matches")
async def list_matches():
    return provider.list_matches()


@router.get("/api/matches/{match_id}/analysis")
async def get_match_analysis(match_id: str):
    match = provider.get_match(match_id)
    if match is None:
        raise HTTPException(status_code=404, detail="Match not found")
    return analyze_match(match)


@router.get("/api/parlays")
async def get_parlays(strategy: StrategyName = Query(default="balanced")):
    return build_parlay_recommendations(provider.list_matches(), strategy)


@router.post("/api/analyze")
async def analyze_manual_match(match: MatchInput):
    return analyze_match(match)


@router.post("/api/matches/{match_id}/snapshots")
async def save_match_snapshot(match_id: str):
    match = provider.get_match(match_id)
    if match is None:
        raise HTTPException(status_code=404, detail="Match not found")
    snapshot_id = repository.save_snapshot(match_id, analysis_payload(match))
    return {"snapshot_id": snapshot_id, "match_id": match_id}


@router.get("/api/matches/{match_id}/snapshots")
async def list_match_snapshots(match_id: str):
    return repository.list_snapshots(match_id)
