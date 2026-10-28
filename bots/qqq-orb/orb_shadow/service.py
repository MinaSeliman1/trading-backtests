from qqq_paper.alpaca import Transport,DATA
from pathlib import Path
from datetime import datetime,timezone
from logging.handlers import RotatingFileHandler
import argparse,json,logging,os,time
from contextlib import nullcontext
import pandas as pd
from qqq_paper.alpaca import DataClient,network_failure_code
from qqq_paper.windows_vault import WindowsVault
from qqq_paper.runtime import ProcessLock,session_for,write_status
from qqq_paper.power import PowerGuard
from .core import verify_model
from .ledger import Ledger
class ReadOnlyTransport(Transport):
    def request(self,origin,path,method='GET',params=None,body=None):
        if origin!=DATA or path!='/v2/stocks/QQQ/bars' or method!='GET' or body is not None or not params or params.get('feed')!='sip':raise ValueError('ORB only QQQ SIP GET data allowed')
        return super().request(origin,path,method,params=params)


def utcnow():return pd.Timestamp(datetime.now(timezone.utc))


def cycle(db,data,now=utcnow):
    logical=pd.Timestamp(now()).tz_convert('America/New_York')-pd.Timedelta(minutes=16);clock_day=str(logical.date());a=db.get_account()
    date=a['open_day'] or clock_day;s=session_for(date);d=db.day(date)
    if s is None:return dict(state='waiting_non_session')
    if logical<s.open+pd.Timedelta(minutes=5):return dict(state='waiting_opening')
    if d and d['phase'] in ('closed','flat','skipped','unresolved'):return dict(state=d['phase'],reason=d.get('reason'))
    if logical>s.open+pd.Timedelta(minutes=7) and not (d or {}).get('entry_done'):
        frame=pd.DataFrame(columns=['open','high','low','close','volume'],index=pd.DatetimeIndex([],tz='UTC'))
    else:
        frame=data.bars(s.open,min(logical.floor('min'),s.close),'sip')
        logical=pd.Timestamp(now()).tz_convert('America/New_York')-pd.Timedelta(minutes=16)
        if str(logical.date())!=clock_day:raise RuntimeError('date changed during fetch')
    a,d=db.tick(s,frame,logical)
    return dict(state=d['phase'],logical_asof=str(logical),fully_observed=d['fully_observed'],notes=d['notes'])


def first_session(now):
    logical=pd.Timestamp(now).tz_convert('America/New_York')-pd.Timedelta(minutes=16)
    for j in range(12):
        day=str((logical+pd.Timedelta(days=j)).date());s=session_for(day)
        if s and logical<=s.open+pd.Timedelta(minutes=7):return day
    raise RuntimeError('no upcoming session')


def probe(data):
    end=utcnow()-pd.Timedelta(minutes=16);f=data.bars(end-pd.Timedelta(days=7),end,'sip')
    if f.empty:raise ValueError('empty historical SIP probe')
    return dict(state='read_only_sip_connected',symbol='QQQ',rows=len(f),utc=str(utcnow()),broker_orders=False,credentials_printed=False)


def pause(stop,seconds):
    until=time.monotonic()+seconds
    while not stop.exists() and time.monotonic()<until:time.sleep(min(1,max(0,until-time.monotonic())))


def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument('--runtime',type=Path,default=Path('runtime'));p.add_argument('--check',action='store_true');a=p.parse_args(argv)
    root=a.runtime.resolve();root.mkdir(parents=True,exist_ok=True);stop=root/'STOP_SHADOW.flag';verify_model()
    log=logging.getLogger('orb_shadow');log.setLevel(logging.INFO);log.propagate=False
    handler=RotatingFileHandler(root/'background.log',maxBytes=2000000,backupCount=5,encoding='utf-8');handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'));log.addHandler(handler)
    try:
        power=PowerGuard(root);power.logger=log
        with ProcessLock(root/'background.lock'),(nullcontext() if a.check else power):
            while not stop.exists():
                transport=None
                try:
                    key,secret=WindowsVault().load();transport=ReadOnlyTransport(key,secret);del key,secret;data=DataClient(transport)
                    write_status(root,state='checking_connection',mode='shadow',feed='sip',pid=os.getpid(),utc=str(utcnow()))
                    connected=probe(data)
                    (root/'connection.json').write_text(json.dumps(connected,indent=2),encoding='utf-8')
                    if a.check:print(json.dumps(connected));return 0
                    with Ledger(root/'state.sqlite') as db:
                        db.record_restart()
                        if db.get('first_session') is None:
                            with db.db:db.put('first_session',first_session(utcnow()))
                        log.info('QQQ ORB local simulation started; data-only GET; no broker orders')
                        while not stop.exists():
                            try:
                                fields=cycle(db,data);acct=db.get_account();write_status(root,**fields,mode='shadow',feed='sip',delay_minutes=16,pid=os.getpid(),utc=str(utcnow()),balance=acct['balance'],marked_equity=acct['marked_equity'],open_day=acct['open_day'])
                            except Exception as error:
                                write_status(root,state='error_no_new_entries',error_type=type(error).__name__,api_status=getattr(error,'status',None),network_reason=network_failure_code(error) if isinstance(error,(ConnectionError,TimeoutError)) else None,mode='shadow',feed='sip',pid=os.getpid(),utc=str(utcnow()))
                                log.error('Cycle interrupted: %s; network_reason=%s; credential values omitted',type(error).__name__,network_failure_code(error) if isinstance(error,(ConnectionError,TimeoutError)) else None)
                            pause(stop,5)
                except Exception as error:
                    write_status(root,state='startup_retry',error_type=type(error).__name__,api_status=getattr(error,'status',None),network_reason=network_failure_code(error) if isinstance(error,(ConnectionError,TimeoutError)) else None,mode='shadow',feed='sip',pid=os.getpid(),utc=str(utcnow()))
                    log.error('Startup retry in 60s: %s; network_reason=%s; credential values omitted',type(error).__name__,network_failure_code(error) if isinstance(error,(ConnectionError,TimeoutError)) else None)
                    if a.check:return 1
                    pause(stop,60)
                finally:
                    if transport:transport.clear()
            write_status(root,state='stopped',mode='shadow',feed='sip',pid=os.getpid(),utc=str(utcnow()))
            return 0
    finally:log.removeHandler(handler);handler.close()


if __name__=='__main__':raise SystemExit(main())
