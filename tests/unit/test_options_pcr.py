from datetime import datetime, timezone
import pytest
from nse_universe.options.models import OptionContract
from nse_universe.options.pcr import calculate_atm_pcr, calculate_nearby_pcr, calculate_pcr, find_atm_strike
NOW=datetime(2026,10,26,10,0,tzinfo=timezone.utc)
def c(strike,side,oi): return OptionContract(strike,side,oi,NOW)
def test_overall_pcr(): assert calculate_pcr([c(100,"CE",100),c(100,"PE",250)]).pcr==2.5
def test_zero_call_oi_is_undefined():
    result=calculate_pcr([c(100,"PE",250)])
    assert result.pcr is None and "zero" in result.reason_unavailable
def test_empty_chain_unavailable(): assert calculate_pcr([]).pcr is None
def test_atm_tie_chooses_lower(): assert find_atm_strike(105,[110,100])==100
def test_atm_pcr_scopes_to_one_strike():
    result=calculate_atm_pcr([c(100,"CE",100),c(100,"PE",200),c(110,"CE",900)],spot_price=102)
    assert result.pcr==2 and result.scope=="ATM strike 100"
def test_nearby_pcr_uses_nearest_distinct_strikes():
    items=[c(90,"CE",100),c(90,"PE",100),c(100,"CE",100),c(100,"PE",300),c(110,"CE",100),c(110,"PE",500),c(120,"CE",100),c(120,"PE",900)]
    result=calculate_nearby_pcr(items,spot_price=101,strike_count_each_side=1)
    assert result.put_oi==800 and result.call_oi==300
def test_invalid_nearby_range_rejected():
    with pytest.raises(ValueError): calculate_nearby_pcr([c(100,"CE",1)],spot_price=100,strike_count_each_side=-1)
def test_no_strikes_rejected():
    with pytest.raises(ValueError): find_atm_strike(100,[])
