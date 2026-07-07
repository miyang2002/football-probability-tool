from app.domain import MatchContext, MatchInput, OddsQuote, TeamInput


def test_match_input_accepts_core_fields():
    match = MatchInput(
        match_id="m1",
        competition="World Cup",
        kickoff_utc="2026-07-08T19:00:00Z",
        home=TeamInput(name="France", attack_rating=1.25, defense_rating=0.88),
        away=TeamInput(name="Brazil", attack_rating=1.18, defense_rating=0.93),
        neutral_venue=True,
        context=MatchContext(home_injury_impact=0.08, away_injury_impact=0.03, data_quality=0.82),
        odds=[
            OddsQuote(market="winner", selection="home", decimal_odds=2.15),
            OddsQuote(market="winner", selection="draw", decimal_odds=3.20),
            OddsQuote(market="winner", selection="away", decimal_odds=3.40),
        ],
    )

    assert match.home.name == "France"
    assert match.context.data_quality == 0.82
    assert match.odds[0].decimal_odds == 2.15


def test_context_defaults_are_conservative():
    context = MatchContext()

    assert context.home_injury_impact == 0.0
    assert context.away_injury_impact == 0.0
    assert context.lineup_uncertainty == 0.2
    assert context.data_quality == 0.7
