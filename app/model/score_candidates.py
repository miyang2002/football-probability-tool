from collections import defaultdict

from app.domain import OddsQuote, ScoreCandidate, ScoreProbability
from app.model.official_odds_model import normalized_official_probabilities, payout_if_hit_2


OTHER_LABELS = {
    "home_other": "胜其它",
    "draw_other": "平其它",
    "away_other": "负其它",
}


def score_selection_for_sporttery(home_goals: int, away_goals: int, official_selections: set[str]) -> str:
    concrete = f"{home_goals}-{away_goals}"
    if concrete in official_selections:
        return concrete
    if home_goals > away_goals:
        return "home_other"
    if home_goals == away_goals:
        return "draw_other"
    return "away_other"


def team_score_probabilities_by_official_option(
    scores: list[ScoreProbability],
    quotes: list[OddsQuote],
) -> dict[str, float]:
    official_selections = {quote.selection for quote in quotes}
    grouped: dict[str, float] = defaultdict(float)
    for score in scores:
        selection = score_selection_for_sporttery(score.home_goals, score.away_goals, official_selections)
        grouped[selection] += score.probability
    return dict(grouped)


def score_outcome(selection: str) -> str | None:
    if selection == "home_other":
        return "home"
    if selection == "draw_other":
        return "draw"
    if selection == "away_other":
        return "away"
    if "-" not in selection:
        return None
    home, away = selection.split("-", 1)
    if not home.isdigit() or not away.isdigit():
        return None
    home_goals, away_goals = int(home), int(away)
    if home_goals > away_goals:
        return "home"
    if home_goals < away_goals:
        return "away"
    return "draw"


def score_total_goals(selection: str) -> int | None:
    if "-" not in selection:
        return None
    home, away = selection.split("-", 1)
    if not home.isdigit() or not away.isdigit():
        return None
    return int(home) + int(away)


def confidence_label(probability: float | None, support_count: int, conflict_count: int) -> str:
    if probability is None:
        return "低"
    if probability >= 0.12 and support_count >= 2 and conflict_count == 0:
        return "高"
    if probability >= 0.07 and support_count >= 1:
        return "中"
    return "低"


def consistency_items(
    selection: str,
    winner_probabilities: dict[str, float],
    handicap_probabilities: dict[str, float],
    total_goal_probabilities: dict[str, float],
    half_full_probabilities: dict[str, float],
) -> tuple[list[str], list[str]]:
    support: list[str] = []
    conflict: list[str] = []
    outcome = score_outcome(selection)
    total = score_total_goals(selection)

    if outcome and winner_probabilities:
        top_winner = max(winner_probabilities, key=winner_probabilities.get)
        if top_winner == outcome:
            support.append(f"胜平负支持{selection}")
        else:
            conflict.append(f"胜平负不支持{selection}")
    if outcome and handicap_probabilities:
        top_handicap = max(handicap_probabilities, key=handicap_probabilities.get)
        if top_handicap == outcome:
            support.append("让球方向支持")
        else:
            conflict.append("让球方向有分歧")
    if total is not None and total_goal_probabilities:
        top_total = max(total_goal_probabilities, key=total_goal_probabilities.get)
        total_key = str(total) if str(total) in total_goal_probabilities else "7+"
        if top_total == total_key:
            support.append("总进球支持")
        else:
            conflict.append(f"总进球更偏向{top_total}球")
    if outcome and half_full_probabilities:
        top_half_full = max(half_full_probabilities, key=half_full_probabilities.get)
        if top_half_full.endswith(outcome):
            support.append("半全场方向支持")
        else:
            conflict.append("半全场方向有分歧")
    return support, conflict


def capped_consistency_multiplier(support_count: int, conflict_count: int) -> float:
    raw = 1.0 + min(support_count * 0.04, 0.16) - min(conflict_count * 0.05, 0.20)
    return max(0.80, min(1.20, raw))


def quote_label(quote: OddsQuote | None, selection: str) -> str:
    if quote is not None:
        return quote.selection_label or quote.selection
    return OTHER_LABELS.get(selection, selection)


def build_score_candidates(
    quotes: list[OddsQuote],
    team_probabilities: dict[str, float],
    winner_probabilities: dict[str, float],
    handicap_probabilities: dict[str, float],
    total_goal_probabilities: dict[str, float],
    half_full_probabilities: dict[str, float],
    official_weight: float,
    team_weight: float,
) -> list[ScoreCandidate]:
    official_probabilities = normalized_official_probabilities(quotes)
    quote_by_selection = {quote.selection: quote for quote in quotes}
    selections = set(official_probabilities) | set(team_probabilities)
    rows = []
    for selection in selections:
        quote = quote_by_selection.get(selection)
        label = quote_label(quote, selection)
        official_probability = official_probabilities.get(selection)
        team_probability = team_probabilities.get(selection)
        base_probability = 0.0
        if official_probability is not None:
            base_probability += official_probability * official_weight
        if team_probability is not None:
            base_probability += team_probability * team_weight
        support, conflict = consistency_items(
            selection,
            winner_probabilities,
            handicap_probabilities,
            total_goal_probabilities,
            half_full_probabilities,
        )
        combined = max(0.0, min(1.0, base_probability * capped_consistency_multiplier(len(support), len(conflict))))
        rows.append(
            ScoreCandidate(
                selection=selection,
                label=label,
                official_option_label=label,
                official_probability=official_probability,
                team_probability=team_probability,
                combined_probability=combined,
                decimal_odds=quote.decimal_odds if quote else None,
                payout_if_hit_2=payout_if_hit_2(quote.decimal_odds) if quote else None,
                confidence_label=confidence_label(combined, len(support), len(conflict)),
                rank=1,
                support_items=support,
                conflict_items=conflict,
                reason=f"{label}综合参考概率为{combined:.1%}，{len(support)}项支持，{len(conflict)}项分歧。",
                grouped_scorelines=[],
            )
        )
    ordered = sorted(rows, key=lambda row: (row.combined_probability or 0.0), reverse=True)
    return [row.model_copy(update={"rank": index + 1}) for index, row in enumerate(ordered)]
