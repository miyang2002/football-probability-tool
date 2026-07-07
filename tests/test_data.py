from app.data.providers import SampleDataProvider
from app.data.repository import PredictionRepository
from app.domain import MarketProbability


def test_sample_provider_returns_matches():
    provider = SampleDataProvider()

    matches = provider.list_matches()

    assert len(matches) >= 4
    assert matches[0].match_id
    assert matches[0].odds


def test_sample_provider_returns_deep_copies():
    provider = SampleDataProvider()
    first = provider.list_matches()[0]
    first.context.notes.append("mutated")
    first.odds.clear()

    refetched = provider.get_match(first.match_id)

    assert refetched is not None
    assert "mutated" not in refetched.context.notes
    assert refetched.odds


def test_repository_saves_prediction_snapshot(tmp_path):
    db_path = tmp_path / "predictions.sqlite3"
    repo = PredictionRepository(str(db_path))

    snapshot_id = repo.save_snapshot("m1", {"winner": {"home": 0.5}})
    rows = repo.list_snapshots("m1")

    assert snapshot_id == 1
    assert rows[0]["match_id"] == "m1"
    assert rows[0]["payload"]["winner"]["home"] == 0.5


def test_repository_creates_nested_parent_and_reopens_database(tmp_path):
    db_path = tmp_path / "nested" / "path" / "predictions.sqlite3"
    repo = PredictionRepository(str(db_path))
    repo.save_snapshot("m1", {"first": True})

    reopened = PredictionRepository(str(db_path))
    rows = reopened.list_snapshots("m1")

    assert db_path.exists()
    assert rows[0]["payload"] == {"first": True}


def test_repository_filters_and_orders_snapshots_newest_first(tmp_path):
    db_path = tmp_path / "predictions.sqlite3"
    repo = PredictionRepository(str(db_path))

    first_id = repo.save_snapshot("m1", {"version": 1})
    repo.save_snapshot("m2", {"version": 99})
    second_id = repo.save_snapshot("m1", {"version": 2})

    rows = repo.list_snapshots("m1")

    assert [row["id"] for row in rows] == [second_id, first_id]
    assert [row["payload"]["version"] for row in rows] == [2, 1]


def test_repository_serializes_pydantic_payloads(tmp_path):
    db_path = tmp_path / "predictions.sqlite3"
    repo = PredictionRepository(str(db_path))

    repo.save_snapshot("m1", {"winner": MarketProbability(market="winner", selection="home", probability=0.55)})
    rows = repo.list_snapshots("m1")

    assert rows[0]["payload"]["winner"]["probability"] == 0.55
