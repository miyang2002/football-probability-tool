from app.domain import MarketProbability, MatchContext, OddsQuote, PickRecommendation, RiskLevel
from app.model.odds import expected_value, implied_probability


SELECTION_LABELS = {
    "home": "主胜",
    "draw": "平局",
    "away": "客胜",
}

MARKET_LABELS = {
    "winner": "胜平负",
    "total_goals": "总进球",
    "over_under": "大小球",
    "half_time": "半场胜平负",
    "score": "比分",
}


def selection_label(selection: str) -> str:
    if selection in SELECTION_LABELS:
        return SELECTION_LABELS[selection]
    if selection.startswith("over_"):
        return f"大于 {selection.removeprefix('over_')} 球"
    if selection.startswith("under_"):
        return f"小于 {selection.removeprefix('under_')} 球"
    if selection == "5+":
        return "5球以上"
    return selection


def market_label(market: str) -> str:
    return MARKET_LABELS.get(market, market)


def price_value_label(ev: float | None, edge: float | None) -> str:
    if ev is None or edge is None:
        return "没有赔率，无法判断"
    if ev >= 0.05 and edge >= 0.03:
        return "赔率偏划算"
    if ev >= 0:
        return "赔率基本合理"
    return "赔率偏低，回报不够"


def expected_profit_text(ev: float | None) -> str:
    if ev is None:
        return "没有赔率，无法估算长期盈亏。"
    amount = ev * 100
    if amount >= 0:
        return f"按当前赔率长期重复下注，理论上每100元约多{amount:.1f}元。"
    return f"按当前赔率长期重复下注，理论上每100元约少{abs(amount):.1f}元。"


def risk_from_context(context: MatchContext, edge: float | None) -> RiskLevel:
    uncertainty = (context.lineup_uncertainty + context.tactical_uncertainty) / 2
    if context.data_quality < 0.55 or uncertainty > 0.55:
        return "high"
    if edge is not None and edge > 0.08 and context.data_quality >= 0.75:
        return "low"
    return "medium"


def confidence_from_probability(probability: float, context: MatchContext) -> float:
    return round(min(0.95, probability * 0.75 + context.data_quality * 0.25), 4)


def primary_probability_floor(market: str) -> float:
    if market == "winner":
        return 0.30
    if market == "over_under":
        return 0.50
    return 0.0


def recommendation_sort_key(pick: PickRecommendation) -> tuple[int, float, float]:
    has_priced_market = pick.decimal_odds is not None
    primary_candidate = pick.model_probability >= primary_probability_floor(pick.market)
    value_score = pick.expected_value if pick.expected_value is not None else -1.0
    return (1 if has_priced_market else 0, 1 if primary_candidate else 0, pick.model_probability, value_score)


def build_recommendations(
    match_id: str,
    markets: list[MarketProbability],
    odds: list[OddsQuote],
    context: MatchContext,
    match_label: str | None = None,
) -> list[PickRecommendation]:
    odds_by_key = {(quote.market, quote.selection): quote for quote in odds}
    picks: list[PickRecommendation] = []

    for item in markets:
        quote = odds_by_key.get((item.market, item.selection))
        implied = implied_probability(quote.decimal_odds) if quote else None
        edge = item.probability - implied if implied is not None else None
        ev = expected_value(item.probability, quote.decimal_odds) if quote else None
        risk = risk_from_context(context, edge)
        value_label = price_value_label(ev, edge)
        pick_label = selection_label(item.selection)
        current_market_label = market_label(item.market)

        reasons = [f"模型认为「{current_market_label} - {pick_label}」出现概率为 {item.probability:.1%}。"]
        warnings: list[str] = []
        if edge is not None:
            reasons.append(f"赔率反推概率约为 {implied:.1%}，模型比赔率高 {edge:.1%}。")
        if ev is not None:
            reasons.append(expected_profit_text(ev))
        else:
            warnings.append("没有对应赔率，无法判断这个选择是否划算。")
        if context.data_quality < 0.6:
            warnings.append("数据质量偏低，需要人工复核。")
        if context.lineup_uncertainty > 0.45:
            warnings.append("首发阵容不确定，需要赛前再看一次。")
        if context.tactical_uncertainty > 0.45:
            warnings.append("战术信息不确定，模型稳定性会下降。")
        plain_summary = (
            f"模型认为「{pick_label}」概率是 {item.probability:.1%}，"
            f"赔率是否划算：{value_label}。{expected_profit_text(ev)}"
        )

        picks.append(
            PickRecommendation(
                match_id=match_id,
                match_label=match_label,
                market=item.market,
                selection=item.selection,
                model_probability=item.probability,
                decimal_odds=quote.decimal_odds if quote else None,
                implied_probability=implied,
                edge=edge,
                expected_value=ev,
                confidence=confidence_from_probability(item.probability, context),
                risk=risk,
                reasons=reasons,
                warnings=warnings,
                value_label=value_label,
                plain_summary=plain_summary,
            )
        )

    return sorted(picks, key=recommendation_sort_key, reverse=True)
