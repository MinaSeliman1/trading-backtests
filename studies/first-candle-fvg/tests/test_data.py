import pandas as pd
import pytest
from fvg_backtest.data import load_csv
from tests.test_engine import session


def save(tmp_path, df):
    p=tmp_path/"bars.csv"; df.rename_axis("timestamp").to_csv(p); return p


def test_complete_and_dst_and_duplicate(tmp_path):
    df=pd.concat([session("2025-03-07"),session("2025-03-10")])
    df=pd.concat([df,df.iloc[:1]])
    result=load_csv(save(tmp_path,df),"SPY")
    assert len(result.sessions)==2
    assert result.manifest["identical_duplicates_removed"]==1
    assert result.sessions[0].index[0].utcoffset().total_seconds()==-18000
    assert result.sessions[1].index[0].utcoffset().total_seconds()==-14400


def test_missing_minute_invalid_ohlc_and_holiday(tmp_path):
    df=session().drop(session().index[0])
    assert not load_csv(save(tmp_path,df),"SPY").sessions
    df=session(); df.iloc[20,2]=200
    assert not load_csv(save(tmp_path,df),"SPY").sessions
    assert not load_csv(save(tmp_path,session("2025-12-25")),"SPY").sessions


def test_early_close_and_no_naive_timezone(tmp_path):
    assert len(load_csv(save(tmp_path,session("2025-11-28","13:00")),"SPY").sessions)==1
    df=session(); df.index=df.index.tz_localize(None)
    with pytest.raises(ValueError,match="timezone"):
        load_csv(save(tmp_path,df),"SPY")


def test_futures_need_contract_identity_and_rolls(tmp_path):
    with pytest.raises(ValueError,match="contract"):
        load_csv(save(tmp_path,session()),"ES")


def test_conflicting_duplicate_excludes_session(tmp_path):
    df=session(); extra=df.iloc[:1].copy(); extra["close"]=100.5
    assert not load_csv(save(tmp_path,pd.concat([df,extra])),"SPY").sessions


def test_fixed_contract_and_dated_margin(tmp_path):
    df=session(); df["contract"]="ESZ25"
    rolls=tmp_path/"rolls.csv"; rolls.write_text("effective_date,instrument,contract\n2025-03-01,ES,ESZ25\n")
    margins=tmp_path/"margins.csv"; margins.write_text("effective_date,instrument,margin_per_unit\n2025-03-01,ES,20000\n")
    d=load_csv(save(tmp_path,df),"ES",rolls=rolls,margins=margins)
    assert d.sessions[0].attrs["contract"]=="ESZ25"
    assert d.sessions[0].attrs["margin"]==20000
    with pytest.raises(ValueError,match="strict futures"):
        load_csv(save(tmp_path,df),"ES",rolls=rolls,strict_futures=True)
