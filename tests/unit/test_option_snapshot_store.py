from datetime import datetime, timedelta, timezone

from nse_universe.history.sqlite_store import SQLiteOptionSnapshotStore
from nse_universe.options.models import OptionChainSnapshot, OptionContract


def make_snapshot(at, call_oi=100, put_oi=120):
    return OptionChainSnapshot(
        underlying="NIFTY", spot_price=25000, observed_at=at,
        complete=True,
        contracts=(
            OptionContract(25000, "CE", call_oi, at, last_price=100.5),
            OptionContract(25000, "PE", put_oi, at, last_price=101.5),
        ),
    )


def test_round_trip_and_chronological_recent_snapshots(tmp_path):
    store = SQLiteOptionSnapshotStore(tmp_path / "history.sqlite3")
    start = datetime(2026, 10, 26, 9, 15, tzinfo=timezone.utc)
    store.save(make_snapshot(start))
    store.save(make_snapshot(start + timedelta(minutes=1), 130, 140))

    recent = store.recent("NIFTY", limit=10)
    assert len(recent) == 2
    assert recent[0].contracts[0].open_interest == 100
    assert recent[1].contracts[0].open_interest == 130
    assert store.latest("NIFTY").spot_price == 25000


def test_save_same_timestamp_replaces_snapshot_without_duplicate(tmp_path):
    store = SQLiteOptionSnapshotStore(tmp_path / "history.sqlite3")
    at = datetime(2026, 10, 26, 9, 15, tzinfo=timezone.utc)
    first_id = store.save(make_snapshot(at, 100, 120))
    second_id = store.save(make_snapshot(at, 150, 170))
    assert first_id == second_id
    assert len(store.recent("NIFTY")) == 1
    assert store.latest("NIFTY").contracts[0].open_interest == 150


def test_recent_rejects_invalid_limit(tmp_path):
    store = SQLiteOptionSnapshotStore(tmp_path / "history.sqlite3")
    try:
        store.recent("NIFTY", limit=0)
    except ValueError as exc:
        assert "positive integer" in str(exc)
    else:
        raise AssertionError("expected ValueError")
