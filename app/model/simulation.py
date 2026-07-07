from collections import Counter
from math import isfinite
from numbers import Real

import numpy as np


TOTAL_GOAL_BUCKETS = ("0", "1", "2", "3", "4", "5+")


def validate_expected_goals(value: float, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, Real) or not isfinite(value) or value < 0:
        raise ValueError(f"{name} must be a finite non-negative real number")


def validate_positive_integer(value: int, name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")


def validate_seed(seed: int) -> None:
    if not isinstance(seed, int) or isinstance(seed, bool) or seed < 0:
        raise ValueError("seed must be a non-negative integer")


def run_simulation(
    home_xg: float,
    away_xg: float,
    trials: int = 10_000,
    seed: int = 42,
) -> dict[str, dict[str, float | int]]:
    validate_expected_goals(home_xg, "home_xg")
    validate_expected_goals(away_xg, "away_xg")
    validate_positive_integer(trials, "trials")
    validate_seed(seed)

    rng = np.random.default_rng(seed)
    home_goals = rng.poisson(home_xg, trials)
    away_goals = rng.poisson(away_xg, trials)

    winner_counts: Counter[str] = Counter({"home": 0, "draw": 0, "away": 0})
    score_counts: Counter[str] = Counter()
    total_counts: Counter[str] = Counter({bucket: 0 for bucket in TOTAL_GOAL_BUCKETS})

    for home, away in zip(home_goals, away_goals):
        if home > away:
            winner_counts["home"] += 1
        elif home == away:
            winner_counts["draw"] += 1
        else:
            winner_counts["away"] += 1

        score_key = f"{int(home)}-{int(away)}"
        total_key = "5+" if home + away >= 5 else str(int(home + away))
        score_counts[score_key] += 1
        total_counts[total_key] += 1

    def probabilities(counter: Counter[str]) -> dict[str, float]:
        return {key: value / trials for key, value in sorted(counter.items())}

    return {
        "winner": dict(winner_counts),
        "score": dict(score_counts),
        "total_goals": dict(total_counts),
        "winner_probability": probabilities(winner_counts),
        "score_probability": probabilities(score_counts),
        "total_goals_probability": probabilities(total_counts),
    }
