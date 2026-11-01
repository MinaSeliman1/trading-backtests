"""Explicit activation gate; it runs before any credential loading."""
from pathlib import Path
import json,os

def status(bot_folder):
 root=Path(bot_folder);lock=json.loads((root/'ENGINE_LOCK.json').read_text(encoding='utf-8'));a=json.loads((root/'activation.json').read_text(encoding='utf-8'))
 allowed=a.get('enabled') is True and os.environ.get('QQQ_EOD_ENABLED','').lower()=='true'
 return dict(state='configured' if allowed else 'awaiting_approved_stop_rule',active=allowed,strategy_commit=lock['strategy_commit'],statistical_start=a.get('first_statistical_session'),credentials_loaded=False,operationally_observed=False)
