from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pandas as pd
import pytest
from qqq_paper.__main__ import arguments,preflight
from qqq_paper.ledger import Store
from qqq_paper.strategy import Parameters
from qqq_paper.runtime import session_for,load_history


def test_cli_defaults_are_shadow_and_no_live_endpoint_exists():
    args=arguments([])
    assert args.mode=='shadow' and args.feed=='sip'
    with pytest.raises(SystemExit):arguments(['--mode','live'])
    with pytest.raises(SystemExit):arguments(['--base-url','https://api.alpaca.markets'])


def test_paper_account_binding_refuses_changed_account_or_blocked_trading(tmp_path):
    class Fake:
        def __init__(self):self.id='paperA';self.block=False
        def account(self):return dict(id=self.id,status='ACTIVE',trading_blocked=self.block,equity='100000')
    b=Fake();s=Store(tmp_path/'s.db',Parameters(),'paper','iex');preflight(b,s)
    b.id='paperB'
    with pytest.raises(ValueError,match='account'):preflight(b,s)
    b.id='paperA';b.block=True
    with pytest.raises(ValueError,match='blocked'):preflight(b,s)


def test_calendar_holiday_and_early_close_are_real_calendar():
    assert session_for('2026-12-25') is None
    s=session_for('2026-11-27')
    assert s.flatten.strftime('%H:%M')=='12:59'


def test_history_rejects_completely_missing_previous_session(tmp_path):
    class Data:
        def bars(self,start,end,feed):
            s=session_for('2026-10-16');idx=pd.date_range(s.open,s.close,inclusive='left',freq='min')
            return pd.DataFrame(dict(open=100.,high=101.,low=99.,close=100.,volume=1000.),index=idx)
    with pytest.raises(ValueError,match='previous NYSE'):load_history(Data(),session_for('2026-10-20'),tmp_path,'iex')


def test_history_rejects_incomplete_prior_days_before_reporting_running(tmp_path):
    from qqq_paper.runtime import calendar
    class Data:
        def bars(self,start,end,feed):
            cal=calendar('2026-10-20')
            rows=[]
            for day in cal.sessions_in_range('2026-09-21','2026-10-19'):
                s=session_for(day)
                idx=pd.date_range(s.open,s.close,inclusive='left',freq='min')
                rows.append(pd.DataFrame(dict(open=100.,high=101.,low=99.,close=100.,volume=1000.),index=idx))
            frame=pd.concat(rows)
            return frame.drop(pd.Timestamp('2026-10-15 14:15',tz='America/New_York'))
    with pytest.raises(ValueError,match='15 consecutive valid'):load_history(Data(),session_for('2026-10-20'),tmp_path,'iex')
