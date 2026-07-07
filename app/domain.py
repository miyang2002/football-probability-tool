from typing import Literal

from pydantic import BaseModel, Field


MarketName = Literal["winner", "total_goals", "half_time", "score"]
StrategyName = Literal["conservative", "balanced", "return_seeking"]
RiskLevel = Literal["low", "medium", "high"]


class TeamInput(BaseModel):
    name: str
    attack_rating: float = Field(gt=0)
    defense_rating: float = Field(gt=0)
    recent_goals_for: float = Field(default=1.4, ge=0)
    recent_goals_against: float = Field(default=1.2, ge=0)


class MatchContext(BaseModel):
    home_injury_impact: float = Field(default=0.0, ge=0, le=0.5)
    away_injury_impact: float = Field(default=0.0, ge=0, le=0.5)
    lineup_uncertainty: float = Field(default=0.2, ge=0, le=1)
    tactical_uncertainty: float = Field(default=0.2, ge=0, le=1)
    data_quality: float = Field(default=0.7, ge=0, le=1)
    notes: list[str] = Field(default_factory=list)


class OddsQuote(BaseModel):
    market: MarketName
    selection: str
    decimal_odds: float = Field(gt=1)


class MatchInput(BaseModel):
    match_id: str
    competition: str
    kickoff_utc: str
    home: TeamInput
    away: TeamInput
    neutral_venue: bool = True
    context: MatchContext = Field(default_factory=MatchContext)
    odds: list[OddsQuote] = Field(default_factory=list)


class ScoreProbability(BaseModel):
    home_goals: int
    away_goals: int
    probability: float


class MarketProbability(BaseModel):
    market: str
    selection: str
    probability: float


class PickRecommendation(BaseModel):
    match_id: str
    market: str
    selection: str
    model_probability: float
    decimal_odds: float | None = None
    implied_probability: float | None = None
    edge: float | None = None
    expected_value: float | None = None
    confidence: float
    risk: RiskLevel
    reasons: list[str]
    warnings: list[str]


class MatchAnalysis(BaseModel):
    match: MatchInput
    expected_home_goals: float
    expected_away_goals: float
    winner_probabilities: list[MarketProbability]
    half_time_probabilities: list[MarketProbability]
    total_goal_probabilities: list[MarketProbability]
    over_under_probabilities: list[MarketProbability]
    score_probabilities: list[ScoreProbability]
    top_scores: list[ScoreProbability]
    recommendations: list[PickRecommendation]
    data_quality: float


class ParlayRequest(BaseModel):
    strategy: StrategyName = "balanced"
    max_legs: int = Field(default=4, ge=2, le=6)


class ParlayLeg(BaseModel):
    match_id: str
    label: str
    market: str
    selection: str
    probability: float
    decimal_odds: float
    edge: float
    risk: RiskLevel


class ParlayRecommendation(BaseModel):
    strategy: StrategyName
    leg_count: int
    legs: list[ParlayLeg]
    combined_probability: float
    combined_odds: float
    expected_value: float
    risk: RiskLevel
    explanation: str
