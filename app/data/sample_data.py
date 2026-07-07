from typing import Any

from app.domain import MatchInput


_SAMPLE_MATCH_FIXTURES: tuple[dict[str, Any], ...] = (
    {
        "match_id": "wc-001",
        "competition": "World Cup",
        "kickoff_utc": "2026-07-08T19:00:00Z",
        "home": {
            "name": "France",
            "attack_rating": 1.25,
            "defense_rating": 0.88,
            "recent_goals_for": 1.8,
            "recent_goals_against": 0.9,
        },
        "away": {
            "name": "Brazil",
            "attack_rating": 1.22,
            "defense_rating": 0.92,
            "recent_goals_for": 1.9,
            "recent_goals_against": 1.0,
        },
        "neutral_venue": True,
        "context": {
            "home_injury_impact": 0.06,
            "away_injury_impact": 0.04,
            "lineup_uncertainty": 0.18,
            "tactical_uncertainty": 0.20,
            "data_quality": 0.86,
            "notes": ["Neutral-site knockout fixture with strong attacking profiles."],
        },
        "odds": [
            {"market": "winner", "selection": "home", "decimal_odds": 2.22},
            {"market": "winner", "selection": "draw", "decimal_odds": 3.20},
            {"market": "winner", "selection": "away", "decimal_odds": 3.10},
        ],
    },
    {
        "match_id": "wc-002",
        "competition": "World Cup",
        "kickoff_utc": "2026-07-09T19:00:00Z",
        "home": {
            "name": "Argentina",
            "attack_rating": 1.28,
            "defense_rating": 0.90,
            "recent_goals_for": 2.0,
            "recent_goals_against": 0.8,
        },
        "away": {
            "name": "Portugal",
            "attack_rating": 1.18,
            "defense_rating": 0.96,
            "recent_goals_for": 1.7,
            "recent_goals_against": 1.1,
        },
        "neutral_venue": True,
        "context": {
            "home_injury_impact": 0.03,
            "away_injury_impact": 0.07,
            "lineup_uncertainty": 0.16,
            "tactical_uncertainty": 0.22,
            "data_quality": 0.88,
            "notes": ["Argentina rate slightly higher on form and chance creation."],
        },
        "odds": [
            {"market": "winner", "selection": "home", "decimal_odds": 2.15},
            {"market": "winner", "selection": "draw", "decimal_odds": 3.25},
            {"market": "winner", "selection": "away", "decimal_odds": 3.75},
        ],
    },
    {
        "match_id": "wc-003",
        "competition": "World Cup",
        "kickoff_utc": "2026-07-10T19:00:00Z",
        "home": {
            "name": "Spain",
            "attack_rating": 1.20,
            "defense_rating": 0.87,
            "recent_goals_for": 1.6,
            "recent_goals_against": 0.7,
        },
        "away": {
            "name": "Netherlands",
            "attack_rating": 1.15,
            "defense_rating": 0.95,
            "recent_goals_for": 1.8,
            "recent_goals_against": 1.0,
        },
        "neutral_venue": True,
        "context": {
            "home_injury_impact": 0.04,
            "away_injury_impact": 0.05,
            "lineup_uncertainty": 0.20,
            "tactical_uncertainty": 0.24,
            "data_quality": 0.84,
            "notes": ["Spain project as a narrow favorite with lower defensive risk."],
        },
        "odds": [
            {"market": "winner", "selection": "home", "decimal_odds": 2.25},
            {"market": "winner", "selection": "draw", "decimal_odds": 3.10},
            {"market": "winner", "selection": "away", "decimal_odds": 3.65},
        ],
    },
    {
        "match_id": "wc-004",
        "competition": "World Cup",
        "kickoff_utc": "2026-07-11T19:00:00Z",
        "home": {
            "name": "England",
            "attack_rating": 1.16,
            "defense_rating": 0.91,
            "recent_goals_for": 1.5,
            "recent_goals_against": 0.9,
        },
        "away": {
            "name": "Germany",
            "attack_rating": 1.19,
            "defense_rating": 0.94,
            "recent_goals_for": 1.7,
            "recent_goals_against": 1.1,
        },
        "neutral_venue": True,
        "context": {
            "home_injury_impact": 0.05,
            "away_injury_impact": 0.04,
            "lineup_uncertainty": 0.19,
            "tactical_uncertainty": 0.23,
            "data_quality": 0.85,
            "notes": ["Market prices a balanced fixture with Germany close on attack."],
        },
        "odds": [
            {"market": "winner", "selection": "home", "decimal_odds": 2.35},
            {"market": "winner", "selection": "draw", "decimal_odds": 3.15},
            {"market": "winner", "selection": "away", "decimal_odds": 3.00},
        ],
    },
)


def build_sample_matches() -> list[MatchInput]:
    return [MatchInput.model_validate(fixture) for fixture in _SAMPLE_MATCH_FIXTURES]
