from datetime import datetime, timezone
from nse_universe.options.chain_validation import validate_chain
from nse_universe.options.models import OptionChainSnapshot, OptionContract
NOW=datetime(2026,10,26,10,0,tzinfo=timezone.utc)
def c(strike,side): return OptionContract(strike,side,100,NOW)
def snap(items,complete): return OptionChainSnapshot("NIFTY",25000,NOW,tuple(items),complete)
def test_complete_chain_usable():
    result=validate_chain(snap([c(24900,"CE"),c(24900,"PE")],True))
    assert result.is_usable and not result.issues
def test_incomplete_chain_rejected():
    result=validate_chain(snap([c(24900,"CE"),c(24900,"PE")],False))
    assert not result.is_usable and any("incomplete" in issue for issue in result.issues)
def test_missing_side_reported():
    result=validate_chain(snap([c(24900,"CE")],True))
    assert not result.is_usable and result.missing_contracts==((24900,"PE"),)
def test_expected_missing_strike_reported():
    result=validate_chain(snap([c(24900,"CE"),c(24900,"PE")],True),expected_strikes=[24900,25000])
    assert (25000,"CE") in result.missing_contracts and (25000,"PE") in result.missing_contracts
def test_empty_chain_rejected():
    result=validate_chain(snap([],True))
    assert not result.is_usable and "snapshot contains no contracts" in result.issues
