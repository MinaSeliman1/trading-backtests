from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pytest
from qqq_paper.alpaca import Transport,PaperBroker,APIError,DataClient,PAPER,DATA,OrderNotSent
import pandas as pd


def test_live_endpoint_and_mutating_data_requests_are_rejected():
    t=Transport('test-key','test-secret')
    with pytest.raises(ValueError):t.request('https://api.alpaca.markets','/v2/orders','POST',body={})
    with pytest.raises(ValueError):t.request(DATA,'/v2/orders','POST',body={})
    with pytest.raises(ValueError):t.request(PAPER,'https://evil.example/','GET')
    assert 'test-secret' not in str(t)


def test_broker_only_submits_qqq_market_day_during_open_clock():
    class Fake:
        def __init__(self):self.sent=[];self.open=True
        def request(self,origin,path,method='GET',params=None,body=None):
            if path=='/v2/clock':return dict(is_open=self.open,timestamp='2026-10-20T14:00:01Z',next_close='2026-10-20T20:00:00Z')
            self.sent.append((origin,path,method,body));return body
    f=Fake();b=PaperBroker(f);b.submit('naqqq-20261020-1000-ob','open',1,10)
    origin,path,method,body=f.sent[0]
    assert origin==PAPER and body['symbol']=='QQQ' and body['type']=='market' and body['time_in_force']=='day' and body['extended_hours'] is False
    f.open=False
    with pytest.raises(ValueError,match='closed'):b.submit('other','open',1,10)
    assert len(f.sent)==1


def test_last_broker_clock_prevents_late_open_after_data_or_reverse_close():
    class Fake:
        def __init__(self):self.posts=0
        def request(self,origin,path,method='GET',params=None,body=None):
            if method=='POST':self.posts+=1;return body
            return dict(is_open=True,timestamp='2026-10-20T14:00:21Z',next_close='2026-10-20T20:00:00Z')
    f=Fake();b=PaperBroker(f)
    with pytest.raises(OrderNotSent,match='expired'):b.submit('naqqq-20261020-1000-ob','open',1,10)
    assert f.posts==0


def test_clock_network_failure_is_known_unsent():
    class Fake:
        def request(self,*args,**kwargs):raise ConnectionError('read clock failed')
    with pytest.raises(OrderNotSent):PaperBroker(Fake()).submit('naqqq-20261020-1000-ob','open',1,10)


def test_data_pagination_raw_feed_and_exclusive_end():
    class Fake:
        def __init__(self):self.calls=[]
        def request(self,origin,path,method='GET',params=None,body=None):
            self.calls.append(params.copy());i=len(self.calls)
            return dict(bars=[dict(t=f'2026-10-20T13:{29+i}:00Z',o=100,h=101,l=99,c=100,v=1000)],next_page_token='next' if i==1 else None)
    f=Fake();d=DataClient(f)
    bars=d.bars(pd.Timestamp('2026-10-20T13:30Z'),pd.Timestamp('2026-10-20T13:31Z'),'iex')
    assert len(bars)==1 and len(f.calls)==2
    assert f.calls[0]['feed']=='iex' and f.calls[0]['adjustment']=='raw' and f.calls[1]['page_token']=='next'


def test_error_text_never_contains_provider_body_or_credentials():
    e=APIError(403,'GET','/v2/account')
    assert str(e)=='Alpaca HTTP 403 GET /v2/account'
