from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from app.data.providers import (
    AutoDataProvider,
    SampleDataProvider,
    SportteryDataProvider,
    TheOddsApiProvider,
    filter_matches_by_window,
    parse_odds_api_payload,
    parse_sporttery_payload,
)


SHANGHAI = ZoneInfo("Asia/Shanghai")


def sporttery_payload() -> dict:
    return {
        "errorCode": "0",
        "success": True,
        "value": {
            "lastUpdateTime": "2026-07-07 20:08:00",
            "matchInfoList": [
                {
                    "businessDate": "2026-07-07",
                    "subMatchList": [
                        {
                            "matchId": 2040427,
                            "leagueAllName": "世界杯",
                            "matchDate": "2026-07-08",
                            "matchTime": "00:00:00",
                            "matchStatus": "Selling",
                            "homeTeamAllName": "阿根廷",
                            "awayTeamAllName": "埃及",
                            "homeRank": "[世界杯1]",
                            "awayRank": "[世界杯2]",
                            "remark": "比赛将在美国-佐治亚州亚特兰大举行",
                            "had": {
                                "h": "1.20",
                                "d": "4.90",
                                "a": "11.00",
                                "hf": "1",
                                "df": "0",
                                "af": "-1",
                                "updateDate": "2026-07-07",
                                "updateTime": "20:07:51",
                            },
                            "hhad": {
                                "goalLine": "-1",
                                "h": "1.74",
                                "d": "3.70",
                                "a": "3.52",
                            },
                        },
                        {
                            "matchId": 2040000,
                            "leagueAllName": "世界杯",
                            "matchDate": "2026-07-07",
                            "matchTime": "10:00:00",
                            "matchStatus": "Selling",
                            "homeTeamAllName": "已过主队",
                            "awayTeamAllName": "已过客队",
                            "homeRank": "",
                            "awayRank": "",
                            "had": {"h": "2.00", "d": "3.00", "a": "3.50"},
                        },
                    ],
                }
            ],
        },
    }


def odds_api_payload() -> list[dict]:
    return [
        {
            "id": "event-1",
            "sport_title": "FIFA World Cup",
            "commence_time": "2026-07-08T00:00:00Z",
            "home_team": "Argentina",
            "away_team": "Egypt",
            "bookmakers": [
                {
                    "key": "bet365",
                    "title": "Bet365",
                    "last_update": "2026-07-07T20:01:00Z",
                    "markets": [
                        {
                            "key": "h2h",
                            "outcomes": [
                                {"name": "Argentina", "price": 1.22},
                                {"name": "Draw", "price": 5.00},
                                {"name": "Egypt", "price": 10.50},
                            ],
                        }
                    ],
                }
            ],
        }
    ]


def test_parse_sporttery_payload_builds_matches_and_live_odds_metadata():
    previous = {("sporttery-2040427", "winner", "home"): 1.18}

    matches = parse_sporttery_payload(sporttery_payload(), previous_odds=previous)

    assert len(matches) == 2
    match = next(match for match in matches if match.match_id == "sporttery-2040427")
    assert match.match_id == "sporttery-2040427"
    assert match.competition == "世界杯"
    assert match.kickoff_utc == "2026-07-07T16:00:00Z"
    assert match.home.name == "阿根廷"
    assert match.away.name == "埃及"
    assert "让球 -1" in match.context.notes

    odds_by_selection = {quote.selection: quote for quote in match.odds}
    assert odds_by_selection["home"].decimal_odds == 1.20
    assert odds_by_selection["home"].previous_decimal_odds == 1.18
    assert odds_by_selection["home"].movement == "up"
    assert odds_by_selection["draw"].movement == "flat"
    assert odds_by_selection["away"].movement == "down"
    assert odds_by_selection["home"].updated_at == "2026-07-07T12:07:51Z"


def test_filter_matches_by_window_keeps_only_upcoming_next_match_day():
    matches = parse_sporttery_payload(sporttery_payload())
    now = datetime(2026, 7, 7, 20, 30, tzinfo=SHANGHAI)

    filtered = filter_matches_by_window(matches, now=now, window="next")

    assert [match.match_id for match in filtered] == ["sporttery-2040427"]


def test_filter_matches_by_window_falls_back_to_next_when_tomorrow_is_empty():
    base = parse_sporttery_payload(sporttery_payload())[0]
    later = base.model_copy(update={"match_id": "sporttery-later", "kickoff_utc": "2026-07-09T16:00:00Z"})
    now = datetime(2026, 7, 7, 20, 30, tzinfo=SHANGHAI)

    filtered = filter_matches_by_window([later], now=now, window="tomorrow")

    assert [match.match_id for match in filtered] == ["sporttery-later"]


def test_sporttery_provider_uses_cached_live_data_when_refresh_fails():
    calls = {"count": 0}

    def fetch_json():
        calls["count"] += 1
        if calls["count"] == 1:
            return sporttery_payload()
        raise RuntimeError("network blocked")

    current = datetime(2026, 7, 7, 20, 30, tzinfo=SHANGHAI)

    def now():
        return current.astimezone(timezone.utc)

    provider = SportteryDataProvider(fetch_json=fetch_json, now=now, refresh_seconds=1)

    first = provider.list_matches()
    current = current + timedelta(seconds=2)
    second = provider.list_matches()

    assert [match.match_id for match in first] == ["sporttery-2040427"]
    assert [match.match_id for match in second] == ["sporttery-2040427"]
    assert provider.status().healthy is False
    assert provider.status().using_fallback is False
    assert "cached" in provider.status().message


def test_sporttery_provider_falls_back_to_sample_when_first_refresh_fails():
    def fetch_json():
        raise RuntimeError("waf")

    provider = SportteryDataProvider(fetch_json=fetch_json, fallback_provider=SampleDataProvider())

    matches = provider.list_matches(window="7d")

    assert matches
    assert provider.status().healthy is False
    assert provider.status().using_fallback is True


def test_parse_odds_api_payload_builds_matches_and_live_odds_metadata():
    previous = {("oddsapi-event-1", "winner", "home"): 1.20}

    matches = parse_odds_api_payload(odds_api_payload(), previous_odds=previous)

    assert len(matches) == 1
    match = matches[0]
    assert match.match_id == "oddsapi-event-1"
    assert match.competition == "FIFA World Cup"
    assert match.kickoff_utc == "2026-07-08T00:00:00Z"
    assert match.home.name == "Argentina"
    assert match.away.name == "Egypt"

    odds_by_selection = {quote.selection: quote for quote in match.odds}
    assert odds_by_selection["home"].decimal_odds == 1.22
    assert odds_by_selection["home"].previous_decimal_odds == 1.20
    assert odds_by_selection["home"].movement == "up"
    assert odds_by_selection["draw"].decimal_odds == 5.00
    assert odds_by_selection["away"].decimal_odds == 10.50
    assert odds_by_selection["home"].source == "the_odds_api:bet365"


def test_the_odds_api_provider_returns_live_matches_from_injected_fetcher():
    provider = TheOddsApiProvider(fetch_json=odds_api_payload, api_key="test-key")

    matches = provider.list_matches(window="7d")

    assert [match.match_id for match in matches] == ["oddsapi-event-1"]
    assert provider.status().healthy is True
    assert provider.status().using_fallback is False


def test_auto_provider_uses_odds_api_when_sporttery_is_blocked():
    def blocked_sporttery():
        raise RuntimeError("HTTP Error 567: Unknown Status")

    sporttery = SportteryDataProvider(fetch_json=blocked_sporttery, refresh_seconds=1)
    odds_api = TheOddsApiProvider(fetch_json=odds_api_payload, api_key="test-key", refresh_seconds=1)
    provider = AutoDataProvider(live_providers=[sporttery, odds_api], fallback_provider=SampleDataProvider())

    matches = provider.list_matches(window="7d")

    assert [match.match_id for match in matches] == ["oddsapi-event-1"]
    assert provider.status().source == "the_odds_api"
    assert provider.status().using_fallback is False
