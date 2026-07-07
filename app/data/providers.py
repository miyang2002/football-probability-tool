from app.data.sample_data import build_sample_matches
from app.domain import MatchInput


class SampleDataProvider:
    def list_matches(self) -> list[MatchInput]:
        return build_sample_matches()

    def get_match(self, match_id: str) -> MatchInput | None:
        for match in build_sample_matches():
            if match.match_id == match_id:
                return match
        return None
