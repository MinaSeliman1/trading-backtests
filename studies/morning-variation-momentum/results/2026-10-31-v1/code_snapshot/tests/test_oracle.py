from pathlib import Path
from types import SimpleNamespace
import sys,math
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'audit'))
from independent import features,replay
from test_engine import market,cfg
def test_scalar_oracle_hand_computed_roundtrip():
 m=market();c=cfg();fs=features(m,c)
 assert abs(fs[-1]['score']-math.sqrt(30))<1e-10
 d,t,u,dd,usd=replay(m,fs,c,fs[-1]['date'],fs[-1]['date'])
 assert not u and len(t)==1 and t[0]['quantity']==1000
 assert abs(t[0]['net_pnl']-973)<1e-7 and abs(d[0]['equity']-100973)<1e-7
