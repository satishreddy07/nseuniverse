"""Provider-neutral ingestion pipeline for normalized option-chain snapshots."""

from nse_universe.ingestion.pipeline import IngestionResult, OptionSnapshotIngestor

__all__ = ["IngestionResult", "OptionSnapshotIngestor"]
