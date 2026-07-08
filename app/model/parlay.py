from itertools import combinations
from functools import reduce
from operator import mul
from typing import Iterable

from app.domain import MatchAnalysis, MatchInput, OddsQuote, ParlayLeg, ParlayRecommendation, PickRecommendation, RiskLevel, StrategyName
from app.model.official_odds_model import normalized_official_probabilities
from app.model.recommendations import market_label, selection_label


RISK_SCORE = {"low": 1.0, "medium": 0.6, "high": 0.25}
VALID_STRATEGIES = {"conservative", "balanced", "return_seeking"}
STRATEGY_LABELS = {
    "conservative": "稳健",
    "balanced": "均衡",
    "return_seeking": "博收益",
}
ODDS_PARLAY_MARKETS = ("winner", "handicap_winner", "total_goals", "half_full", "score")
MIN_PARLAY_MARKET_QUOTES = {
    "winner": 3,
    "handicap_winner": 3,
    "total_goals": 3,
    "half_full": 3,
    "score": 3,
}
MARKET_RISK_BASE = {
    "winner": "low",
    "handicap_winner": "medium",
    "total_goals": "medium",
    "half_full": "high",
    "score": "high",
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
    del expected_value
    return "真实赔率组合"


def probability_label(probability: float) -> str:
    del probability
    return "真实赔率参考"


def leg_display_label(pick: PickRecommendation) -> str:
    match_label = pick.match_label or pick.match_id
    return f"{match_label} · {market_label(pick.market)} · {selection_label(pick.selection)}"


def quote_display_label(quote: OddsQuote) -> str:
    return quote.selection_label or quote.selection


def official_market_quotes(match: MatchInput, market: str) -> list[OddsQuote]:
    return [quote for quote in match.odds if quote.market == market and quote.source == "sporttery"]


def odds_risk(market: str, probability: float, decimal_odds: float) -> RiskLevel:
    if market in {"score", "half_full"}:
        return "high"
    if decimal_odds <= 1.45 or probability >= 0.62:
        return "low"
    if decimal_odds <= 2.50 or probability >= 0.35:
        return "medium"
    return MARKET_RISK_BASE.get(market, "high")


def odds_value_label(quote: OddsQuote, probability: float, market_probabilities: dict[str, float], market_quotes: list[OddsQuote]) -> str:
    favorite_probability = max(market_probabilities.values()) if market_probabilities else probability
    highest_odds = max((item.decimal_odds for item in market_quotes), default=quote.decimal_odds)
    if probability >= favorite_probability:
        return "体彩低赔方向"
    if quote.decimal_odds >= highest_odds:
        return "体彩高回报方向"
    return "体彩均衡方向"


def leg_from_quote(match: MatchInput, quote: OddsQuote, probability: float, market_probabilities: dict[str, float], market_quotes: list[OddsQuote]) -> ParlayLeg:
    match_label = f"{match.home.name} vs {match.away.name}"
    label = f"{match_label} · {market_label(quote.market)} · {quote_display_label(quote)}"
    return ParlayLeg(
        match_id=match.match_id,
        match_label=match_label,
        label=label,
        market=quote.market,
        selection=quote.selection,
        selection_label=quote_display_label(quote),
        probability=probability,
        decimal_odds=quote.decimal_odds,
        edge=0.0,
        risk=odds_risk(quote.market, probability, quote.decimal_odds),
        value_label=odds_value_label(quote, probability, market_probabilities, market_quotes),
    )


def odds_candidate_legs(match: MatchInput) -> list[ParlayLeg]:
    legs: list[ParlayLeg] = []
    for market in ODDS_PARLAY_MARKETS:
        quotes = official_market_quotes(match, market)
        if len(quotes) < MIN_PARLAY_MARKET_QUOTES[market]:
            continue
        probabilities = normalized_official_probabilities(quotes)
        for quote in quotes:
            probability = probabilities.get(quote.selection)
            if probability is None:
                continue
            legs.append(leg_from_quote(match, quote, probability, probabilities, quotes))
    return legs


def strategy_leg_score(leg: ParlayLeg, strategy: StrategyName) -> float:
    risk_bonus = RISK_SCORE[leg.risk]
    odds_score = min(leg.decimal_odds / 12.0, 1.0)
    if strategy == "conservative":
        market_bonus = 0.10 if leg.market == "winner" else 0.0
        return leg.probability * 0.75 + risk_bonus * 0.20 + market_bonus
    if strategy == "return_seeking":
        return odds_score * 0.65 + leg.probability * 0.25 + risk_bonus * 0.10
    return leg.probability * 0.50 + odds_score * 0.30 + risk_bonus * 0.20


def select_strategy_leg(match: MatchInput, strategy: StrategyName) -> ParlayLeg | None:
    legs = odds_candidate_legs(match)
    if not legs:
        return None
    if strategy == "conservative":
        preferred = [leg for leg in legs if leg.risk != "high"] or legs
        return max(preferred, key=lambda leg: strategy_leg_score(leg, strategy))
    if strategy == "return_seeking":
        plausible = [leg for leg in legs if leg.probability >= 0.08] or legs
        return max(plausible, key=lambda leg: strategy_leg_score(leg, strategy))
    return max(legs, key=lambda leg: strategy_leg_score(leg, strategy))


def sort_parlays_for_strategy(items: list[ParlayRecommendation], strategy: StrategyName) -> list[ParlayRecommendation]:
    if strategy == "conservative":
        return sorted(items, key=lambda item: (-item.combined_probability, item.leg_count, item.combined_odds))
    if strategy == "return_seeking":
        return sorted(items, key=lambda item: (-item.payout_if_hit_2, item.leg_count, -item.combined_probability))
    return sorted(items, key=lambda item: (item.leg_count, -item.combined_probability, -item.payout_if_hit_2))


def build_odds_parlays(
    matches: list[MatchInput],
    strategy: StrategyName = "balanced",
    max_legs: int = 4,
    stake: float = 2.0,
) -> list[ParlayRecommendation]:
    if not isinstance(strategy, str) or strategy not in VALID_STRATEGIES:
        raise ValueError("strategy must be conservative, balanced, or return_seeking")
    if not isinstance(max_legs, int) or isinstance(max_legs, bool) or not 2 <= max_legs <= 6:
        raise ValueError("max_legs must be an integer between 2 and 6")

    selected_legs = [leg for match in matches if (leg := select_strategy_leg(match, strategy)) is not None]
    if len(selected_legs) < 2:
        return []

    results: list[ParlayRecommendation] = []
    for leg_count in range(2, min(max_legs, len(selected_legs)) + 1):
        for selected in combinations(selected_legs, leg_count):
            legs = list(selected)
            combined_odds = reduce(mul, (leg.decimal_odds for leg in legs), 1.0)
            results.append(
                parlay_from_legs(
                    legs=legs,
                    strategy=strategy,
                    value_label="真实赔率组合",
                    explanation=(
                        f"{STRATEGY_LABELS[strategy]} {leg_count}串1：真实赔率相乘为 {combined_odds:.2f}，"
                        f"2元一注中出返还约 {combined_odds * stake:.2f} 元。"
                    ),
                    stake=stake,
                )
            )

    return sort_parlays_for_strategy(results, strategy)[:6]


def build_parlay_reasons(
    legs: list[ParlayLeg],
    combined_probability: float,
    combined_odds: float,
    expected_value: float,
    strategy: StrategyName,
    stake: float = 100.0,
) -> tuple[str | None, str | None, list[str], list[str]]:
    del combined_probability
    del expected_value
    reasons = [
        f"{STRATEGY_LABELS[strategy]}方案按体彩真实赔率计算。",
        f"组合总赔率 {combined_odds:.2f}，{stake:g}元一注中出返还约 {combined_odds * stake:.2f} 元。",
    ]
    return None, None, reasons, []


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
    ev = 0.0
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
        expected_profit_100=0.0,
        payout_if_hit_2=combined_odds * stake,
        expected_profit_2=0.0,
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
            2.0,
        )
        explanation = (
            f"{STRATEGY_LABELS[strategy]} {leg_count}串1："
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
                        f"真实胜平负赔率 {leg_count}串1："
                        f"2元一注中出返还约 {combined_odds * stake:.1f} 元。"
                    ),
                    stake=stake,
                )
            )

    return sorted(results, key=lambda item: (item.leg_count, -item.combined_probability, -item.expected_value))


def score_leg_from_analysis(analysis: MatchAnalysis) -> ParlayLeg | None:
    del analysis
    return None


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
    del analyses, stake
    return []
