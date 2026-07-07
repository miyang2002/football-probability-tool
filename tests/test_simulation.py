import pytest

from app.model.simulation import run_simulation


def test_simulation_is_seeded_and_counts_trials():
    result_a = run_simulation(1.4, 1.1, trials=1000, seed=7)
    result_b = run_simulation(1.4, 1.1, trials=1000, seed=7)

    assert result_a == result_b
    assert sum(result_a["winner"].values()) == 1000
    assert sum(result_a["total_goals"].values()) == 1000


def test_simulation_returns_probability_maps():
    result = run_simulation(1.4, 1.1, trials=1000, seed=3)

    assert set(result["winner_probability"]) == {"home", "draw", "away"}
    assert round(sum(result["winner_probability"].values()), 6) == 1.0
    assert "1-1" in result["score_probability"]


def test_simulation_returns_stable_total_goal_buckets():
    result = run_simulation(0.0, 0.0, trials=3, seed=3)

    assert set(result["total_goals"]) == {"0", "1", "2", "3", "4", "5+"}
    assert set(result["total_goals_probability"]) == {"0", "1", "2", "3", "4", "5+"}
    assert result["total_goals"]["0"] == 3
    assert result["total_goals_probability"]["0"] == 1.0


@pytest.mark.parametrize(
    ("home_xg", "away_xg"),
    [
        (-0.01, 1.1),
        (1.4, -0.01),
        (float("nan"), 1.1),
        (1.4, float("inf")),
        (True, 1.1),
        ("1.4", 1.1),
    ],
)
def test_simulation_rejects_invalid_expected_goals(home_xg, away_xg):
    with pytest.raises(ValueError):
        run_simulation(home_xg, away_xg, trials=1000, seed=3)


@pytest.mark.parametrize("trials", [0, -1, 1.5, True])
def test_simulation_rejects_invalid_trials(trials):
    with pytest.raises(ValueError):
        run_simulation(1.4, 1.1, trials=trials, seed=3)


@pytest.mark.parametrize("seed", [-1, 1.5, True, "3"])
def test_simulation_rejects_invalid_seed(seed):
    with pytest.raises(ValueError):
        run_simulation(1.4, 1.1, trials=1000, seed=seed)
