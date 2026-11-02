from pathlib import Path
import sys,json,os
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT.parent/'qqq-eod-replay/runtime/vendor'),str(ROOT.parents[1]/'.python_packages')]
# Never retain inherited provider credentials in this process environment.
for k in list(os.environ):
 if k.startswith(('ALPACA_','APCA_')) or k=='QQQ_EOD_STATE_KEY':os.environ.pop(k)
if __name__=='__main__':
 try:
  from qqq_alerts.service import serve
  raise SystemExit(serve(ROOT))
 except Exception as e:
  from qqq_alerts.outbox import atomic
  atomic(ROOT/'runtime/status.json',dict(state='watcher_failed',error_type=type(e).__name__,read_only_live=True))
  raise SystemExit(1)
