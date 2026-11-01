"""Actions entrypoint. Inactive until task0 approval and rule7 registration."""
from pathlib import Path
import argparse,json,sys
BOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(BOT))
from qqq_eod.activation import status

def main():
 p=argparse.ArgumentParser();p.add_argument('--mode',choices=['status','run'],default='status');a=p.parse_args();s=status(BOT)
 if a.mode=='status' or not s['active']:print(json.dumps(s));return 0
 # The approved rule package must supply policy/state identity before any provider secret is read.
 from qqq_eod.runner import run_registered
 return run_registered(BOT)
if __name__=='__main__':
 try:raise SystemExit(main())
 except Exception as e:
  print(json.dumps(dict(state='replay_blocked',error_type=type(e).__name__,credentials_printed=False)));raise SystemExit(1)
