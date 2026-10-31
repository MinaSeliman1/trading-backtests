from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'audit'))
from independent import features,replay
from test_engine import path,small,market,feature
def test_scalar_band_hand_calculation():
 f=features(path(),small())[-1];assert f['reason']=='eligible' and f['entry_slot']==26 and f['target_price']==97.33 and f['stop_price']==94.79
def test_scalar_roundtrip_manual():
 f=feature();d,t,u,dd,usd=replay(market(),[f],small(),f['date'],f['date'])
 assert len(t)==1 and not u and t[0]['quantity']==1000 and t[0]['net_pnl']==pytest.approx(973.)
