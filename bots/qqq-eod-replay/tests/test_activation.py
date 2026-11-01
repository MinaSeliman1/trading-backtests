from pathlib import Path
import json,subprocess,sys
from qqq_eod.activation import status

def test_activation_needs_both_committed_rule_and_explicit_switch(tmp_path,monkeypatch):
 (tmp_path/'ENGINE_LOCK.json').write_text(json.dumps({'strategy_commit':'fixed'}));(tmp_path/'activation.json').write_text(json.dumps({'enabled':False,'first_statistical_session':None}))
 monkeypatch.setenv('QQQ_EOD_ENABLED','true');assert not status(tmp_path)['active']
 (tmp_path/'activation.json').write_text(json.dumps({'enabled':True,'first_statistical_session':'2026-11-02'}));monkeypatch.delenv('QQQ_EOD_ENABLED');assert not status(tmp_path)['active']

def test_current_entrypoint_does_not_read_or_print_provider_credentials(monkeypatch):
 bot=Path(__file__).resolve().parents[1];monkeypatch.setenv('ALPACA_PAPER_KEY_ID','DUMMY-MUST-NOT-APPEAR');monkeypatch.setenv('ALPACA_PAPER_SECRET_KEY','DUMMY-SECRET-MUST-NOT-APPEAR')
 p=subprocess.run([sys.executable,str(bot/'scripts/run_replay.py'),'--mode','run'],capture_output=True,text=True)
 assert p.returncode==0 and 'DUMMY' not in p.stdout+p.stderr
 obj=json.loads(p.stdout);assert obj['credentials_loaded'] is False and obj['active'] is False
