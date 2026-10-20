"""Compte net durable. Chaque mise à jour cumulative de fill est idempotente."""
from dataclasses import asdict
from pathlib import Path
import csv
import json
import math
import sqlite3
from datetime import datetime,timezone


class Store:
    def __init__(self,path,parameters,mode,feed):
        if mode not in ('paper','shadow') or feed not in ('sip','iex'):raise ValueError('mode/feed')
        self.parameters=parameters;self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        self.db=sqlite3.connect(self.path);self.db.row_factory=sqlite3.Row
        self.db.execute('PRAGMA journal_mode=WAL');self.db.execute('PRAGMA synchronous=FULL')
        self.db.executescript('''CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS orders(cid TEXT PRIMARY KEY,day TEXT,action TEXT,sign INTEGER,quantity INTEGER,clock TEXT,
        status TEXT DEFAULT 'prepared',provider_id TEXT,filled INTEGER DEFAULT 0,average REAL DEFAULT 0,fee REAL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS fills(seq INTEGER PRIMARY KEY,cid TEXT,qty INTEGER,sign INTEGER,actual REAL,modeled REAL,
        commission REAL,borrow REAL,realized REAL,timestamp TEXT);
        CREATE TABLE IF NOT EXISTS decisions(key TEXT PRIMARY KEY,data TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS days(day TEXT PRIMARY KEY,quantity INTEGER,balance REAL,opening REAL,volatility REAL);''')
        config=json.dumps(dict(parameters=asdict(parameters),mode=mode,feed=feed),sort_keys=True)
        old=self.get('configuration')
        if old is not None and old!=config:self.db.close();raise ValueError('configuration does not match existing state')
        with self.db:
            self.put('configuration',config)
            if self.get('account') is None:self._save_account(dict(balance=parameters.initial_capital,position=0,entry=0.))

    def close(self):self.db.close()
    def get(self,key):
        row=self.db.execute('SELECT value FROM meta WHERE key=?',(key,)).fetchone()
        return row[0] if row else None
    def put(self,key,value):self.db.execute('INSERT OR REPLACE INTO meta VALUES(?,?)',(key,str(value)))
    def _account(self):return json.loads(self.get('account'))
    def _save_account(self,obj):self.put('account',json.dumps(obj,allow_nan=False))
    @property
    def balance(self):return self._account()['balance']
    @property
    def position(self):return self._account()['position']
    @property
    def entry(self):return self._account()['entry']
    @property
    def position_day(self):
        value=self._account().get('entry_timestamp')
        return datetime.fromisoformat(value).date().isoformat() if self.position and value else None
    def equity(self,price):return self.balance+self.position*(float(price)-self.entry)
    def order(self,cid):
        row=self.db.execute('SELECT * FROM orders WHERE cid=?',(cid,)).fetchone()
        return dict(row) if row else None
    def pending(self):return [dict(r) for r in self.db.execute("SELECT * FROM orders WHERE status NOT IN ('filled','canceled','expired','rejected')")]
    def intent(self,cid,day,action,sign,quantity,clock):
        if action not in ('open','close') or sign not in (-1,1) or not isinstance(quantity,int) or quantity<=0:raise ValueError('invalid intent')
        values=(cid,day,action,sign,quantity,clock);old=self.order(cid)
        if old:
            if tuple(old[k] for k in ('cid','day','action','sign','quantity','clock'))!=values:raise ValueError('intent collision')
            return False
        with self.db:self.db.execute('INSERT INTO orders(cid,day,action,sign,quantity,clock) VALUES(?,?,?,?,?,?)',values)
        return True

    def apply(self,snapshot):
        cid=snapshot['client_order_id'];old=self.order(cid)
        if not old:raise ValueError('unknown order')
        raw=float(snapshot.get('filled_qty') or 0)
        if not math.isfinite(raw) or raw!=int(raw):raise ValueError('noninteger fill')
        count=int(raw);average=float(snapshot.get('filled_avg_price') or 0);delta=count-old['filled']
        if count<old['filled'] or count>old['quantity']:raise ValueError('invalid cumulative fill')
        if snapshot['status']=='filled' and count!=old['quantity']:raise ValueError('filled status with incomplete quantity')
        if count and (not math.isfinite(average) or average<=0):raise ValueError('invalid fill price')
        if not delta and count and abs(average-old['average'])>1e-8:raise ValueError('fill correction requires reconciliation')
        account=self._account();p=self.parameters;fee=max(p.minimum_commission,count*p.commission) if count else 0.
        if delta:
            price=(average*count-old['average']*old['filled'])/delta
            if not math.isfinite(price) or price<=0:raise ValueError('invalid incremental price')
            modeled=price+old['sign']*p.slippage;borrow=0.;realized=0.
            if old['action']=='open':
                if account['position']*old['sign']<0:raise ValueError('must close before reversal')
                if not account['position']:account['entry_timestamp']=snapshot.get('filled_at') or datetime.now(timezone.utc).isoformat()
                total=abs(account['position'])+delta
                account['entry']=(account['entry']*abs(account['position'])+modeled*delta)/total
            else:
                if account['position']*old['sign']>=0 or delta>abs(account['position']):raise ValueError('close exceeds managed position')
                realized=delta*(1 if account['position']>0 else -1)*(modeled-account['entry'])
                closing=datetime.fromisoformat(snapshot.get('filled_at') or datetime.now(timezone.utc).isoformat()).date()
                opening=datetime.fromisoformat(account['entry_timestamp']).date()
                days=max(1,(closing-opening).days)
                borrow=delta*account['entry']*p.borrow_rate*days/360 if account['position']<0 else 0.
            account['position']+=old['sign']*delta
            account['balance']+=realized-(fee-old['fee'])-borrow
            if not account['position']:account['entry']=0.
        with self.db:
            if delta:
                self._save_account(account)
                self.db.execute('INSERT INTO fills(cid,qty,sign,actual,modeled,commission,borrow,realized,timestamp) VALUES(?,?,?,?,?,?,?,?,?)',
                    (cid,delta,old['sign'],price,modeled,fee-old['fee'],borrow,realized,snapshot.get('filled_at') or datetime.now(timezone.utc).isoformat()))
            self.db.execute('UPDATE orders SET status=?,provider_id=?,filled=?,average=?,fee=? WHERE cid=?',
                            (snapshot['status'],snapshot.get('id'),count,average,fee,cid))

    def fills(self):return [dict(r) for r in self.db.execute('SELECT * FROM fills ORDER BY seq')]
    def record(self,key,data):
        with self.db:self.db.execute('INSERT OR IGNORE INTO decisions VALUES(?,?)',(key,json.dumps(data,sort_keys=True,allow_nan=False)))
    def recorded(self,key):return self.db.execute('SELECT 1 FROM decisions WHERE key=?',(key,)).fetchone() is not None
    def pause(self,reason):
        with self.db:self.put('paused',reason)
    def set_day(self,day,quantity,opening,volatility):
        old=self.db.execute('SELECT * FROM days WHERE day=?',(day,)).fetchone()
        if old:return dict(old)
        with self.db:self.db.execute('INSERT INTO days VALUES(?,?,?,?,?)',(day,quantity,self.balance,opening,volatility))
        return dict(self.db.execute('SELECT * FROM days WHERE day=?',(day,)).fetchone())
    def export(self,folder):
        folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
        for name,rows in [('fills',self.fills()),('decisions',[dict(r) for r in self.db.execute('SELECT * FROM decisions ORDER BY key')])]:
            if not rows:continue
            target=folder/f'{name}.csv';temp=target.with_suffix('.tmp')
            with temp.open('w',newline='',encoding='utf-8') as stream:
                writer=csv.DictWriter(stream,fieldnames=rows[0].keys());writer.writeheader();writer.writerows(rows)
            temp.replace(target)
