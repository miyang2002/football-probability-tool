from app.data.providers import SampleDataProvider
from app.data.repository import PredictionRepository


def test_sample_provider_returns_matches():
    provider = SampleDataProvider()

    matches = provider.list_matches()

    assert len(matches) >= 4
    assert matches[0].match_id
    assert matches[0].odds


def test_repository_saves_prediction_snapshot(tmp_path):
    db_path = tmp_path / "predictions.sqlite3"
    repo = PredictionRepository(str(db_path))

    snapshot_id = repo.save_snapshot("m1", {"winner": {"home": 0.5}})
    rows = repo.list_snapshots("m1")

    assert snapshot_id == 1
    assert rows[0]["match_id"] == "m1"
    assert rows[0]["payload"]["winner"]["home"] == 0.5
