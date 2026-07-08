from typing import Protocol

from app.domain import MatchInput, TeamInfoFact, TeamInfoSnapshot


class TeamInfoProvider(Protocol):
    def snapshot(self, match: MatchInput) -> TeamInfoSnapshot:
        ...


class MissingTeamInfoProvider:
    def snapshot(self, match: MatchInput) -> TeamInfoSnapshot:
        return TeamInfoSnapshot(
            match_id=match.match_id,
            facts=[
                TeamInfoFact(
                    category="recent_form",
                    team="match",
                    title="球队近况未抓到",
                    summary="当前没有可用的近5-10场球队资料。",
                    source_name="system",
                    confidence=0.0,
                    affects_model=False,
                ),
                TeamInfoFact(
                    category="injury",
                    team="match",
                    title="伤停信息缺失",
                    summary="当前没有可信伤停来源进入模型。",
                    source_name="system",
                    confidence=0.0,
                    affects_model=False,
                ),
                TeamInfoFact(
                    category="motivation",
                    team="match",
                    title="赛程战意缺失",
                    summary="当前没有可信赛程战意信息进入模型。",
                    source_name="system",
                    confidence=0.0,
                    affects_model=False,
                ),
            ],
            quality=0.0,
            missing_info=["球队近况未抓到", "伤停信息缺失", "赛程战意缺失"],
        )


def team_model_weight(snapshot: TeamInfoSnapshot) -> float:
    if snapshot.quality <= 0:
        return 0.0
    return max(0.10, min(0.45, snapshot.quality * 0.45))
