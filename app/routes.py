from fastapi import APIRouter, HTTPException, Query

from app.data.providers import SampleDataProvider
from app.domain import StrategyName
from app.services import analyze_match, build_parlay_recommendations


router = APIRouter()
provider = SampleDataProvider()


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
