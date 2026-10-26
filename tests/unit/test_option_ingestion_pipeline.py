from datetime import datetime, timedelta, timezone

from nse_universe.history.sqlite_store import SQLiteOptionSnapshotStore
from nse_universe.ingestion.pipeline import OptionSnapshotIngestor
from nse_universe.options.models import OptionChainSnapshot, OptionContract


def snapshot(at, call_oi=100, put_oi=120, complete=True):
    return OptionChainSnapshot(
        underlying="NIFTY", spot_price=25000, observed_at=at, complete=complete,
        contracts=(
            OptionContract(25000, "CE", call_oi, at),
            OptionContract(25000, "PE", put_oi, at),
        ),
    )


def test_ingestion_persists_snapshot_and_builds_report_after_second_snapshot(tmp_path):
    now = datetime(2026, 10, 26, 10, 0, tzinfo=timezone.utc)
    store = SQLiteOptionSnapshotStore(tmp_path / "history.sqlite3")
    ingestor = OptionSnapshotIngestor(store, max_age_seconds=10, clock=lambda: now)
    first = ingestor.ingest(snapshot(now - timedelta(seconds=1)))
    second = ingestor.ingest(snapshot(now, 150, 180))

    assert first.stored
    assert first.trend_report is None
    assert second.trend_report is not None
    assert second.trend_report.call_oi_change == 50
    assert second.trend_report.put_oi_change == 60


def test_stale_and_incomplete_snapshots_are_flagged_but_retained(tmp_path):
    now = datetime(2026, 10, 26, 10, 0, tzinfo=timezone.utc)
    store = SQLiteOptionSnapshotStore(tmp_path / "history.sqlite3")
    ingestor = OptionSnapshotIngestor(store, max_age_seconds=5, clock=lambda: now)
    result = ingestor.ingest(snapshot(now - timedelta(seconds=30), complete=False))

    assert result.stored
    assert any("stale" in warning.lower() for warning in result.warnings)
    assert any("incomplete" in warning.lower() for warning in result.warnings)
    assert store.latest("NIFTY") is not None


def test_rejects_invalid_configuration(tmp_path):
    store = SQLiteOptionSnapshotStore(tmp_path / "history.sqlite3")
    try:
        OptionSnapshotIngestor(store, history_window=1)
    except ValueError as exc:
        assert "at least 2" in str(exc)
    else:
        raise AssertionError("expected ValueError")
