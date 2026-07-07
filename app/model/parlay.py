from functools import reduce
from operator import mul
from typing import Iterable

from app.domain import ParlayLeg, ParlayRecommendation, PickRecommendation, RiskLevel, StrategyName


RISK_SCORE = {"low": 1.0, "medium": 0.6, "high": 0.25}


def score_pick(pick: PickRecommendation, strategy: StrategyName) -> float:
    probability = pick.model_probability
    edge = max(pick.edge or 0.0, 0.0)
    ev = max(pick.expected_value or -1.0, -1.0)
    odds = pick.decimal_odds or 1.0
    low_risk = RISK_SCORE[pick.risk]

    if strategy == "conservative":
        return probability * 0.60 + edge * 0.25 + low_risk * 0.15
    if strategy == "return_seeking":
        return max(ev, 0.0) * 0.50 + min(odds / 5.0, 1.0) * 0.30 + probability * 0.20
    return probability * 0.40 + edge * 0.40 + low_risk * 0.20


def parlay_risk(legs: Iterable[ParlayLeg]) -> RiskLevel:
    risks = [leg.risk for leg in legs]
    if "high" in risks or len(risks) >= 4:
        return "high"
    if "medium" in risks or len(risks) == 3:
        return "medium"
    return "low"


def build_parlays(
    picks: list[PickRecommendation],
    strategy: StrategyName = "balanced",
    max_legs: int = 4,
) -> list[ParlayRecommendation]:
    eligible = [
        pick
        for pick in picks
        if pick.decimal_odds is not None
        and pick.edge is not None
        and pick.edge > 0
        and pick.model_probability >= 0.45
    ]
    ordered_by_score = sorted(eligible, key=lambda item: score_pick(item, strategy), reverse=True)
    best_by_match: dict[str, PickRecommendation] = {}
    for pick in ordered_by_score:
        if pick.match_id not in best_by_match:
            best_by_match[pick.match_id] = pick
    ordered = list(best_by_match.values())

    results: list[ParlayRecommendation] = []
    for leg_count in range(2, min(max_legs, len(ordered)) + 1):
        selected = ordered[:leg_count]
        legs = [
            ParlayLeg(
                match_id=pick.match_id,
                label=f"{pick.match_id} {pick.market} {pick.selection}",
                market=pick.market,
                selection=pick.selection,
                probability=pick.model_probability,
                decimal_odds=pick.decimal_odds or 1.0,
                edge=pick.edge or 0.0,
                risk=pick.risk,
            )
            for pick in selected
        ]
        combined_probability = reduce(mul, (leg.probability for leg in legs), 1.0)
        combined_odds = reduce(mul, (leg.decimal_odds for leg in legs), 1.0)
        ev = combined_probability * combined_odds - 1.0
        risk = parlay_risk(legs)
        explanation = (
            f"{leg_count}-leg combination selected by {strategy} scoring. "
            f"Combined hit probability is {combined_probability:.1%}; expected value is {ev:.1%}."
        )
        results.append(
            ParlayRecommendation(
                strategy=strategy,
                leg_count=leg_count,
                legs=legs,
                combined_probability=combined_probability,
                combined_odds=combined_odds,
                expected_value=ev,
                risk=risk,
                explanation=explanation,
            )
        )

    return results
