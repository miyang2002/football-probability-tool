from functools import reduce
from operator import mul
from typing import Iterable

from app.domain import ParlayLeg, ParlayRecommendation, PickRecommendation, RiskLevel, StrategyName
from app.model.recommendations import market_label, selection_label


RISK_SCORE = {"low": 1.0, "medium": 0.6, "high": 0.25}
VALID_STRATEGIES = {"conservative", "balanced", "return_seeking"}
STRATEGY_LABELS = {
    "conservative": "稳健",
    "balanced": "均衡",
    "return_seeking": "博收益",
}


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


def parlay_value_label(expected_value: float) -> str:
    if expected_value >= 0.12:
        return "赔率组合偏划算"
    if expected_value >= 0:
        return "赔率组合一般"
    return "赔率组合回报不够"


def probability_label(probability: float) -> str:
    return f"预计命中 {probability:.1%}，约等于100次里中{round(probability * 100)}次"


def leg_display_label(pick: PickRecommendation) -> str:
    match_label = pick.match_label or pick.match_id
    return f"{match_label} · {market_label(pick.market)} · {selection_label(pick.selection)}"


def build_parlay_reasons(
    legs: list[ParlayLeg],
    combined_probability: float,
    combined_odds: float,
    expected_value: float,
    strategy: StrategyName,
) -> tuple[str | None, str | None, list[str], list[str]]:
    strongest = max(legs, key=lambda leg: leg.probability, default=None)
    weakest = min(legs, key=lambda leg: leg.probability, default=None)
    strongest_label = strongest.label if strongest else None
    weakest_label = weakest.label if weakest else None
    expected_profit = expected_value * 100
    reasons = [
        f"{STRATEGY_LABELS[strategy]}方案会同时看模型概率、赔率划算度和单关风险。",
        f"组合总赔率 {combined_odds:.2f}，预计命中 {combined_probability:.1%}。",
        f"100元长期理论盈亏约 {expected_profit:+.1f} 元。",
    ]
    warnings: list[str] = []
    if strongest:
        reasons.append(f"最稳一关：{strongest.label}，模型概率 {strongest.probability:.1%}。")
    if weakest:
        reasons.append(f"拖后腿一关：{weakest.label}，模型概率 {weakest.probability:.1%}，需要重点复核。")
    if any(leg.risk == "high" for leg in legs):
        warnings.append("组合里有风险偏高的单关，不适合重仓。")
    if len(legs) >= 4:
        warnings.append("串关场次越多，命中率下降越快。")
    if expected_value < 0:
        warnings.append("模型看下来赔率回报不够，建议谨慎或放弃。")

    return strongest_label, weakest_label, reasons, warnings


def build_parlays(
    picks: list[PickRecommendation],
    strategy: StrategyName = "balanced",
    max_legs: int = 4,
) -> list[ParlayRecommendation]:
    if not isinstance(strategy, str) or strategy not in VALID_STRATEGIES:
        raise ValueError("strategy must be conservative, balanced, or return_seeking")
    if not isinstance(max_legs, int) or isinstance(max_legs, bool) or not 2 <= max_legs <= 6:
        raise ValueError("max_legs must be an integer between 2 and 6")

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
                match_label=pick.match_label,
                label=leg_display_label(pick),
                market=pick.market,
                selection=pick.selection,
                selection_label=selection_label(pick.selection),
                probability=pick.model_probability,
                decimal_odds=pick.decimal_odds or 1.0,
                edge=pick.edge or 0.0,
                risk=pick.risk,
                value_label=pick.value_label,
            )
            for pick in selected
        ]
        combined_probability = reduce(mul, (leg.probability for leg in legs), 1.0)
        combined_odds = reduce(mul, (leg.decimal_odds for leg in legs), 1.0)
        ev = combined_probability * combined_odds - 1.0
        risk = parlay_risk(legs)
        strongest_leg, weakest_leg, reasons, warnings = build_parlay_reasons(
            legs,
            combined_probability,
            combined_odds,
            ev,
            strategy,
        )
        explanation = (
            f"{STRATEGY_LABELS[strategy]} {leg_count}串1：预计命中 {combined_probability:.1%}，"
            f"总赔率 {combined_odds:.2f}，{parlay_value_label(ev)}。"
        )
        results.append(
            ParlayRecommendation(
                strategy=strategy,
                strategy_label=STRATEGY_LABELS[strategy],
                leg_count=leg_count,
                legs=legs,
                combined_probability=combined_probability,
                combined_odds=combined_odds,
                expected_value=ev,
                probability_label=probability_label(combined_probability),
                value_label=parlay_value_label(ev),
                payout_if_hit_100=combined_odds * 100,
                expected_profit_100=ev * 100,
                strongest_leg=strongest_leg,
                weakest_leg=weakest_leg,
                risk=risk,
                explanation=explanation,
                reasons=reasons,
                warnings=warnings,
            )
        )

    return results
