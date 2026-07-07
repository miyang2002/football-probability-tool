from itertools import combinations
from functools import reduce
from operator import mul
from typing import Iterable

from app.domain import MatchAnalysis, ParlayLeg, ParlayRecommendation, PickRecommendation, RiskLevel, StrategyName
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
    stake: float = 100.0,
) -> tuple[str | None, str | None, list[str], list[str]]:
    strongest = max(legs, key=lambda leg: leg.probability, default=None)
    weakest = min(legs, key=lambda leg: leg.probability, default=None)
    strongest_label = strongest.label if strongest else None
    weakest_label = weakest.label if weakest else None
    expected_profit = expected_value * stake
    reasons = [
        f"{STRATEGY_LABELS[strategy]}方案会同时看模型概率、赔率划算度和单关风险。",
        f"组合总赔率 {combined_odds:.2f}，预计命中 {combined_probability:.1%}。",
        f"{stake:g}元一注长期理论盈亏约 {expected_profit:+.1f} 元。",
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


def parlay_from_legs(
    legs: list[ParlayLeg],
    strategy: StrategyName,
    value_label: str,
    explanation: str,
    warnings: list[str] | None = None,
    stake: float = 2.0,
) -> ParlayRecommendation:
    combined_probability = reduce(mul, (leg.probability for leg in legs), 1.0)
    combined_odds = reduce(mul, (leg.decimal_odds for leg in legs), 1.0)
    ev = combined_probability * combined_odds - 1.0
    risk = parlay_risk(legs)
    strongest_leg, weakest_leg, reasons, generated_warnings = build_parlay_reasons(
        legs,
        combined_probability,
        combined_odds,
        ev,
        strategy,
        stake,
    )
    all_warnings = [*(warnings or []), *generated_warnings]
    return ParlayRecommendation(
        strategy=strategy,
        strategy_label=STRATEGY_LABELS[strategy],
        leg_count=len(legs),
        legs=legs,
        combined_probability=combined_probability,
        combined_odds=combined_odds,
        expected_value=ev,
        probability_label=probability_label(combined_probability),
        value_label=value_label,
        payout_if_hit_100=combined_odds * 100,
        expected_profit_100=ev * 100,
        payout_if_hit_2=combined_odds * stake,
        expected_profit_2=ev * stake,
        strongest_leg=strongest_leg,
        weakest_leg=weakest_leg,
        risk=risk,
        explanation=explanation,
        reasons=reasons,
        warnings=all_warnings,
    )


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
                payout_if_hit_2=combined_odds * 2,
                expected_profit_2=ev * 2,
                strongest_leg=strongest_leg,
                weakest_leg=weakest_leg,
                risk=risk,
                explanation=explanation,
                reasons=reasons,
                warnings=warnings,
            )
        )

    return results


def build_selected_winner_parlays(
    picks: list[PickRecommendation],
    strategy: StrategyName = "balanced",
    max_legs: int = 4,
    stake: float = 2.0,
) -> list[ParlayRecommendation]:
    if not isinstance(strategy, str) or strategy not in VALID_STRATEGIES:
        raise ValueError("strategy must be conservative, balanced, or return_seeking")
    if not isinstance(max_legs, int) or isinstance(max_legs, bool) or not 2 <= max_legs <= 6:
        raise ValueError("max_legs must be an integer between 2 and 6")

    best_by_match: dict[str, PickRecommendation] = {}
    for pick in picks:
        if pick.market != "winner" or pick.decimal_odds is None:
            continue
        if pick.match_id not in best_by_match:
            best_by_match[pick.match_id] = pick

    ordered = list(best_by_match.values())
    results: list[ParlayRecommendation] = []
    for leg_count in range(2, min(max_legs, len(ordered)) + 1):
        for selected in combinations(ordered, leg_count):
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
            results.append(
                parlay_from_legs(
                    legs=list(legs),
                    strategy=strategy,
                    value_label=parlay_value_label(ev),
                    explanation=(
                        f"真实胜平负赔率 {leg_count}串1：预计命中 {combined_probability:.1%}，"
                        f"2元一注中出返还约 {combined_odds * stake:.1f} 元。"
                    ),
                    stake=stake,
                )
            )

    return sorted(results, key=lambda item: (item.leg_count, -item.combined_probability, -item.expected_value))


def score_leg_from_analysis(analysis: MatchAnalysis) -> ParlayLeg | None:
    if not analysis.top_scores:
        return None
    score = analysis.top_scores[0]
    if score.probability <= 0:
        return None
    selection = f"{score.home_goals}-{score.away_goals}"
    fair_odds = 1.0 / score.probability
    return ParlayLeg(
        match_id=analysis.match.match_id,
        match_label=f"{analysis.match.home.name} vs {analysis.match.away.name}",
        label=f"{analysis.match.home.name} vs {analysis.match.away.name} · 比分 · {selection}",
        market="score",
        selection=selection,
        selection_label=selection,
        probability=score.probability,
        decimal_odds=fair_odds,
        edge=0.0,
        risk="high",
        value_label="模型理论赔率",
    )


def build_score_parlays(
    analyses: list[MatchAnalysis],
    strategy: StrategyName = "balanced",
    max_legs: int = 4,
    stake: float = 2.0,
) -> list[ParlayRecommendation]:
    if not isinstance(strategy, str) or strategy not in VALID_STRATEGIES:
        raise ValueError("strategy must be conservative, balanced, or return_seeking")
    if not isinstance(max_legs, int) or isinstance(max_legs, bool) or not 2 <= max_legs <= 6:
        raise ValueError("max_legs must be an integer between 2 and 6")

    legs = [leg for analysis in analyses if (leg := score_leg_from_analysis(analysis)) is not None]
    results: list[ParlayRecommendation] = []
    for leg_count in range(2, min(max_legs, len(legs)) + 1):
        for selected in combinations(legs, leg_count):
            selected_legs = list(selected)
            combined_probability = reduce(mul, (leg.probability for leg in selected_legs), 1.0)
            if combined_probability <= 0:
                continue
            combined_odds = 1.0 / combined_probability
            adjusted_legs = [
                leg.model_copy(update={"decimal_odds": leg.decimal_odds})
                for leg in selected_legs
            ]
            parlay = parlay_from_legs(
                legs=adjusted_legs,
                strategy=strategy,
                value_label="模型理论赔率",
                explanation=(
                    f"比分串关 {leg_count}串1：每场采用模型最可能比分，"
                    f"预计命中 {combined_probability:.2%}，2元理论返还约 {combined_odds * stake:.1f} 元。"
                ),
                warnings=["比分串关使用模型理论赔率，不是真实体彩比分赔率。"],
                stake=stake,
            )
            parlay.combined_odds = combined_odds
            parlay.expected_value = 0.0
            parlay.payout_if_hit_100 = combined_odds * 100
            parlay.expected_profit_100 = 0.0
            parlay.payout_if_hit_2 = combined_odds * stake
            parlay.expected_profit_2 = 0.0
            results.append(parlay)

    return sorted(results, key=lambda item: (item.leg_count, -item.combined_probability))
