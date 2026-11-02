import json
from pathlib import Path
import pytest
from qqq_eod import runner

def test_inactive_context_cannot_enter_registered_run(monkeypatch):
 monkeypatch.delenv('GITHUB_ACTIONS',raising=False)
 with pytest.raises(ValueError):runner.run_registered(Path(__file__).resolve().parents[1])

def test_public_summary_preserves_pending_and_unknown():
 data=dict(first_day='2026-11-02',accounts={'noise':100000,'orb':100000},sessions=[dict(bot='noise',day='2026-11-02',status='pending',result=None,inputs=None),dict(bot='orb',day='2026-11-02',status='unresolved',result={'net_pnl':None,'capital_after':None,'open_position':10,'known_commission':.35},inputs={'sha':'x'})])
 out=runner.public_summary(data,{'generation':'test'})
 assert out['sessions'][0]['status']=='pending' and 'net_pnl' not in out['sessions'][0]
 assert out['sessions'][1]['net_pnl'] is None and out['sessions'][1]['open_position']==10
 assert not out['operationally_observed']

def test_worker_version_check_rejects_changed_registered_file(tmp_path):
 import subprocess
 repo=tmp_path;bot=repo/'bots/qqq-eod-replay';(bot/'qqq_eod').mkdir(parents=True);f=bot/'qqq_eod/module.py';f.write_bytes(b'x=1\n')
 for args in [('init',),('-c','user.name=Fixture','-c','user.email=fixture@example.invalid','add','.'),('-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-m','Fixture')]:subprocess.run(['git',*args],cwd=repo,check=True,capture_output=True)
 commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()
 assert runner.verify_package(bot,commit)
 f.write_text('x=2\n')
 with pytest.raises(ValueError):runner.verify_package(bot,commit)
