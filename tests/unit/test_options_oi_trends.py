from datetime import datetime, timedelta, timezone

from nse_universe.options.models import OptionChainSnapshot, OptionContract
from nse_universe.options.oi_trends import summarize_oi_trends


def snapshot(at, call_oi, put_oi, call_oi_25k=None, put_oi_25k=None):
    return OptionChainSnapshot(
        underlying="NIFTY", spot_price=25000, observed_at=at, complete=True,
        contracts=(
            OptionContract(25000, "CE", call_oi, at),
            OptionContract(25000, "PE", put_oi, at),
            OptionContract(25100, "CE", call_oi_25k if call_oi_25k is not None else call_oi, at),
            OptionContract(25100, "PE", put_oi_25k if put_oi_25k is not None else put_oi, at),
        ),
    )


def test_summarize_net_oi_changes_and_rank_contracts():
    at = datetime(2026, 10, 26, 9, 15, tzinfo=timezone.utc)
    report = summarize_oi_trends([
        snapshot(at, 100, 200, 300, 400),
        snapshot(at + timedelta(minutes=1), 130, 180, 350, 390),
        snapshot(at + timedelta(minutes=2), 160, 170, 320, 450),
    ])
    assert report.call_oi_change == 80
    assert report.put_oi_change == 20
    assert report.pcr_start == 1.0
    assert report.pcr_latest == 620 / 480
    assert report.top_call_additions[0].strike == 25000
    assert report.top_call_additions[0].net_change == 60
    assert report.top_put_additions[0].strike == 25100
    assert report.top_put_additions[0].net_change == 50
    assert report.top_call_unwinding[0].strike == 25100
    assert report.top_put_unwinding[0].strike == 25000


def test_requires_two_chronological_snapshots():
    at = datetime(2026, 10, 26, 9, 15, tzinfo=timezone.utc)
    one = snapshot(at, 100, 100)
    try:
        summarize_oi_trends([one])
    except ValueError as exc:
        assert "at least two" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_rejects_out_of_order_snapshots():
    at = datetime(2026, 10, 26, 9, 15, tzinfo=timezone.utc)
    try:
        summarize_oi_trends([snapshot(at, 100, 100), snapshot(at, 110, 110)])
    except ValueError as exc:
        assert "chronological" in str(exc)
    else:
        raise AssertionError("expected ValueError")
