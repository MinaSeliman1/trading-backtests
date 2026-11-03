"""Explicit offline recovery of an existing shadow position; no API or order code."""
from copy import deepcopy
from pathlib import Path
import argparse,hashlib,io,json,math,sqlite3
import pandas as pd
from .core import advance,note,KEYS
from .ledger import dump,Ledger
from qqq_paper.runtime import ProcessLock,session_for


def position_digest(account,day):
    return hashlib.sha256(dump(dict(account=account,day=day)).encode('utf-8')).hexdigest()


def prepare_recovery(account,day,bars,session,asof):
    if not day or day['phase']!='unresolved' or not day.get('entry_done') or account['open_day']!=day['day']:
        raise ValueError('existing unresolved entered position required')
    if day.get('trade') or str(session.open.date())!=day['day']:
        raise ValueError('wrong session or existing trade')
    asof=pd.Timestamp(asof)
    if asof.tz is None or bars.index.tz is None or bars.index.has_duplicates:
        raise ValueError('unique timezone-aware bars required')
    if asof<pd.Timestamp(day['entry_observed_at']) or asof<session.open+pd.Timedelta(minutes=day['last_processed']+1):
        raise ValueError('recovery cannot move clock backwards')
    if any(str(j) not in day['bars'] for j in range(6)):
        raise ValueError('original opening and entry bars required')
    q=day['intent']['quantity'];sign=day['intent']['sign'];entry=day['bars']['5'][0]
    stop=min(day['bars'][str(j)][2] for j in range(5)) if sign==1 else max(day['bars'][str(j)][1] for j in range(5))
    fee=max(.35,q*.0035)
    checks=[day['entry_reference']==entry,day['entry_price']==entry+sign*.01,day['entry_fee']==fee,day['intent']['stop']==stop,
            math.isclose(account['balance'],day['capital_before']-fee,rel_tol=0,abs_tol=1e-8)]
    if not all(checks):raise ValueError('original entry/account inconsistent')
    d=deepcopy(day);d['phase']='active';d.pop('reason',None);note(d,'historical_recovery')
    a,d=advance(account,d,bars,session,asof)
    if d['phase']=='unresolved':raise ValueError('recovery still unresolved; no mutation permitted')
    last_closed=min(int((session.close-session.open).total_seconds()/60)-1,int((asof-session.open).total_seconds()//60)-1)
    if d['phase']=='active' and d['last_processed']!=last_closed:
        raise ValueError('recovery still unresolved: missing closed bars inside live grace period')
    for field in ('intent','entry_reference','entry_price','entry_fee','entry_observed_at','capital_before','peak_before','dd_before'):
        if d[field]!=day[field]:raise ValueError('original entry modified')
    if any(d['bars'].get(k)!=v for k,v in day['bars'].items()):raise ValueError('known bars modified')
    if d.get('trade'):
        t=d['trade']
        if (t['quantity'],t['sign'],t['entry_price'],t['stop_price'])!=(q,sign,day['entry_price'],stop):
            raise ValueError('recovered trade changed entry')
    elif a['balance']!=account['balance']:raise ValueError('entry fee charged twice')
    revisions=0
    for at,row in bars.iterrows():
        slot=(at-session.open).total_seconds()/60
        key=str(int(slot))
        if slot==int(slot) and key in day['bars']:
            value=[float(row[k]) if pd.notna(row[k]) else None for k in KEYS]
            revisions+=value!=day['bars'][key]
    d['fully_observed']=False;d['prospective']=False
    return a,d,dict(previous_digest=position_digest(account,day),result_digest=position_digest(a,d),source_revision_count=revisions,
                    old_last_processed=day['last_processed'],new_last_processed=d['last_processed'],new_phase=d['phase'],logical_asof=str(asof))


def recover(ledger,session,bars,asof,*,expected_digest,source_sha256):
    if len(source_sha256)!=64 or any(c not in '0123456789abcdef' for c in source_sha256):raise ValueError('source SHA256 required')
    with ledger.db:
        ledger.db.execute('BEGIN IMMEDIATE')
        date=str(session.open.date());old=ledger.day(date);account=ledger.get_account()
        if position_digest(account,old)!=expected_digest:raise ValueError('position changed since reviewed snapshot')
        if ledger.db.execute("SELECT 1 FROM trades WHERE day=?",(date,)).fetchone() or ledger.db.execute("SELECT 1 FROM events WHERE day=? AND kind='recovery'",(date,)).fetchone():
            raise ValueError('existing recovery or closed trade')
        entry=ledger.db.execute("SELECT data FROM events WHERE day=? AND kind='entry'",(date,)).fetchone()
        if not entry:raise ValueError('original entry audit required')
        recorded=json.loads(entry[0])
        expected={k:old[k] for k in ('intent','entry_reference','entry_price','entry_fee','entry_observed_at')}
        if recorded!=expected:raise ValueError('original entry audit inconsistent')
        a,d,audit=prepare_recovery(account,old,bars,session,asof)
        audit.update(source_sha256=source_sha256,recovered_at=str(pd.Timestamp.now(tz='UTC')),previous_account=account,previous_day=old,broker_orders=False)
        ledger.put('account',a)
        ledger.db.execute('UPDATE days SET data=? WHERE day=?',(dump(d),date))
        ledger.db.execute('INSERT INTO events VALUES(?,?,?)',(date,'recovery',dump(audit)))
        if d.get('trade'):
            ledger.db.execute('INSERT INTO trades VALUES(?,?)',(date,dump(d['trade'])))
            ledger.db.execute('INSERT INTO events VALUES(?,?,?)',(date,'exit',dump(d['trade'])))
    return audit


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--runtime',type=Path,required=True);p.add_argument('--evidence',type=Path,required=True)
    p.add_argument('--apply',action='store_true');p.add_argument('--expected-digest')
    args=p.parse_args(argv);root=args.runtime.resolve();evidence=args.evidence.resolve()
    receipt=json.loads((evidence/'data_receipt.json').read_text(encoding='utf-8'))
    path=evidence/'sip-bars.csv';source_bytes=path.read_bytes();sha=hashlib.sha256(source_bytes).hexdigest()
    if sha!=receipt['sha256']:raise ValueError('source receipt mismatch')
    asof=pd.Timestamp(receipt['logical_asof'])
    if asof>pd.Timestamp.now(tz='UTC')-pd.Timedelta(minutes=16):raise ValueError('delayed source cutoff required')
    bars=pd.read_csv(io.BytesIO(source_bytes),index_col=0,parse_dates=True);bars.index=pd.to_datetime(bars.index,utc=True)
    if (bars.index>=asof).any():raise ValueError('source contains unclosed or future bars')
    with ProcessLock(root/'background.lock'):
        if (root/'STOP_SHADOW.flag').exists():raise ValueError('operator STOP; no recovery applied')
        # Preview never opens the active journal writable.
        ro=sqlite3.connect((root/'state.sqlite').as_uri()+'?mode=ro',uri=True)
        try:
            ro.execute('PRAGMA query_only=ON')
            account=json.loads(ro.execute("SELECT value FROM meta WHERE key='account'").fetchone()[0])
            row=ro.execute('SELECT data FROM days WHERE day=?',(account['open_day'],)).fetchone();day=json.loads(row[0]) if row else None
            session=session_for(account['open_day'])
            a,d,audit=prepare_recovery(account,day,bars,session,asof)
        finally:ro.close()
        if args.apply:
            if args.expected_digest!=audit['previous_digest']:raise ValueError('reviewed digest required for apply')
            backup=evidence/'apply-before.sqlite'
            if backup.exists():raise ValueError('apply backup already exists')
            src=sqlite3.connect((root/'state.sqlite').as_uri()+'?mode=ro',uri=True);dest=sqlite3.connect(backup)
            try:src.backup(dest)
            finally:dest.close();src.close()
            with Ledger(root/'state.sqlite') as db:
                audit=recover(db,session,bars,asof,expected_digest=args.expected_digest,source_sha256=sha)
                if db.db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise RuntimeError('integrity check')
            (evidence/'applied_receipt.json').write_text(json.dumps(audit,indent=2,allow_nan=False),encoding='utf-8')
        summary={k:v for k,v in audit.items() if not k.startswith('previous_') or k=='previous_digest'}
        summary.update(applied=args.apply,open_day=a['open_day'],balance=a['balance'],trade=d.get('trade'),broker_orders=False)
        print(json.dumps(summary,indent=2,allow_nan=False))
    return 0


if __name__=='__main__':raise SystemExit(main())
