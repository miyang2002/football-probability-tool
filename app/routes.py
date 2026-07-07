from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, Query

from app.data.providers import MatchProvider, build_provider
from app.data.repository import PredictionRepository
from app.domain import MatchInput, StrategyName
from app.services import analysis_payload, analyze_match, build_parlay_recommendations


router = APIRouter()


@lru_cache(maxsize=1)
def _get_repository() -> PredictionRepository:
    return PredictionRepository()


async def get_repository() -> PredictionRepository:
    return _get_repository()


@lru_cache(maxsize=1)
def _get_provider() -> MatchProvider:
    return build_provider()


async def get_provider() -> MatchProvider:
    return _get_provider()


@router.get("/api/matches")
async def list_matches(window: str = Query(default="next"), provider: MatchProvider = Depends(get_provider)):
    return provider.list_matches(window=window)


@router.get("/api/feed/status")
async def feed_status(provider: MatchProvider = Depends(get_provider)):
    return provider.status()


@router.get("/api/matches/{match_id}/analysis")
async def get_match_analysis(match_id: str, provider: MatchProvider = Depends(get_provider)):
    match = provider.get_match(match_id)
    if match is None:
        raise HTTPException(status_code=404, detail="Match not found")
    return analyze_match(match)


@router.get("/api/parlays")
async def get_parlays(
    strategy: StrategyName = Query(default="balanced"),
    window: str = Query(default="next"),
    provider: MatchProvider = Depends(get_provider),
):
    return build_parlay_recommendations(provider.list_matches(window=window), strategy)


@router.post("/api/analyze")
async def analyze_manual_match(match: MatchInput):
    return analyze_match(match)


@router.post("/api/matches/{match_id}/snapshots")
async def save_match_snapshot(
    match_id: str,
    repository: PredictionRepository = Depends(get_repository),
    provider: MatchProvider = Depends(get_provider),
):
    match = provider.get_match(match_id)
    if match is None:
        raise HTTPException(status_code=404, detail="Match not found")
    snapshot_id = repository.save_snapshot(match_id, analysis_payload(match))
    return {"snapshot_id": snapshot_id, "match_id": match_id}


@router.get("/api/matches/{match_id}/snapshots")
async def list_match_snapshots(
    match_id: str,
    repository: PredictionRepository = Depends(get_repository),
    provider: MatchProvider = Depends(get_provider),
):
    if provider.get_match(match_id) is None:
        raise HTTPException(status_code=404, detail="Match not found")
    return repository.list_snapshots(match_id)
