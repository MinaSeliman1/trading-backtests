from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'audit'))
from independent import features,replay
from test_engine import market,Config,feature
def test_scalar_past_tr_and_level_manual():
 f=features(market(),Config())[-1];assert f['atr']==2 and f['breakout_level']==100.66 and f['entry_slot']==6
def test_scalar_manual_roundtrip():
 f=feature();d,t,u,dd,usd=replay(market(),[f],Config(),f['date'],f['date'])
 assert len(t)==1 and not u and t[0]['quantity']==1000 and t[0]['net_pnl']==pytest.approx(973.)
