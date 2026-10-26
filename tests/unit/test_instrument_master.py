import pytest

from nse_universe.providers.instrument_master import InstrumentMaster, Instrument


def test_loads_actual_kotak_transformed_csv_and_uses_psymbol_as_token(tmp_path):
    path = tmp_path / "nse_fo.csv"
    path.write_text(
        "pSymbol,pGroup,pExchSeg,pInstType,pSymbolName,pTrdSymbol,pOptionType,"
        "pScripRefKey,lLotSize,lExpiryDate,dStrikePrice;\n"
        "98765,,nse_fo,OPTIDX,NIFTY,NIFTY26OCT26000CE,CE,NIFTY26OCT26000CE,65,1793000000,26000\n"
        "98766,,nse_fo,OPTIDX,NIFTY,NIFTY26OCT26000PE,PE,NIFTY26OCT26000PE,65,1793000000,26000\n",
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
    path.write_text("pSymbol,pExchSeg,pTrdSymbol\n", encoding="utf-8")
    with pytest.raises(ValueError, match="no usable instruments"):
        InstrumentMaster.from_csv(path)
    with pytest.raises(ValueError, match="Duplicate"):
        InstrumentMaster([Instrument("1", "nse_fo", "A"), Instrument("1", "nse_fo", "B")])
