from pathlib import Path
from types import SimpleNamespace
import sys
import pandas as pd
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'audit'))
from independent import validate_export_keys

def frames():
    t=pd.DataFrame([dict(date='2024-01-02',symbol='SPY',mode='long_only',quality='complete_days',sign=1,direction='LONG')])
    u=pd.DataFrame([dict(date='2024-01-03',symbol='SPY',sign=1)])
    cfg=SimpleNamespace(symbol='SPY',mode='long_only',quality='complete_days')
    return t,u,cfg
def test_exact_trade_and_unknown_membership():
    t,u,c=frames();validate_export_keys(t,u,{'2024-01-02':1},{'2024-01-03':1},c)
@pytest.mark.parametrize('bad',['extra_trade','extra_unknown','missing_trade','missing_unknown','wrong_sign','wrong_symbol','wrong_direction','wrong_mode','wrong_quality'])
def test_audit_rejects_extra_missing_or_mislabeled_rows(bad):
    t,u,c=frames()
    if bad=='extra_trade':t=pd.concat([t,t.assign(date='1999-01-01')])
    if bad=='extra_unknown':u=pd.concat([u,u.assign(date='1999-01-01')])
    if bad=='missing_trade':t=t.iloc[:0]
    if bad=='missing_unknown':u=u.iloc[:0]
    for tag,key,val in [('wrong_sign','sign',-1),('wrong_symbol','symbol','QQQ'),('wrong_direction','direction','SHORT'),('wrong_mode','mode','both'),('wrong_quality','quality','resolved_prefix')]:
        if bad==tag:t.loc[0,key]=val
    with pytest.raises(AssertionError):validate_export_keys(t,u,{'2024-01-02':1},{'2024-01-03':1},c)
