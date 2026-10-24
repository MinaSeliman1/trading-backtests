"""Automatic sleep must not interrupt an AC-powered shadow session."""
from pathlib import Path
import json
import sys
import threading
import time

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from qqq_paper.power import PowerGuard, protection_window


@pytest.mark.parametrize('at,want', [
    ('2026-10-23T13:14:59Z', False),
    ('2026-10-23T13:15:00Z', True),
    ('2026-10-23T20:19:59Z', True),
    ('2026-10-23T20:20:00Z', False),
    ('2026-10-24T14:00:00Z', False),
    ('2026-12-25T15:00:00Z', False),
    ('2026-11-27T18:19:59Z', True),
    ('2026-11-27T18:20:00Z', False),
    ('2026-11-02T14:15:00Z', True),
    ('2026-11-02T14:14:59Z', False),
])
def test_only_the_real_exchange_session_and_delayed_close_are_protected(at,want):
    assert protection_window(pd.Timestamp(at)) is want


class Power:
    """External Windows API boundary; the policy and lifecycle remain real."""
    def __init__(self):
        self.ac=True
        self.required=False
        self.transitions=[]
        self.fail=False

    def on_ac(self):
        if self.fail:
            raise OSError('private API detail must not be logged')
        return self.ac

    def system_required(self,enabled):
        self.required=enabled
        self.transitions.append((enabled,threading.get_ident()))


def test_ac_protection_releases_on_battery_and_unknown_power(tmp_path):
    api=Power()
    guard=PowerGuard(tmp_path,backend=api)
    at=pd.Timestamp('2026-10-23T15:00:00Z')
    guard.tick(at)
    assert api.required
    api.ac=False
    guard.tick(at+pd.Timedelta(seconds=15))
    assert not api.required
    api.ac=None
    guard.tick(at+pd.Timedelta(seconds=30))
    assert not api.required
    api.ac=True
    guard.tick(at+pd.Timedelta(seconds=45))
    assert api.required
    status=json.loads((tmp_path/'windows/power_status.json').read_text())
    assert status['state']=='protected' and status['system_required']


def test_ac_request_survives_the_night_so_next_session_is_not_blocked_by_sleep(tmp_path):
    api=Power();guard=PowerGuard(tmp_path,backend=api)
    guard.tick(pd.Timestamp('2026-10-23T20:20:00Z'))
    assert api.required
    guard.tick(pd.Timestamp('2026-10-24T03:00:00Z'))
    assert api.required
    status=json.loads((tmp_path/'windows/power_status.json').read_text())
    assert status['state']=='protected' and not status['in_session_window']


def test_power_failure_is_reported_released_and_can_recover(tmp_path):
    api=Power();guard=PowerGuard(tmp_path,backend=api)
    at=pd.Timestamp('2026-10-23T15:00:00Z')
    guard.tick(at);api.fail=True;guard.tick(at+pd.Timedelta(seconds=15))
    status=json.loads((tmp_path/'windows/power_status.json').read_text())
    assert status['state']=='error' and not api.required
    assert 'private API detail' not in json.dumps(status)
    api.fail=False;guard.tick(at+pd.Timedelta(seconds=30))
    assert api.required


def test_resume_gap_is_visible_but_never_reclassified_as_success(tmp_path):
    api=Power();guard=PowerGuard(tmp_path,backend=api)
    guard.tick(pd.Timestamp('2026-10-23T15:00:00Z'))
    guard.tick(pd.Timestamp('2026-10-23T18:00:00Z'))
    status=json.loads((tmp_path/'windows/power_status.json').read_text())
    assert status['last_gap_seconds']==10800
    assert status['last_gap_utc']=='2026-10-23T18:00:00+00:00'
    assert api.required


def test_operator_stop_releases_power_even_while_application_has_not_returned(tmp_path):
    api=Power();guard=PowerGuard(tmp_path,backend=api)
    at=pd.Timestamp('2026-10-23T15:00:00Z')
    guard.tick(at)
    assert api.required
    (tmp_path/'STOP_SHADOW.flag').touch()
    guard.tick(at+pd.Timedelta(seconds=15))
    assert not api.required
    status=json.loads((tmp_path/'windows/power_status.json').read_text())
    assert status['state']=='stop_requested'


def test_worker_keeps_request_during_blocking_work_and_releases_on_its_own_thread(tmp_path):
    api=Power()
    with PowerGuard(tmp_path,backend=api,clock=lambda:pd.Timestamp('2026-10-23T15:00:00Z'),interval=.01):
        deadline=time.monotonic()+3
        while not api.required and time.monotonic()<deadline:
            time.sleep(.01)
        assert api.required
        time.sleep(.05)  # supervisor/application may be waiting for data
        assert api.required
    assert not api.required
    assert api.transitions[0][0] is True and api.transitions[-1][0] is False
    assert len({thread for _,thread in api.transitions})==1
    assert api.transitions[0][1]!=threading.get_ident()
    status=json.loads((tmp_path/'windows/power_status.json').read_text())
    assert status['state']=='stopped' and not status['system_required']
