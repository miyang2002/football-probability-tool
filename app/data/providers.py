from app.data.sample_data import SAMPLE_MATCHES
from app.domain import MatchInput


class SampleDataProvider:
    def list_matches(self) -> list[MatchInput]:
        return SAMPLE_MATCHES

    def get_match(self, match_id: str) -> MatchInput | None:
        for match in SAMPLE_MATCHES:
            if match.match_id == match_id:
                return match
        return None
