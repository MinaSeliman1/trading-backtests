"""Ledger independant, transactionnel, aucune cle ni requete reseau."""
from pathlib import Path
from dataclasses import asdict
from datetime import datetime,timezone
import json,sqlite3
from .core import account,advance,verify_model,MODEL_SHA,PARAMETERS
APP_ID=1330790995
dump=lambda x:json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False)


class Ledger:
    def __init__(self,path,capital=100000):
        verify_model();self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True);existed=self.path.exists();self.db=sqlite3.connect(self.path,timeout=15)
        try:
            if existed and self.db.execute('PRAGMA application_id').fetchone()[0]!=APP_ID:raise ValueError('other database refused')
            self.db.execute('PRAGMA journal_mode=WAL');self.db.execute(f'PRAGMA application_id={APP_ID}')
            self.db.executescript('CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value TEXT NOT NULL); CREATE TABLE IF NOT EXISTS days(day TEXT PRIMARY KEY,data TEXT NOT NULL); CREATE TABLE IF NOT EXISTS trades(day TEXT PRIMARY KEY,data TEXT NOT NULL); CREATE TABLE IF NOT EXISTS events(day TEXT NOT NULL,kind TEXT NOT NULL,data TEXT NOT NULL,PRIMARY KEY(day,kind));')
            settings=dict(mode='shadow',feed='sip',delay_minutes=16,capital=capital,model_sha256=MODEL_SHA,parameters=asdict(PARAMETERS))
            existing=self.get('configuration')
            if existing is not None and existing!=settings:raise ValueError('configuration changed; ledger not reset')
            with self.db:
                if existing is None:
                    self.put('configuration',settings);self.put('account',account(capital));self.put('started_utc',datetime.now(timezone.utc).isoformat())
        except Exception:self.db.close();raise

    def get(self,key):
        r=self.db.execute('select value from meta where key=?',(key,)).fetchone();return json.loads(r[0]) if r else None
    def put(self,key,value):self.db.execute('INSERT INTO meta VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(key,dump(value)))
    def get_account(self):return self.get('account')
    def record_restart(self):
        date=self.get_account()['open_day']
        if not date:return
        d=self.day(date)
        if d is None:raise ValueError('open position without session state')
        d['prospective']=False;d['fully_observed']=False
        if 'process_restart' not in d['notes']:d['notes'].append('process_restart')
        with self.db:
            self.db.execute('UPDATE days SET data=? WHERE day=?',(dump(d),date))
            self.db.execute('INSERT OR IGNORE INTO events VALUES(?,?,?)',(date,'process_restart',dump(dict(utc=datetime.now(timezone.utc).isoformat()))))
    def day(self,date):
        r=self.db.execute('select data from days where day=?',(date,)).fetchone();return json.loads(r[0]) if r else None
    def tick(self,session,bars,asof):
        date=str(session.open.date())
        with self.db:
            self.db.execute('BEGIN IMMEDIATE');previous=self.day(date);a,d=advance(self.get_account(),previous,bars,session,asof)
            self.put('account',a);self.db.execute('INSERT INTO days VALUES(?,?) ON CONFLICT(day) DO UPDATE SET data=excluded.data',(date,dump(d)))
            if d.get('entry_done') and not (previous or {}).get('entry_done'):
                self.db.execute('INSERT INTO events VALUES(?,?,?)',(date,'entry',dump({k:d[k] for k in ('intent','entry_reference','entry_price','entry_fee','entry_observed_at')})))
            if 'trade' in d:
                value=dump(d['trade']);existing=self.db.execute('SELECT data FROM trades WHERE day=?',(date,)).fetchone()
                if existing and existing[0]!=value:raise ValueError('closed trade mutation refused')
                self.db.execute('INSERT OR IGNORE INTO trades VALUES(?,?)',(date,value))
                self.db.execute('INSERT OR IGNORE INTO events VALUES(?,?,?)',(date,'exit',value))
            for kind in d['notes']:self.db.execute('INSERT OR IGNORE INTO events VALUES(?,?,?)',(date,kind,dump(dict(asof=str(asof),phase=d['phase']))))
        return a,d
    def __enter__(self):return self
    def __exit__(self,*args):self.db.close()
