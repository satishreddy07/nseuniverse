from datetime import datetime, timedelta, timezone
import pytest
from nse_universe.options.models import OptionChainSnapshot, OptionContract
from nse_universe.options.oi_analysis import classify_price_oi_quadrant, compare_open_interest
T0=datetime(2026,10,26,10,0,tzinfo=timezone.utc)
def c(strike,side,oi,price,at): return OptionContract(strike,side,oi,at,last_price=price)
def snap(at,items,complete=True): return OptionChainSnapshot("NIFTY",25000,at,tuple(items),complete)
def test_oi_and_price_delta():
    later=T0+timedelta(minutes=1)
    result=compare_open_interest(snap(T0,[c(25000,"CE",1000,100,T0)]),snap(later,[c(25000,"CE",1250,112,later)]))
    assert result.changes[0].change_in_oi==250 and result.changes[0].price_change==12
def test_new_and_missing_contracts():
    later=T0+timedelta(minutes=1)
    result=compare_open_interest(snap(T0,[c(25000,"CE",1000,100,T0)]),snap(later,[c(25000,"PE",2000,90,later)]))
    assert result.missing_from_current==((25000.0,"CE"),)
    assert result.new_in_current==((25000.0,"PE"),)
def test_comparison_requires_same_underlying_and_later_time():
    with pytest.raises(ValueError): compare_open_interest(snap(T0,[]),OptionChainSnapshot("BANKNIFTY",50000,T0+timedelta(minutes=1),(),True))
    with pytest.raises(ValueError): compare_open_interest(snap(T0,[]),snap(T0,[]))
@pytest.mark.parametrize(("price","oi","expected"),[(1,1,"long_buildup"),(-1,1,"short_buildup"),(1,-1,"short_covering"),(-1,-1,"long_unwinding"),(0,0,"unchanged_or_ambiguous")])
def test_price_oi_quadrants(price,oi,expected): assert classify_price_oi_quadrant(price,oi)==expected
