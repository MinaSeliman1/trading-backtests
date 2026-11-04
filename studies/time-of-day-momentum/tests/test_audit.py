from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'audit'))
from dataclasses import asdict
import copy
import numpy as np
import pytest
import oracle
from test_engine import market
from seasonal.engine import Config,prepare,simulate


@pytest.mark.parametrize('mode',['both','inverse','long_only','control_same_clock_long','control_fixed_clock','control_random_clock'])
def test_scalar_oracle_matches_features_and_money(mode):
    m=market(negative=True);c=Config(mode=mode,initial_capital=1000);history=oracle.historical_returns(m);f=prepare(m,c)[-1];o=oracle.feature(m,len(m.dates)-1,asdict(c),history)
    for key in ('reason','historical_slot','reference_sign','sign','entry_slot','scheduled_exit_slot'):
        assert f.get(key)==o.get(key)
    if f['reason']=='eligible':
        x=oracle.trade(m,o,asdict(c),1000);r=simulate(m,[f],c,f['date'],f['date']);t=r.trades.iloc[0]
        for key in ('quantity','exit_slot','entry_reference','exit_reference','entry_price','exit_price','commission','borrow_fee','friction_cost','net_pnl'):
            assert t[key]==pytest.approx(x[key])
        assert t['exit_reason']==x['exit_reason']


def test_scalar_oracle_refuses_same_history_hole():
    m=market();m.arrays['open'][-2,40]=np.nan;c=Config();h=oracle.historical_returns(m)
    assert oracle.feature(m,69,asdict(c),h)['reason']=='unknown_history'
