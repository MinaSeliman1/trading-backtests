"""Frozen scenario membership and summary binding, without market data."""
import json,sys,copy
from pathlib import Path
import pandas as pd
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'audit'))

def fixture(tmp_path):
    rows=[]
    f=dict(symbols=['SPY','QQQ'],periods={'TEST':['2024-01-02','2024-01-03']},specifications={'reference':{'slippage':.01},'stress':{'slippage':.02}},executions=4)
    (tmp_path/'PRE_EXECUTION_PROTOCOL.json').write_text(json.dumps(f),encoding='utf-8')
    for s in f['symbols']:
        for v,cfg in f['specifications'].items():
            row=dict(label=f'{s}_TEST_{v}',symbol=s,period='TEST',variant=v,start='2024-01-02',end='2024-01-03',**cfg,net_pnl=1.2345678901,profit_factor=None)
            rows.append(row);p=tmp_path/row['label'];p.mkdir();(p/'summary.json').write_text(json.dumps(row),encoding='utf-8')
    return pd.DataFrame(rows)

def test_full_frozen_matrix_and_summaries_accept_roundtrip(tmp_path):
    from matrix import validate_matrix
    frame=fixture(tmp_path);assert validate_matrix(frame,tmp_path)>0

@pytest.mark.parametrize('corruption',['duplicate','config','dates','summary'])
def test_frozen_matrix_rejects_repeated_rows_or_drift(tmp_path,corruption):
    from matrix import validate_matrix
    frame=fixture(tmp_path)
    if corruption=='duplicate':frame.iloc[1]=frame.iloc[0]
    if corruption=='config':frame.loc[0,'slippage']=.05
    if corruption=='dates':frame.loc[0,'start']='2024-01-03'
    if corruption=='summary':
        p=tmp_path/frame.iloc[0].label/'summary.json';d=json.loads(p.read_text(encoding='utf-8'));d['net_pnl']=100;p.write_text(json.dumps(d),encoding='utf-8')
    with pytest.raises(AssertionError):validate_matrix(frame,tmp_path)
