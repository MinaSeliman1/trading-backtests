from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import json
import pandas as pd
from qqq_paper.ledger import Store
from qqq_paper.strategy import Parameters,decision_times
from qqq_paper.runtime import session_for,finalize_shadow_session


def populate(store,session,late=False):
    for at in decision_times(session):
        observed=at+pd.Timedelta(minutes=10 if late else 1)
        store.record(f'{session.open.date()}:{at:%H%M}',dict(status='processed',observed_at=str(observed)))


def test_completed_session_requires_close_flat_and_all_decisions(tmp_path):
    s=Store(tmp_path/'s.db',Parameters(),'shadow','sip');session=session_for('2026-10-21')
    assert not finalize_shadow_session(s,session,session.close)
    populate(s,session)
    assert not finalize_shadow_session(s,session,session.close-pd.Timedelta(minutes=1))
    assert finalize_shadow_session(s,session,session.close)
    j=json.loads(s.get('completed_session:2026-10-21'))
    assert j['fully_prospective'] and j['processed_decisions']==12
    assert not finalize_shadow_session(s,session,session.close)


def test_replayed_day_is_never_counted_as_fully_prospective(tmp_path):
    s=Store(tmp_path/'s.db',Parameters(),'shadow','sip');session=session_for('2026-10-21');populate(s,session,late=True)
    assert finalize_shadow_session(s,session,session.close)
    assert not json.loads(s.get('completed_session:2026-10-21'))['fully_prospective']


def test_paused_or_open_position_cannot_mark_session_complete(tmp_path):
    s=Store(tmp_path/'s.db',Parameters(),'shadow','sip');session=session_for('2026-10-21');populate(s,session)
    with s.db:s._save_account(dict(balance=100000.,position=1,entry=100.))
    assert not finalize_shadow_session(s,session,session.close)
    with s.db:s._save_account(dict(balance=100000.,position=0,entry=0.))
    s.pause('missing data')
    assert not finalize_shadow_session(s,session,session.close)


def test_late_closure_is_not_a_fully_observed_session(tmp_path):
    s=Store(tmp_path/'s.db',Parameters(),'shadow','sip');session=session_for('2026-10-21');populate(s,session)
    assert finalize_shadow_session(s,session,session.close+pd.Timedelta(minutes=10))
    assert not json.loads(s.get('completed_session:2026-10-21'))['fully_prospective']


def test_slow_fetch_cannot_use_earlier_data_cutoff_as_observation_time(tmp_path):
    s=Store(tmp_path/'s.db',Parameters(),'shadow','sip');session=session_for('2026-10-21');populate(s,session)
    assert finalize_shadow_session(s,session,session.close,observed_at=session.close+pd.Timedelta(minutes=9))
    assert not json.loads(s.get('completed_session:2026-10-21'))['fully_prospective']
