from typing import Literal

from pydantic import BaseModel, Field


MarketName = Literal[
    "winner",
    "handicap_winner",
    "score",
    "total_goals",
    "half_full",
    "over_under",
    "half_time",
]
StrategyName = Literal["conservative", "balanced", "return_seeking"]
RiskLevel = Literal["low", "medium", "high"]
OddsMovement = Literal["up", "down", "flat"]
OfficialMarketStatus = Literal["available", "missing", "suspended", "malformed"]


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
    source: str | None = None
    updated_at: str | None = None
    previous_decimal_odds: float | None = Field(default=None, gt=1)
    movement: OddsMovement | None = None
    selection_label: str | None = None
    raw_selection: str | None = None


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
    home_goals: int = Field(ge=0)
    away_goals: int = Field(ge=0)
    probability: float = Field(ge=0, le=1)
    outcome: str | None = None
    outcome_label: str | None = None
    related_odds: float | None = Field(default=None, gt=1)
    odds_value_label: str | None = None
    explanation: str | None = None


class MarketProbability(BaseModel):
    market: MarketName
    selection: str
    probability: float = Field(ge=0, le=1)


class PickRecommendation(BaseModel):
    match_id: str
    match_label: str | None = None
    market: MarketName
    selection: str
    model_probability: float = Field(ge=0, le=1)
    decimal_odds: float | None = Field(default=None, gt=1)
    implied_probability: float | None = Field(default=None, ge=0, le=1)
    edge: float | None = Field(default=None, ge=-1, le=1)
    expected_value: float | None = Field(default=None, ge=-1)
    confidence: float = Field(ge=0, le=1)
    risk: RiskLevel
    reasons: list[str]
    warnings: list[str]
    value_label: str = "没有赔率，无法判断"
    plain_summary: str = ""


class MatchAnalysis(BaseModel):
    match: MatchInput
    expected_home_goals: float = Field(ge=0)
    expected_away_goals: float = Field(ge=0)
    score_method_summary: str
    odds_basis_summary: str
    winner_probabilities: list[MarketProbability]
    half_time_probabilities: list[MarketProbability]
    total_goal_probabilities: list[MarketProbability]
    over_under_probabilities: list[MarketProbability]
    score_probabilities: list[ScoreProbability]
    top_scores: list[ScoreProbability]
    recommendations: list[PickRecommendation]
    data_quality: float = Field(ge=0, le=1)


class ParlayRequest(BaseModel):
    strategy: StrategyName = "balanced"
    max_legs: int = Field(default=4, ge=2, le=6)


class ParlayLeg(BaseModel):
    match_id: str
    match_label: str | None = None
    label: str
    market: MarketName
    selection: str
    selection_label: str = ""
    probability: float = Field(ge=0, le=1)
    decimal_odds: float = Field(gt=1)
    edge: float = Field(ge=-1, le=1)
    risk: RiskLevel
    value_label: str = "没有赔率，无法判断"


class ParlayRecommendation(BaseModel):
    strategy: StrategyName
    strategy_label: str = ""
    leg_count: int
    legs: list[ParlayLeg]
    combined_probability: float = Field(ge=0, le=1)
    combined_odds: float = Field(gt=1)
    expected_value: float = Field(ge=-1)
    probability_label: str = ""
    value_label: str = "没有赔率，无法判断"
    payout_if_hit_100: float = Field(default=0.0, ge=0)
    expected_profit_100: float = 0.0
    payout_if_hit_2: float = Field(default=0.0, ge=0)
    expected_profit_2: float = 0.0
    strongest_leg: str | None = None
    weakest_leg: str | None = None
    risk: RiskLevel
    explanation: str
    reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class SelectedParlayAnalysis(BaseModel):
    selected_match_ids: list[str]
    stake: float = Field(default=2.0, gt=0)
    winner_parlays: list[ParlayRecommendation] = Field(default_factory=list)
    score_parlays: list[ParlayRecommendation] = Field(default_factory=list)


class SourceStatus(BaseModel):
    source: str
    healthy: bool
    using_fallback: bool
    last_attempt_at: str | None = None
    last_success_at: str | None = None
    refresh_seconds: int = Field(gt=0)
    message: str


class OfficialMarketDiagnostic(BaseModel):
    market: MarketName
    label: str
    status: OfficialMarketStatus
    odds_count: int = Field(ge=0)
    odds: list[OddsQuote] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class OfficialOddsMatchDiagnostic(BaseModel):
    match_id: str
    home_name: str
    away_name: str
    kickoff_utc: str
    competition: str
    markets: list[OfficialMarketDiagnostic]

    @property
    def missing_markets(self) -> list[str]:
        return [market.market for market in self.markets if market.status != "available"]


class OfficialOddsDiagnostics(BaseModel):
    status: SourceStatus
    match_count: int = Field(ge=0)
    matches: list[OfficialOddsMatchDiagnostic]
