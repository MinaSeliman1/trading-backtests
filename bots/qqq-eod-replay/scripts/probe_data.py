"""Small historical SIP authorization probe, no P&L, account API or orders."""
from pathlib import Path
import sys,json,os,argparse,tempfile
BOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(BOT))

def probe(key,secret):
 import pandas as pd
 from qqq_eod.source import freeze_sources,activate_sources,QQQDataOnly,canonical_frame
 from qqq_eod.schedule import calendar
 lock=json.loads((BOT/'ENGINE_LOCK.json').read_text());root=Path(tempfile.mkdtemp(prefix='qqq-probe-source-'));activate_sources(freeze_sources(BOT.parents[1],lock,root),lock)
 from qqq_paper.alpaca import Transport,DataClient
 now=pd.Timestamp.now(tz='UTC');today=now.tz_convert('America/New_York').date();c=calendar(str(today),str(today));past=c.schedule[c.schedule['close']+pd.Timedelta(minutes=17)<=now]
 row=past.iloc[-1];transport=QQQDataOnly(Transport(key,secret));client=DataClient(transport)
 try:frame=canonical_frame(client.bars(row['open'],row['open']+pd.Timedelta(minutes=5),'sip'))
 finally:transport.clear()
 if len(frame)!=5:raise ValueError('historical SIP probe incomplete')
 return dict(probe='passed',feed='sip',adjustment='raw',rows=len(frame),source_day=str(row['open'].tz_convert('America/New_York').date()),requests_kind='QQQ market data GET only',broker_orders=0,pnl_calculated=False)

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path);args=parser.parse_args();result=probe(os.environ['ALPACA_PAPER_KEY_ID'],os.environ['ALPACA_PAPER_SECRET_KEY'])
 if args.output:args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2),encoding='utf-8')
 print(json.dumps(result));return 0
if __name__=='__main__':
 try:raise SystemExit(main())
 except Exception as e:print(json.dumps(dict(probe='failed',error_type=type(e).__name__,api_status=getattr(e,'status',None),credential_values_output=False)));raise SystemExit(1)
