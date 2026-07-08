import pytest

from app.domain import OddsQuote
from app.model.official_odds_model import (
    best_return_reference,
    market_favorite,
    normalized_official_probabilities,
    official_model_line,
)


def q(market: str, selection: str, odds: float, label: str | None = None) -> OddsQuote:
    return OddsQuote(
        market=market,
        selection=selection,
        decimal_odds=odds,
        source="sporttery",
        selection_label=label or selection,
    )


def test_score_probabilities_include_other_options():
    quotes = [
        q("score", "1-0", 6.5, "1-0"),
        q("score", "2-0", 6.25, "2-0"),
        q("score", "home_other", 35.0, "胜其它"),
        q("score", "draw_other", 120.0, "平其它"),
        q("score", "away_other", 80.0, "负其它"),
    ]

    probabilities = normalized_official_probabilities(quotes)

    assert set(probabilities) == {"1-0", "2-0", "home_other", "draw_other", "away_other"}
    assert sum(probabilities.values()) == pytest.approx(1.0)
    assert probabilities["2-0"] > probabilities["home_other"]


def test_market_favorite_uses_normalized_probability_and_returns_two_yuan_payout():
    quotes = [
        q("winner", "home", 1.4, "主胜"),
        q("winner", "draw", 4.0, "平局"),
        q("winner", "away", 7.0, "客胜"),
    ]

    favorite = market_favorite("winner", quotes)

    assert favorite.selection == "home"
    assert favorite.selection_label == "主胜"
    assert favorite.payout_if_hit_2 == 2.8
    assert favorite.probability is not None


def test_best_return_reference_uses_reasonable_model_candidates():
    quotes = [q("score", "1-0", 6.0, "1-0"), q("score", "2-0", 8.0, "2-0"), q("score", "0-2", 60.0, "0-2")]
    model_probabilities = {"1-0": 0.12, "2-0": 0.10, "0-2": 0.01}

    reference = best_return_reference("score", quotes, model_probabilities)

    assert reference.selection == "2-0"
    assert reference.selection_label == "2-0"
    assert reference.payout_if_hit_2 == 16.0


def test_official_model_line_uses_plain_chinese_label():
    quotes = [q("total_goals", "2", 3.4, "2球"), q("total_goals", "3", 3.2, "3球")]

    line = official_model_line("total_goals", quotes)

    assert line.source == "official_odds"
    assert line.selection_label == "3球"
    assert "体彩更看好" in line.label
    assert line.payout_if_hit_2 == 6.4
