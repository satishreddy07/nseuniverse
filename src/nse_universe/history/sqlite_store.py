"""Small, dependency-free SQLite store for option-chain snapshot history."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from nse_universe.options.models import OptionChainSnapshot, OptionContract
from nse_universe.validation.market_data import to_utc


class SQLiteOptionSnapshotStore:
    """Persist normalized snapshots for repeatable intraday OI comparisons.

    A snapshot is identified by (underlying, observed_at in UTC). Re-inserting
    the same key replaces its contracts atomically, which makes ingestion retries safe.
    """

    def __init__(self, database: str | Path = "data/option_history.sqlite3") -> None:
        self.database = str(database)
        if self.database != ":memory:":
            Path(self.database).parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS option_snapshots (
                    id INTEGER PRIMARY KEY,
                    underlying TEXT NOT NULL,
                    observed_at TEXT NOT NULL,
                    spot_price REAL NOT NULL,
                    complete INTEGER NOT NULL,
                    UNIQUE (underlying, observed_at)
                )
            """)
            db.execute("""
                CREATE TABLE IF NOT EXISTS option_contracts (
                    snapshot_id INTEGER NOT NULL REFERENCES option_snapshots(id) ON DELETE CASCADE,
                    strike REAL NOT NULL,
                    option_type TEXT NOT NULL CHECK (option_type IN ('CE', 'PE')),
                    open_interest INTEGER NOT NULL,
                    change_in_oi INTEGER,
                    volume INTEGER,
                    last_price REAL,
                    instrument TEXT,
                    contract_observed_at TEXT NOT NULL,
                    PRIMARY KEY (snapshot_id, strike, option_type)
                )
            """)
            db.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_underlying_time "
                       "ON option_snapshots(underlying, observed_at DESC)")
            db.execute("PRAGMA foreign_keys = ON")

    def save(self, snapshot: OptionChainSnapshot) -> int:
        """Insert or replace a snapshot and return its database id."""
        timestamp = _iso_utc(snapshot.observed_at)
        with self._connect() as db:
            db.execute("PRAGMA foreign_keys = ON")
            db.execute("""
                INSERT INTO option_snapshots (underlying, observed_at, spot_price, complete)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(underlying, observed_at) DO UPDATE SET
                    spot_price=excluded.spot_price, complete=excluded.complete
            """, (snapshot.underlying, timestamp, snapshot.spot_price, int(snapshot.complete)))
            row = db.execute(
                "SELECT id FROM option_snapshots WHERE underlying=? AND observed_at=?",
                (snapshot.underlying, timestamp),
            ).fetchone()
            snapshot_id = int(row["id"])
            db.execute("DELETE FROM option_contracts WHERE snapshot_id=?", (snapshot_id,))
            db.executemany("""
                INSERT INTO option_contracts
                (snapshot_id, strike, option_type, open_interest, change_in_oi, volume,
                 last_price, instrument, contract_observed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                (snapshot_id, c.strike, c.option_type, c.open_interest, c.change_in_oi,
                 c.volume, c.last_price, c.instrument, _iso_utc(c.observed_at))
                for c in snapshot.contracts
            ])
            return snapshot_id

    def get(self, snapshot_id: int) -> OptionChainSnapshot | None:
        with self._connect() as db:
            row = db.execute("SELECT * FROM option_snapshots WHERE id=?", (snapshot_id,)).fetchone()
            if row is None:
                return None
            contracts = db.execute(
                "SELECT * FROM option_contracts WHERE snapshot_id=? ORDER BY strike, option_type",
                (snapshot_id,),
            ).fetchall()
        return _build_snapshot(row, contracts)

    def latest(self, underlying: str) -> OptionChainSnapshot | None:
        with self._connect() as db:
            row = db.execute(
                "SELECT * FROM option_snapshots WHERE underlying=? "
                "ORDER BY observed_at DESC LIMIT 1", (underlying,),
            ).fetchone()
            if row is None:
                return None
            contracts = db.execute(
                "SELECT * FROM option_contracts WHERE snapshot_id=? ORDER BY strike, option_type",
                (row["id"],),
            ).fetchall()
        return _build_snapshot(row, contracts)

    def recent(self, underlying: str, limit: int = 20) -> tuple[OptionChainSnapshot, ...]:
        """Return up to limit snapshots in chronological order."""
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise ValueError("limit must be a positive integer")
        with self._connect() as db:
            rows = db.execute(
                "SELECT * FROM (SELECT * FROM option_snapshots WHERE underlying=? "
                "ORDER BY observed_at DESC LIMIT ?) ORDER BY observed_at ASC",
                (underlying, limit),
            ).fetchall()
            result = []
            for row in rows:
                contracts = db.execute(
                    "SELECT * FROM option_contracts WHERE snapshot_id=? ORDER BY strike, option_type",
                    (row["id"],),
                ).fetchall()
                result.append(_build_snapshot(row, contracts))
        return tuple(result)


def _iso_utc(value: datetime) -> str:
    return to_utc(value).isoformat(timespec="microseconds")


def _build_snapshot(row: sqlite3.Row, rows: list[sqlite3.Row]) -> OptionChainSnapshot:
    contracts = tuple(
        OptionContract(
            strike=item["strike"],
            option_type=item["option_type"],
            open_interest=item["open_interest"],
            observed_at=datetime.fromisoformat(item["contract_observed_at"]),
            change_in_oi=item["change_in_oi"],
            volume=item["volume"],
            last_price=item["last_price"],
            instrument=item["instrument"],
        )
        for item in rows
    )
    return OptionChainSnapshot(
        underlying=row["underlying"],
        spot_price=row["spot_price"],
        observed_at=datetime.fromisoformat(row["observed_at"]),
        contracts=contracts,
        complete=bool(row["complete"]),
    )
