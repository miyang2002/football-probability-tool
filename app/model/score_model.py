from math import exp, isfinite, lgamma, log

from app.domain import MarketProbability, MatchInput, ScoreProbability


PROBABILITY_EPSILON = 1e-12


def bounded_probability(probability: float) -> float:
    if not isfinite(probability):
        raise ValueError("probability must be finite")
    if probability < -PROBABILITY_EPSILON or probability > 1.0 + PROBABILITY_EPSILON:
        raise ValueError("probability must be between 0 and 1")
    return min(1.0, max(0.0, probability))


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
    if goals < 0:
        raise ValueError("goals must be non-negative")
    if expected_goals == 0:
        return 1.0 if goals == 0 else 0.0
    return exp((goals * log(expected_goals)) - expected_goals - lgamma(goals + 1))


def poisson_score_matrix(home_xg: float, away_xg: float, max_goals: int = 8) -> list[ScoreProbability]:
    if not isfinite(home_xg) or not isfinite(away_xg) or home_xg < 0 or away_xg < 0:
        raise ValueError("expected goals must be finite and non-negative")
    if not isinstance(max_goals, int) or isinstance(max_goals, bool) or max_goals <= 0:
        raise ValueError("max_goals must be a positive integer")

    raw: list[tuple[int, int, float]] = []
    for home_goals in range(max_goals + 1):
        for away_goals in range(max_goals + 1):
            probability = poisson_probability(home_goals, home_xg) * poisson_probability(away_goals, away_xg)
            raw.append((home_goals, away_goals, probability))

    total = sum(probability for _, _, probability in raw)
    if not isfinite(total) or total <= 0:
        raise ValueError("score matrix has no finite probability mass")
    return [
        ScoreProbability(
            home_goals=home_goals,
            away_goals=away_goals,
            probability=bounded_probability(probability / total),
        )
        for home_goals, away_goals, probability in raw
    ]


def aggregate_score_matrix(matrix: list[ScoreProbability]) -> dict[str, list[MarketProbability]]:
    home = sum(item.probability for item in matrix if item.home_goals > item.away_goals)
    draw = sum(item.probability for item in matrix if item.home_goals == item.away_goals)
    away = sum(item.probability for item in matrix if item.home_goals < item.away_goals)

    total_goals: list[MarketProbability] = []
    for total in range(5):
        probability = sum(item.probability for item in matrix if item.home_goals + item.away_goals == total)
        total_goals.append(
            MarketProbability(market="total_goals", selection=str(total), probability=bounded_probability(probability))
        )
    total_goals.append(
        MarketProbability(
            market="total_goals",
            selection="5+",
            probability=bounded_probability(
                sum(item.probability for item in matrix if item.home_goals + item.away_goals >= 5)
            ),
        )
    )

    over_under = []
    for line in (1.5, 2.5, 3.5):
        over = sum(item.probability for item in matrix if item.home_goals + item.away_goals > line)
        over_under.append(
            MarketProbability(market="over_under", selection=f"over_{line}", probability=bounded_probability(over))
        )
        over_under.append(
            MarketProbability(
                market="over_under",
                selection=f"under_{line}",
                probability=bounded_probability(1.0 - bounded_probability(over)),
            )
        )

    return {
        "winner": [
            MarketProbability(market="winner", selection="home", probability=bounded_probability(home)),
            MarketProbability(market="winner", selection="draw", probability=bounded_probability(draw)),
            MarketProbability(market="winner", selection="away", probability=bounded_probability(away)),
        ],
        "total_goals": total_goals,
        "over_under": over_under,
    }


def half_time_probabilities(home_xg: float, away_xg: float) -> list[MarketProbability]:
    half_matrix = poisson_score_matrix(home_xg * 0.45, away_xg * 0.45, max_goals=5)
    return aggregate_score_matrix(half_matrix)["winner"]


def top_scorelines(matrix: list[ScoreProbability], limit: int = 10) -> list[ScoreProbability]:
    return sorted(matrix, key=lambda item: item.probability, reverse=True)[:limit]
