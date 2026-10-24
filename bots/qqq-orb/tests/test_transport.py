from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pytest
from orb_shadow.service import ReadOnlyTransport
from qqq_paper.alpaca import Transport,DATA,PAPER


def test_get_guard_allows_only_qqq_sip_data_and_never_any_broker_request(monkeypatch):
    calls=[]
    def fake(self,*args,**kwargs):calls.append((args,kwargs));return {'bars':[]}
    monkeypatch.setattr(Transport,'request',fake)
    t=ReadOnlyTransport('synthetic','synthetic')
    assert t.request(DATA,'/v2/stocks/QQQ/bars',params={'feed':'sip'})=={'bars':[]}
    for origin,path,method,params in [(PAPER,'/v2/orders','POST',{}),(PAPER,'/v2/clock','GET',{}),(DATA,'/v2/stocks/QQQ/bars','POST',{'feed':'sip'}),(DATA,'/v2/stocks/SPY/bars','GET',{'feed':'sip'}),(DATA,'/v2/stocks/QQQ/bars','GET',{'feed':'iex'})]:
        with pytest.raises(ValueError):t.request(origin,path,method,params=params)
    assert len(calls)==1
    t.clear()
