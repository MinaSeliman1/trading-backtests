from pathlib import Path
import sys,json,hashlib
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pandas as pd
import pytest
from orb_shadow.ledger import Ledger
from orb_shadow.recovery import prepare_recovery,position_digest,recover
from test_core import session,bars

SOURCE='a'*64

def broken(db,s,f):
    db.tick(s,f,s.open+pd.Timedelta(minutes=6))
    db.tick(s,f.drop(f.index[7]),s.open+pd.Timedelta(minutes=11))
    assert db.day(str(s.open.date()))['phase']=='unresolved'


def test_recovery_closes_same_trade_without_second_entry_fee(tmp_path):
    s=session();f=bars(s);f.iloc[10,:4]=[100,100.2,98,100]
    with Ledger(tmp_path/'state.sqlite',1000) as db:
        broken(db,s,f);before=db.get_account();old=db.day(str(s.open.date()))
        entry=db.db.execute("SELECT data FROM events WHERE kind='entry'").fetchone()[0]
        cfg=db.db.execute("SELECT value FROM meta WHERE key='configuration'").fetchone()[0]
        digest=position_digest(before,old)
        receipt=recover(db,s,f,s.close,expected_digest=digest,source_sha256=SOURCE)
        d=db.day(old['day']);a=db.get_account()
        assert d['phase']=='closed' and a['balance']==pytest.approx(989.1) and a['open_day'] is None
        assert d['intent']==old['intent'] and d['entry_price']==old['entry_price'] and d['entry_fee']==old['entry_fee']
        assert not d['prospective'] and not d['fully_observed']
        assert all(d['bars'][k]==v for k,v in old['bars'].items())
        assert db.db.execute("SELECT data FROM events WHERE kind='entry'").fetchone()[0]==entry
        assert db.db.execute("SELECT value FROM meta WHERE key='configuration'").fetchone()[0]==cfg
        assert db.db.execute('SELECT COUNT(*) FROM trades').fetchone()[0]==1
        assert db.db.execute("SELECT COUNT(*) FROM events WHERE kind='recovery'").fetchone()[0]==1
        assert receipt['previous_digest']==digest
        with pytest.raises(ValueError):recover(db,s,f,s.close,expected_digest=digest,source_sha256=SOURCE)
        assert db.get_account()==a


def test_no_forced_close_when_original_position_still_active(tmp_path):
    s=session();f=bars(s)
    with Ledger(tmp_path/'state.sqlite',1000) as db:
        broken(db,s,f);old=db.day(str(s.open.date()));before=db.get_account()
        a,d,audit=prepare_recovery(before,old,f,s,s.open+pd.Timedelta(minutes=20))
        assert d['phase']=='active' and a['open_day']==old['day'] and a['balance']==before['balance']
        assert not d['fully_observed'] and not d['prospective'] and 'reason' not in d
        assert d['last_processed']==19 and old['last_processed']==6


def test_missing_data_remains_unresolved_and_nothing_is_written(tmp_path):
    s=session();f=bars(s)
    with Ledger(tmp_path/'state.sqlite',1000) as db:
        broken(db,s,f);a=db.get_account();d=db.day(str(s.open.date()));fingerprint=position_digest(a,d)
        with pytest.raises(ValueError,match='unresolved'):
            recover(db,s,f.drop(f.index[7]),s.close,expected_digest=fingerprint,source_sha256=SOURCE)
        assert position_digest(db.get_account(),db.day(d['day']))==fingerprint
        assert db.db.execute("SELECT COUNT(*) FROM events WHERE kind='recovery'").fetchone()[0]==0


def test_stale_approval_digest_is_refused(tmp_path):
    s=session();f=bars(s)
    with Ledger(tmp_path/'state.sqlite',1000) as db:
        broken(db,s,f)
        with pytest.raises(ValueError,match='changed'):
            recover(db,s,f,s.close,expected_digest='b'*64,source_sha256=SOURCE)


def test_source_revisions_do_not_reprice_known_entry_or_opening(tmp_path):
    s=session();f=bars(s)
    with Ledger(tmp_path/'state.sqlite',1000) as db:
        broken(db,s,f);a=db.get_account();d=db.day(str(s.open.date()))
        revised=f.copy();revised.iloc[5,:4]=[101,101.2,100.8,101]
        aa,dd,audit=prepare_recovery(a,d,revised,s,s.close)
        assert dd['entry_reference']==100 and dd['trade']['entry_reference']==100
        assert dd['trade']['net_pnl']==pytest.approx(9.1) and audit['source_revision_count']==1


@pytest.mark.parametrize('field,value',[('entry_reference',101),('entry_fee',.7),('entry_price',101.01)])
def test_inconsistent_saved_entry_is_refused(tmp_path,field,value):
    s=session();f=bars(s)
    with Ledger(tmp_path/'state.sqlite',1000) as db:
        broken(db,s,f);a=db.get_account();d=db.day(str(s.open.date()));d[field]=value
        with pytest.raises(ValueError,match='entry'):
            prepare_recovery(a,d,f,s,s.close)


def test_recent_missing_closed_minute_is_refused_even_inside_live_grace(tmp_path):
    s=session();f=bars(s)
    with Ledger(tmp_path/'state.sqlite',1000) as db:
        broken(db,s,f);a=db.get_account();d=db.day(str(s.open.date()))
        with pytest.raises(ValueError,match='missing closed bars'):
            prepare_recovery(a,d,f.drop(f.index[18]),s,s.open+pd.Timedelta(minutes=20))
        assert position_digest(db.get_account(),db.day(d['day']))==position_digest(a,d)


def test_missing_bars_after_determined_exit_are_not_needed(tmp_path):
    s=session();f=bars(s);f.iloc[10,:4]=[100,100.2,98,100]
    with Ledger(tmp_path/'state.sqlite',1000) as db:
        broken(db,s,f)
        a,d,audit=prepare_recovery(db.get_account(),db.day(str(s.open.date())),f.iloc[:11],s,s.close)
        assert d['phase']=='closed' and d['trade']['exit_slot']==10


@pytest.mark.parametrize('apply',[False,True])
def test_cli_preview_and_apply_use_the_same_hashed_source_bytes(tmp_path,monkeypatch,capsys,apply):
    import io,sqlite3
    from orb_shadow.recovery import main
    s=session();f=bars(s);runtime=tmp_path/'runtime';evidence=tmp_path/'evidence';evidence.mkdir()
    path=evidence/'sip-bars.csv';f.to_csv(path,index_label='timestamp');sha=hashlib.sha256(path.read_bytes()).hexdigest()
    (evidence/'data_receipt.json').write_text(json.dumps(dict(logical_asof=str(s.close),sha256=sha)))
    with Ledger(runtime/'state.sqlite') as db:
        broken(db,s,f);digest=position_digest(db.get_account(),db.day(str(s.open.date())))
        before=[(table,list(db.db.execute('SELECT * FROM '+table+' ORDER BY 1'))) for table in ('meta','days','events','trades')]
    original=pd.read_csv
    def parse(buffer,**kwargs):
        assert isinstance(buffer,io.BytesIO) and hashlib.sha256(buffer.getvalue()).hexdigest()==sha
        return original(buffer,**kwargs)
    monkeypatch.setattr('orb_shadow.recovery.pd.read_csv',parse)
    args=['--runtime',str(runtime),'--evidence',str(evidence)]
    if apply:args+=['--apply','--expected-digest',digest]
    assert main(args)==0
    result=json.loads(capsys.readouterr().out);assert result['applied']==apply
    if apply:
        backup=sqlite3.connect(evidence/'apply-before.sqlite')
        try:assert json.loads(backup.execute('SELECT data FROM days').fetchone()[0])['phase']=='unresolved'
        finally:backup.close()
        assert json.loads((evidence/'applied_receipt.json').read_text())['source_sha256']==sha
    else:
        with Ledger(runtime/'state.sqlite') as db:
            after=[(table,list(db.db.execute('SELECT * FROM '+table+' ORDER BY 1'))) for table in ('meta','days','events','trades')]
        assert after==before and not (evidence/'apply-before.sqlite').exists()


@pytest.mark.parametrize('guard',['sha','stop','instance_lock'])
def test_cli_guard_refusals_leave_position_unchanged(tmp_path,guard):
    from contextlib import nullcontext
    from orb_shadow.recovery import main
    from qqq_paper.runtime import ProcessLock
    s=session();f=bars(s);runtime=tmp_path/'runtime';evidence=tmp_path/'evidence';evidence.mkdir()
    path=evidence/'sip-bars.csv';f.to_csv(path,index_label='timestamp');sha=hashlib.sha256(path.read_bytes()).hexdigest()
    (evidence/'data_receipt.json').write_text(json.dumps(dict(logical_asof=str(s.close),sha256='0'*64 if guard=='sha' else sha)))
    with Ledger(runtime/'state.sqlite') as db:
        broken(db,s,f);before=position_digest(db.get_account(),db.day(str(s.open.date())))
    if guard=='stop':(runtime/'STOP_SHADOW.flag').touch()
    held=ProcessLock(runtime/'background.lock') if guard=='instance_lock' else nullcontext()
    with held,pytest.raises((ValueError,RuntimeError)):
        main(['--runtime',str(runtime),'--evidence',str(evidence),'--apply','--expected-digest',before])
    with Ledger(runtime/'state.sqlite') as db:
        assert position_digest(db.get_account(),db.day(str(s.open.date())))==before
    assert not (evidence/'apply-before.sqlite').exists()
