"""API HTTP restreinte au compte PAPER et aux données QQQ."""
import json
import re
import socket,ssl,errno
from urllib.error import HTTPError,URLError
from urllib.parse import urlencode,quote,urlparse
from urllib.request import Request,build_opener,HTTPRedirectHandler
import pandas as pd

PAPER='https://paper-api.alpaca.markets'
DATA='https://data.alpaca.markets'


class OrderNotSent(ValueError):
    """Refus local certain : aucun POST n'a été tenté."""


class APIError(Exception):
    def __init__(self,status,method,path):
        self.status=status
        super().__init__(f'Alpaca HTTP {status} {method} {path}')


class DataConnectionError(ConnectionError):
    """Safe classification only: no provider text, URL, headers or credentials."""
    CODES=frozenset(('dns','tls','timeout','connection_refused','connection_reset','network_unreachable','redirect_refused','network_unknown'))
    def __init__(self,reason_code):
        self.reason_code=reason_code if reason_code in self.CODES else 'network_unknown'
        super().__init__('Alpaca request incomplete: '+self.reason_code+'; reconcile before retry')


def network_failure_code(error):
    if isinstance(error,DataConnectionError):return error.reason_code
    cause=error.reason if isinstance(error,URLError) else error
    if isinstance(cause,socket.gaierror):return 'dns'
    if isinstance(cause,ssl.SSLError):return 'tls'
    if isinstance(cause,TimeoutError):return 'timeout'
    if isinstance(cause,ConnectionRefusedError):return 'connection_refused'
    if isinstance(cause,ConnectionResetError):return 'connection_reset'
    if isinstance(cause,OSError) and (cause.errno in (errno.ENETUNREACH,errno.EHOSTUNREACH) or getattr(cause,'winerror',None) in (10051,10065)):return 'network_unreachable'
    return 'network_unknown'


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):raise DataConnectionError('redirect_refused')


class Transport:
    def __init__(self,key,secret):
        if not key or not secret:raise ValueError('missing paper credentials')
        self._headers={'APCA-API-KEY-ID':key,'APCA-API-SECRET-KEY':secret,'User-Agent':'QQQNoiseAreaPaper/1.0'}
        self._opener=build_opener(NoRedirect())

    def clear(self):self._headers.clear()

    def request(self,origin,path,method='GET',params=None,body=None):
        if origin not in (PAPER,DATA) or not path.startswith('/') or path.startswith('//') or '..' in path or urlparse(path).scheme:
            raise ValueError('unapproved API origin/path')
        allowed_data=path in ('/v2/stocks/QQQ/bars','/v1/corporate-actions')
        allowed_paper=bool(re.fullmatch(r'/v2/(account|clock|calendar|assets/QQQ|positions(?:/QQQ)?|orders(?::by_client_order_id|/[A-Za-z0-9_-]+)?)',path))
        if origin==DATA and (method!='GET' or not allowed_data):raise ValueError('market data is read-only')
        if origin==PAPER and not allowed_paper:raise ValueError('unapproved paper route')
        if method not in ('GET','POST','DELETE'):raise ValueError('method refused')
        if method=='POST':
            if origin!=PAPER or path!='/v2/orders' or not body or body.get('symbol')!='QQQ':raise ValueError('only QQQ paper orders allowed')
        if method=='DELETE' and (origin!=PAPER or not path.startswith('/v2/orders/')):raise ValueError('only known paper order cancellation allowed')
        url=origin+path+('?' + urlencode(params) if params else '')
        headers=dict(self._headers);payload=json.dumps(body).encode('utf-8') if body is not None else None
        if payload is not None:headers['Content-Type']='application/json'
        try:
            with self._opener.open(Request(url,data=payload,headers=headers,method=method),timeout=15) as response:
                raw=response.read();return json.loads(raw) if raw else None
        except HTTPError as error:raise APIError(error.code,method,path) from None
        except (URLError,TimeoutError,OSError) as error:raise DataConnectionError(network_failure_code(error)) from None


class PaperBroker:
    def __init__(self,transport):self.transport=transport
    def account(self):return self.transport.request(PAPER,'/v2/account')
    def clock(self):return self.transport.request(PAPER,'/v2/clock')
    def asset(self):return self.transport.request(PAPER,'/v2/assets/QQQ')
    def position(self):
        try:
            row=self.transport.request(PAPER,'/v2/positions/QQQ')
            qty=float(row['qty'])
            if not qty.is_integer():raise ValueError('external fractional QQQ position')
            return int(qty)
        except APIError as e:
            if e.status==404:return 0
            raise
    def open_orders(self):return self.transport.request(PAPER,'/v2/orders',params=dict(status='open',symbols='QQQ',limit=500))
    def calendar(self,day):return self.transport.request(PAPER,'/v2/calendar',params=dict(start=day,end=day))
    def get_order(self,cid):
        try:
            row=self.transport.request(PAPER,'/v2/orders:by_client_order_id',params=dict(client_order_id=cid))
            if row.get('symbol','QQQ')!='QQQ':raise ValueError('unexpected order symbol')
            return row
        except APIError as e:
            if e.status==404:return None
            raise
    def cancel(self,provider_id):return self.transport.request(PAPER,'/v2/orders/'+quote(provider_id,safe=''),'DELETE')
    def submit(self,cid,action,sign,qty):
        if action not in ('open','close') or sign not in (-1,1) or not isinstance(qty,int) or qty<=0:raise OrderNotSent('invalid paper order')
        try:clock=self.clock()
        except (APIError,ConnectionError,TimeoutError):raise OrderNotSent('clock validation unavailable; no POST attempted') from None
        at=pd.Timestamp(clock['timestamp']);closing=pd.Timestamp(clock['next_close'])
        if not clock['is_open'] or at>=closing-pd.Timedelta(seconds=1):raise OrderNotSent('paper market closed or closing')
        match=re.fullmatch(r'naqqq-(\d{8})-(\d{4})-[oc][bs]',cid)
        if match:
            date,hm=match.groups();moment=pd.Timestamp(f'{date[:4]}-{date[4:6]}-{date[6:]} {hm[:2]}:{hm[2:]}',tz='America/New_York')
            if not 0<=(at-moment).total_seconds()<=20:raise OrderNotSent('expired decision at final broker clock')
        elif action=='open':raise OrderNotSent('scheduled client order id required for opening')
        intent=('buy' if sign==1 else 'sell')+'_to_'+action
        return self.transport.request(PAPER,'/v2/orders','POST',body=dict(symbol='QQQ',qty=str(qty),side='buy' if sign==1 else 'sell',
              type='market',time_in_force='day',extended_hours=False,client_order_id=cid,position_intent=intent))


class DataClient:
    def __init__(self,transport):self.transport=transport
    def bars(self,start,end,feed):
        if feed not in ('sip','iex'):raise ValueError('feed must be sip or iex')
        start=pd.Timestamp(start);end=pd.Timestamp(end)
        if start.tz is None or end.tz is None or start>=end:raise ValueError('invalid bar range')
        params=dict(timeframe='1Min',start=start.tz_convert('UTC').isoformat(),end=end.tz_convert('UTC').isoformat(),
                    feed=feed,adjustment='raw',limit=10000,sort='asc')
        rows=[];tokens=set()
        for _ in range(100):
            page=self.transport.request(DATA,'/v2/stocks/QQQ/bars',params=params)
            rows.extend(page.get('bars') or []);token=page.get('next_page_token')
            if not token:break
            if token in tokens:raise ValueError('repeated data pagination token')
            tokens.add(token);params['page_token']=token
        else:raise ValueError('data pagination limit')
        if not rows:return pd.DataFrame(columns=['open','high','low','close','volume'],index=pd.DatetimeIndex([],tz='UTC',name='timestamp'))
        f=pd.DataFrame(rows).rename(columns={'o':'open','h':'high','l':'low','c':'close','v':'volume'})
        f.index=pd.to_datetime(f.pop('t'),utc=True,format='mixed');f.index.name='timestamp'
        return f.loc[(f.index>=start)&(f.index<end),['open','high','low','close','volume']].sort_index()
    def dividend(self,day):
        params=dict(symbols='QQQ',start=day,end=day,limit=1000);values={};seen=set()
        for _ in range(20):
            page=self.transport.request(DATA,'/v1/corporate-actions',params=params)
            for x in page.get('corporate_actions',{}).get('cash_dividends',[]):
                if x['symbol']=='QQQ' and x['ex_date']==day:
                    value=float(x['rate'])
                    if value<0:raise ValueError('invalid dividend')
                    key=x['ex_date']
                    if key in values and values[key]!=value:raise ValueError('conflicting dividend amounts')
                    values[key]=value
            token=page.get('next_page_token')
            if not token:return values.get(day,0.)
            if token in seen:raise ValueError('repeated corporate action page')
            seen.add(token);params['page_token']=token
        raise ValueError('corporate action pagination limit')
