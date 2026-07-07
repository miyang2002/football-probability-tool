import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Protocol
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from app.data.sample_data import build_sample_matches
from app.domain import MatchContext, MatchInput, OddsMovement, OddsQuote, SourceStatus, TeamInput


SPORTTERY_ENDPOINT = (
    "https://webapi.sporttery.cn/gateway/uniform/football/getMatchCalculatorV1.qry"
    "?channel=c&poolCode=had,hhad"
)
SPORTTERY_REFERER = "https://www.sporttery.cn/jc/jsq/zqspf/"
SHANGHAI = ZoneInfo("Asia/Shanghai")
MatchWindow = str
FetchJson = Callable[[], dict[str, Any]]
Now = Callable[[], datetime]


class MatchProvider(Protocol):
    def list_matches(self, window: MatchWindow = "next") -> list[MatchInput]:
        ...

    def get_match(self, match_id: str) -> MatchInput | None:
        ...

    def status(self) -> SourceStatus:
        ...


class SampleDataProvider:
    def list_matches(self, window: MatchWindow = "next") -> list[MatchInput]:
        return build_sample_matches()

    def get_match(self, match_id: str) -> MatchInput | None:
        for match in build_sample_matches():
            if match.match_id == match_id:
                return match
        return None

    def status(self) -> SourceStatus:
        return SourceStatus(
            source="sample",
            healthy=True,
            using_fallback=False,
            refresh_seconds=30,
            message="Using deterministic sample data.",
        )


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def to_utc_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_utc_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def parse_local_datetime(date_value: str | None, time_value: str | None) -> datetime | None:
    if not date_value:
        return None
    raw_time = time_value or "00:00:00"
    try:
        return datetime.fromisoformat(f"{date_value}T{raw_time}").replace(tzinfo=SHANGHAI)
    except ValueError:
        return None


def parse_decimal(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number <= 1:
        return None
    return number


def movement_from_flag(flag: Any) -> OddsMovement:
    if str(flag) == "1":
        return "up"
    if str(flag) == "-1":
        return "down"
    return "flat"


def movement_from_previous(current: float, previous: float | None, fallback: OddsMovement) -> OddsMovement:
    if previous is None:
        return fallback
    if current > previous:
        return "up"
    if current < previous:
        return "down"
    return "flat"


def odds_updated_at(had: dict[str, Any]) -> str | None:
    local_dt = parse_local_datetime(had.get("updateDate"), had.get("updateTime"))
    return to_utc_iso(local_dt) if local_dt else None


def team_rating_from_odds(own_odds: float | None, opponent_odds: float | None) -> tuple[float, float]:
    if own_odds is None or opponent_odds is None:
        return 1.0, 1.0
    edge = max(min((opponent_odds - own_odds) / max(opponent_odds, own_odds), 0.25), -0.25)
    attack = max(0.82, min(1.28, 1.0 + edge * 0.9))
    defense = max(0.86, min(1.18, 1.0 - edge * 0.45))
    return attack, defense


def build_winner_odds(
    match_id: str,
    had: dict[str, Any],
    previous_odds: dict[tuple[str, str, str], float],
) -> list[OddsQuote]:
    mapping = {"home": ("h", "hf"), "draw": ("d", "df"), "away": ("a", "af")}
    updated = odds_updated_at(had)
    quotes: list[OddsQuote] = []

    for selection, (value_key, flag_key) in mapping.items():
        decimal_odds = parse_decimal(had.get(value_key))
        if decimal_odds is None:
            continue
        previous = previous_odds.get((match_id, "winner", selection))
        fallback_movement = movement_from_flag(had.get(flag_key))
        quotes.append(
            OddsQuote(
                market="winner",
                selection=selection,
                decimal_odds=decimal_odds,
                source="sporttery",
                updated_at=updated,
                previous_decimal_odds=previous,
                movement=movement_from_previous(decimal_odds, previous, fallback_movement),
            )
        )

    return quotes


def extract_sub_matches(payload: dict[str, Any]) -> list[dict[str, Any]]:
    value = payload.get("value") or {}
    match_groups = value.get("matchInfoList") or []
    sub_matches: list[dict[str, Any]] = []
    for group in match_groups:
        sub_matches.extend(group.get("subMatchList") or [])
    return sub_matches


def parse_sporttery_payload(
    payload: dict[str, Any],
    previous_odds: dict[tuple[str, str, str], float] | None = None,
) -> list[MatchInput]:
    if str(payload.get("errorCode")) != "0":
        raise ValueError(f"Sporttery response error: {payload.get('errorMessage') or payload.get('errorCode')}")

    previous = previous_odds or {}
    matches: list[MatchInput] = []
    for item in extract_sub_matches(payload):
        local_kickoff = parse_local_datetime(item.get("matchDate"), item.get("matchTime"))
        if local_kickoff is None:
            continue

        match_id = f"sporttery-{item.get('matchId')}"
        had = item.get("had") or {}
        hhad = item.get("hhad") or {}
        odds = build_winner_odds(match_id, had, previous)
        home_odds = next((quote.decimal_odds for quote in odds if quote.selection == "home"), None)
        away_odds = next((quote.decimal_odds for quote in odds if quote.selection == "away"), None)
        home_attack, home_defense = team_rating_from_odds(home_odds, away_odds)
        away_attack, away_defense = team_rating_from_odds(away_odds, home_odds)

        notes = ["来源：中国体育彩票竞彩。"]
        if item.get("remark"):
            notes.append(str(item["remark"]))
        if hhad.get("goalLine") not in (None, ""):
            notes.append(f"让球 {hhad['goalLine']}")
        if odds and odds[0].updated_at:
            notes.append(f"赔率更新时间 {odds[0].updated_at}")

        matches.append(
            MatchInput(
                match_id=match_id,
                competition=str(item.get("leagueAllName") or item.get("leagueAbbName") or "竞彩足球"),
                kickoff_utc=to_utc_iso(local_kickoff),
                home=TeamInput(
                    name=str(item.get("homeTeamAllName") or item.get("homeTeamAbbName") or "主队"),
                    attack_rating=home_attack,
                    defense_rating=home_defense,
                ),
                away=TeamInput(
                    name=str(item.get("awayTeamAllName") or item.get("awayTeamAbbName") or "客队"),
                    attack_rating=away_attack,
                    defense_rating=away_defense,
                ),
                neutral_venue=True,
                context=MatchContext(
                    lineup_uncertainty=0.25,
                    tactical_uncertainty=0.25,
                    data_quality=0.78 if odds else 0.58,
                    notes=notes,
                ),
                odds=odds,
            )
        )

    return sorted(matches, key=lambda match: parse_utc_iso(match.kickoff_utc))


def filter_matches_by_window(
    matches: list[MatchInput],
    now: datetime | None = None,
    window: MatchWindow = "next",
) -> list[MatchInput]:
    current = (now or utc_now()).astimezone(timezone.utc)
    upcoming = sorted(
        [match for match in matches if parse_utc_iso(match.kickoff_utc) > current],
        key=lambda match: parse_utc_iso(match.kickoff_utc),
    )
    if not upcoming:
        return []

    local_now = current.astimezone(SHANGHAI)
    if window == "3d":
        end = current + timedelta(days=3)
        return [match for match in upcoming if parse_utc_iso(match.kickoff_utc) <= end]
    if window == "7d":
        end = current + timedelta(days=7)
        return [match for match in upcoming if parse_utc_iso(match.kickoff_utc) <= end]
    if window == "tomorrow":
        target = local_now.date() + timedelta(days=1)
        tomorrow = [match for match in upcoming if parse_utc_iso(match.kickoff_utc).astimezone(SHANGHAI).date() == target]
        if tomorrow:
            return tomorrow

    next_date = parse_utc_iso(upcoming[0].kickoff_utc).astimezone(SHANGHAI).date()
    return [match for match in upcoming if parse_utc_iso(match.kickoff_utc).astimezone(SHANGHAI).date() == next_date]


class SportteryDataProvider:
    def __init__(
        self,
        fetch_json: FetchJson | None = None,
        now: Now = utc_now,
        refresh_seconds: int = 30,
        fallback_provider: MatchProvider | None = None,
    ) -> None:
        self._fetch_json = fetch_json or self._fetch_from_endpoint
        self._now = now
        self._refresh_seconds = max(refresh_seconds, 1)
        self._fallback_provider = fallback_provider or SampleDataProvider()
        self._cache: list[MatchInput] = []
        self._last_attempt_at: datetime | None = None
        self._last_success_at: datetime | None = None
        self._last_refresh_at: datetime | None = None
        self._last_error: str | None = None
        self._using_fallback = False
        self._previous_odds: dict[tuple[str, str, str], float] = {}

    def list_matches(self, window: MatchWindow = "next") -> list[MatchInput]:
        self._refresh_if_needed()
        if self._cache:
            self._using_fallback = False
            return filter_matches_by_window(self._cache, now=self._now(), window=window)

        self._using_fallback = True
        return self._fallback_provider.list_matches(window)

    def get_match(self, match_id: str) -> MatchInput | None:
        self._refresh_if_needed()
        for match in self._cache:
            if match.match_id == match_id:
                return match
        if not self._cache:
            return self._fallback_provider.get_match(match_id)
        return None

    def status(self) -> SourceStatus:
        healthy = self._last_error is None
        if healthy and self._last_success_at is not None:
            message = "Live Sporttery data loaded."
        elif self._cache:
            message = f"Live refresh failed; using cached data: {self._last_error}"
        elif self._using_fallback:
            message = f"Live refresh failed; using sample fallback: {self._last_error}"
        else:
            message = "Live data has not been requested yet."

        return SourceStatus(
            source="sporttery",
            healthy=healthy,
            using_fallback=self._using_fallback,
            last_attempt_at=to_utc_iso(self._last_attempt_at) if self._last_attempt_at else None,
            last_success_at=to_utc_iso(self._last_success_at) if self._last_success_at else None,
            refresh_seconds=self._refresh_seconds,
            message=message,
        )

    def _refresh_if_needed(self) -> None:
        now = self._now().astimezone(timezone.utc)
        if self._last_refresh_at and (now - self._last_refresh_at).total_seconds() < self._refresh_seconds:
            return

        self._last_attempt_at = now
        try:
            payload = self._fetch_json()
            matches = parse_sporttery_payload(payload, previous_odds=self._previous_odds)
            self._cache = matches
            self._previous_odds = {
                (match.match_id, quote.market, quote.selection): quote.decimal_odds
                for match in matches
                for quote in match.odds
            }
            self._last_error = None
            self._last_success_at = now
            self._last_refresh_at = now
            self._using_fallback = False
        except Exception as exc:  # pragma: no cover - exercised through injected fetchers.
            self._last_error = str(exc)
            self._last_refresh_at = now

    def _fetch_from_endpoint(self) -> dict[str, Any]:
        request = Request(
            os.getenv("SPORTTERY_ENDPOINT", SPORTTERY_ENDPOINT),
            headers={
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Referer": SPORTTERY_REFERER,
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
                ),
            },
        )
        with urlopen(request, timeout=15) as response:
            body = response.read().decode("utf-8")
        return json.loads(body)


def build_provider() -> MatchProvider:
    provider = os.getenv("FOOTBALL_DATA_PROVIDER", "sample").lower()
    if provider == "sporttery":
        refresh_seconds = int(os.getenv("SPORTTERY_REFRESH_SECONDS", "30"))
        return SportteryDataProvider(refresh_seconds=refresh_seconds)
    return SampleDataProvider()
