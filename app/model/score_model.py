from math import exp, factorial

from app.domain import MarketProbability, MatchInput, ScoreProbability


def estimate_expected_goals(match: MatchInput) -> tuple[float, float]:
    base_home = 1.35
    base_away = 1.15
    venue_boost = 1.0 if match.neutral_venue else 1.08

    home_xg = base_home * match.home.attack_rating * match.away.defense_rating * venue_boost
    away_xg = base_away * match.away.attack_rating * match.home.defense_rating

    home_xg *= 1.0 - match.context.home_injury_impact
    away_xg *= 1.0 - match.context.away_injury_impact

    uncertainty_drag = 1.0 - (match.context.tactical_uncertainty * 0.04)
    return max(home_xg * uncertainty_drag, 0.05), max(away_xg * uncertainty_drag, 0.05)


def poisson_probability(goals: int, expected_goals: float) -> float:
    return (expected_goals**goals * exp(-expected_goals)) / factorial(goals)


def poisson_score_matrix(home_xg: float, away_xg: float, max_goals: int = 8) -> list[ScoreProbability]:
    raw: list[ScoreProbability] = []
    for home_goals in range(max_goals + 1):
        for away_goals in range(max_goals + 1):
            probability = poisson_probability(home_goals, home_xg) * poisson_probability(away_goals, away_xg)
            raw.append(ScoreProbability(home_goals=home_goals, away_goals=away_goals, probability=probability))

    total = sum(item.probability for item in raw)
    return [
        ScoreProbability(
            home_goals=item.home_goals,
            away_goals=item.away_goals,
            probability=item.probability / total,
        )
        for item in raw
    ]


def aggregate_score_matrix(matrix: list[ScoreProbability]) -> dict[str, list[MarketProbability]]:
    home = sum(item.probability for item in matrix if item.home_goals > item.away_goals)
    draw = sum(item.probability for item in matrix if item.home_goals == item.away_goals)
    away = sum(item.probability for item in matrix if item.home_goals < item.away_goals)

    total_goals: list[MarketProbability] = []
    for total in range(5):
        probability = sum(item.probability for item in matrix if item.home_goals + item.away_goals == total)
        total_goals.append(MarketProbability(market="total_goals", selection=str(total), probability=probability))
    total_goals.append(
        MarketProbability(
            market="total_goals",
            selection="5+",
            probability=sum(item.probability for item in matrix if item.home_goals + item.away_goals >= 5),
        )
    )

    over_under = []
    for line in (1.5, 2.5, 3.5):
        over = sum(item.probability for item in matrix if item.home_goals + item.away_goals > line)
        over_under.append(MarketProbability(market="over_under", selection=f"over_{line}", probability=over))
        over_under.append(MarketProbability(market="over_under", selection=f"under_{line}", probability=1.0 - over))

    return {
        "winner": [
            MarketProbability(market="winner", selection="home", probability=home),
            MarketProbability(market="winner", selection="draw", probability=draw),
            MarketProbability(market="winner", selection="away", probability=away),
        ],
        "total_goals": total_goals,
        "over_under": over_under,
    }


def half_time_probabilities(home_xg: float, away_xg: float) -> list[MarketProbability]:
    half_matrix = poisson_score_matrix(home_xg * 0.45, away_xg * 0.45, max_goals=5)
    return aggregate_score_matrix(half_matrix)["winner"]


def top_scorelines(matrix: list[ScoreProbability], limit: int = 10) -> list[ScoreProbability]:
    return sorted(matrix, key=lambda item: item.probability, reverse=True)[:limit]
