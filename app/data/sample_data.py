from typing import Any

from app.domain import MatchInput


_SAMPLE_MATCH_FIXTURES: tuple[dict[str, Any], ...] = (
    {
        "match_id": "wc-001",
        "competition": "世界杯",
        "kickoff_utc": "2026-07-08T19:00:00Z",
        "home": {
            "name": "法国",
            "attack_rating": 1.25,
            "defense_rating": 0.88,
            "recent_goals_for": 1.8,
            "recent_goals_against": 0.9,
        },
        "away": {
            "name": "巴西",
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
            "notes": ["中立场淘汰赛，两队进攻能力都偏强。"],
        },
        "odds": [
            {"market": "winner", "selection": "home", "decimal_odds": 2.22},
            {"market": "winner", "selection": "draw", "decimal_odds": 3.20},
            {"market": "winner", "selection": "away", "decimal_odds": 3.10},
        ],
    },
    {
        "match_id": "wc-002",
        "competition": "世界杯",
        "kickoff_utc": "2026-07-09T19:00:00Z",
        "home": {
            "name": "阿根廷",
            "attack_rating": 1.28,
            "defense_rating": 0.90,
            "recent_goals_for": 2.0,
            "recent_goals_against": 0.8,
        },
        "away": {
            "name": "葡萄牙",
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
            "notes": ["阿根廷近期状态和机会创造略占优势。"],
        },
        "odds": [
            {"market": "winner", "selection": "home", "decimal_odds": 2.15},
            {"market": "winner", "selection": "draw", "decimal_odds": 3.25},
            {"market": "winner", "selection": "away", "decimal_odds": 3.75},
        ],
    },
    {
        "match_id": "wc-003",
        "competition": "世界杯",
        "kickoff_utc": "2026-07-10T19:00:00Z",
        "home": {
            "name": "西班牙",
            "attack_rating": 1.20,
            "defense_rating": 0.87,
            "recent_goals_for": 1.6,
            "recent_goals_against": 0.7,
        },
        "away": {
            "name": "荷兰",
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
            "notes": ["西班牙略占优势，防守波动相对更小。"],
        },
        "odds": [
            {"market": "winner", "selection": "home", "decimal_odds": 2.25},
            {"market": "winner", "selection": "draw", "decimal_odds": 3.10},
            {"market": "winner", "selection": "away", "decimal_odds": 3.65},
        ],
    },
    {
        "match_id": "wc-004",
        "competition": "世界杯",
        "kickoff_utc": "2026-07-11T19:00:00Z",
        "home": {
            "name": "英格兰",
            "attack_rating": 1.16,
            "defense_rating": 0.91,
            "recent_goals_for": 1.5,
            "recent_goals_against": 0.9,
        },
        "away": {
            "name": "德国",
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
            "notes": ["市场认为双方接近，德国进攻评价略接近。"],
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
