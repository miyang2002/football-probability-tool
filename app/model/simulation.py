from collections import Counter
from math import isfinite

import numpy as np


def run_simulation(
    home_xg: float,
    away_xg: float,
    trials: int = 10_000,
    seed: int = 42,
) -> dict[str, dict[str, float | int]]:
    if not isfinite(home_xg) or not isfinite(away_xg) or home_xg < 0 or away_xg < 0:
        raise ValueError("expected goals must be finite and non-negative")
    if not isinstance(trials, int) or isinstance(trials, bool) or trials <= 0:
        raise ValueError("trials must be a positive integer")

    rng = np.random.default_rng(seed)
    home_goals = rng.poisson(home_xg, trials)
    away_goals = rng.poisson(away_xg, trials)

    winner_counts: Counter[str] = Counter({"home": 0, "draw": 0, "away": 0})
    score_counts: Counter[str] = Counter()
    total_counts: Counter[str] = Counter()

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
