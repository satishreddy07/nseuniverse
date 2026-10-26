import pytest
from nse_universe.providers.instrument_master import InstrumentMaster

def test_loads_kotak_style_csv_and_looks_up_contract(tmp_path):
    path = tmp_path / "nse_fo.csv"
    path.write_text(
        "pSymbol,pScripRefKey,pTrdSymbol,pInstType,lExpiryDate,dStrikePrice,pOptionType,lLotSize\\n"
        "nse_fo,98765,NIFTY26OCT26000CE,OPTIDX,2026-10-29,26000,CE,65\\n"
        "nse_fo,98766,NIFTY26OCT26000PE,OPTIDX,2026-10-29,26000,PE,65\\n",
        encoding="utf-8",
    )
    master = InstrumentMaster.from_csv(path)
    item = master.get("nse_fo", "98765")
    assert item is not None
    assert item.trading_symbol == "NIFTY26OCT26000CE"
    assert item.strike == 26000
    assert item.option_type == "CE"
    assert item.lot_size == 65
    assert master.by_symbol("nse_fo", "nifty26oct26000pe").token == "98766"
    assert len(master.search("NIFTY", exchange_segment="nse_fo")) == 2

def test_master_rejects_empty_and_duplicate_keys(tmp_path):
    path = tmp_path / "empty.csv"
    path.write_text("pSymbol,pScripRefKey,pTrdSymbol\\n", encoding="utf-8")
    with pytest.raises(ValueError, match="no usable instruments"):
        InstrumentMaster.from_csv(path)
    with pytest.raises(ValueError, match="Duplicate"):
        from nse_universe.providers.instrument_master import Instrument
        InstrumentMaster([Instrument("1", "nse_fo", "A"), Instrument("1", "nse_fo", "B")])
