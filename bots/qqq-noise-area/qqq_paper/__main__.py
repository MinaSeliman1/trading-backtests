"""Lanceur local : simulation SIP différée ou ordres Alpaca PAPER QQQ."""
import argparse
from contextlib import ExitStack
import getpass
import os
from pathlib import Path
import sys
import time
from datetime import datetime,timezone
import pandas as pd
from .strategy import Parameters,verify_frozen_strategy
from .ledger import Store
from .alpaca import Transport,PaperBroker,DataClient,APIError
from .runtime import ProcessLock,session_for,load_history,write_status
from .runner import Controller,Executor,PendingOrder


def arguments(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mode',choices=['paper','shadow'],default='shadow')
    p.add_argument('--feed',choices=['sip','iex'],default='sip')
    p.add_argument('--runtime',type=Path,default=Path('runtime'))
    p.add_argument('--prompt',action='store_true',help='Saisie masquée des clés PAPER en mémoire seulement.')
    p.add_argument('--check',action='store_true',help='Connexion et lecture uniquement, aucun ordre.')
    p.add_argument('--once',action='store_true')
    p.add_argument('--poll-seconds',type=float,default=5.)
    a=p.parse_args(argv)
    if not 1<=a.poll_seconds<=60:p.error('poll-seconds must be between 1 and 60')
    return a


def preflight(broker,store):
    account=broker.account()
    if account.get('status')!='ACTIVE' or account.get('trading_blocked') or account.get('account_blocked'):
        raise ValueError('paper account inactive or blocked')
    if float(account['equity'])<=0:raise ValueError('paper account has no equity')
    existing=store.get('paper_account_id')
    if existing is not None and existing!=account['id']:raise ValueError('paper account does not match existing state')
    if existing is None:
        if float(account['equity'])<store.parameters.initial_capital:raise ValueError('paper account requires at least 100000 USD initial equity')
        with store.db:store.put('paper_account_id',account['id'])
    return account


def main(argv=None):
    a=arguments(argv);a.runtime.mkdir(parents=True,exist_ok=True);verify_frozen_strategy()
    folder=a.runtime/(a.mode+'-'+a.feed);folder.mkdir(parents=True,exist_ok=True)
    key=os.environ.get('ALPACA_PAPER_KEY_ID','');secret=os.environ.get('ALPACA_PAPER_SECRET_KEY','')
    if a.prompt:
        print('QQQ NOISE AREA — ALPACA PAPER UNIQUEMENT',flush=True)
        print('Cles du compte PAPER ; saisie masquee ; aucune sauvegarde des cles.',flush=True)
        print(f'Mode {a.mode} / flux {a.feed}. IEX differe du backtest SIP.',flush=True)
        key=getpass.getpass('Paper API Key ID : ').strip();secret=getpass.getpass('Paper API Secret : ').strip()
    if not key or not secret:
        write_status(folder,state='awaiting_paper_credentials',mode=a.mode,feed=a.feed)
        print('Cles PAPER absentes. Utiliser --prompt dans une console interactive ; ne pas envoyer les cles dans le chat.',flush=True)
        return 2
    if any(ch in key+secret for ch in '\r\n\x00'):raise ValueError('credentials contain control characters')
    transport=Transport(key,secret);del key,secret
    broker=PaperBroker(transport);data=DataClient(transport);store=None;controller=None;resources=ExitStack()
    try:
        resources.enter_context(ProcessLock(a.runtime/('paper.lock' if a.mode=='paper' else 'shadow-'+a.feed+'.lock')))
        store=Store(folder/'state.sqlite',Parameters(),a.mode,a.feed);preflight(broker,store)
        executor=Executor(store,broker) if a.mode=='paper' else None
        controller=Controller(store,executor,a.mode)
        clock=broker.clock();now=pd.Timestamp(clock['timestamp']).tz_convert('America/New_York')
        if a.check:
            probe=data.bars(now-pd.Timedelta(days=2),now-pd.Timedelta(minutes=16),'sip')
            write_status(folder,state='connection_checked_no_orders',mode=a.mode,feed=a.feed,read_only=True,
                         historical_sip_rows=len(probe),market_open=bool(clock['is_open']),checked_utc=datetime.now(timezone.utc).isoformat())
            print('Connexion PAPER et historique SIP verifies ; aucun ordre envoye.',flush=True);return 0
        print('Bot demarre. Ctrl+C suspend les entrees et tente de fermer la position geree si le marche est ouvert.',flush=True)
        history=None;loaded_day=None;dividend=0.;last_note=None;recovering=True
        while True:
            try:
                clock=broker.clock();now=pd.Timestamp(clock['timestamp']).tz_convert('America/New_York')
                day=str(now.date());session=session_for(day)
                if a.mode=='paper':
                    had_pending=bool(store.pending())
                    closing=bool(session and now>=session.flatten) or bool(store.get('paused')) or recovering
                    controller.reconcile_live(closing=closing)
                    if recovering and had_pending:store.pause('restarted with an unresolved order; flatten and inspect')
                    recovering=False
                if session is None or now<session.open:
                    state='waiting_for_regular_session'
                elif a.mode=='paper' and controller.must_flatten(session,now):
                    controller.step(None,pd.DataFrame(),session,now);state='flat_after_session' if store.position==0 else 'ALERT_position_open'
                else:
                    if loaded_day!=day:
                        history=load_history(data,session,folder,a.feed);dividend=data.dividend(day)
                        if a.mode=='paper':
                            calendar=broker.calendar(day)
                            if len(calendar)!=1 or calendar[0]['open']!=session.open.strftime('%H:%M') or calendar[0]['close']!=session.close.strftime('%H:%M'):
                                raise ValueError('broker/NYSE calendar mismatch')
                        loaded_day=day
                    asof=(now-pd.Timedelta(minutes=16)).floor('min') if a.mode=='shadow' else now
                    end=min(asof.floor('min'),session.close)
                    if end>session.open:
                        bars=data.bars(session.open,end,a.feed)
                        controller.step(history,bars,session,asof,dividend)
                    state='paused' if store.get('paused') or store.get('paused_day')==day else 'running'
                status=dict(state=state,mode=a.mode,feed=a.feed,utc=datetime.now(timezone.utc).isoformat(),
                            managed_qty=store.position,net_realized_equity=store.balance,model_extra_friction_per_share=.01,
                            note='IEX est distinct du backtest SIP' if a.feed=='iex' else 'SIP shadow retarde de 16 minutes' if a.mode=='shadow' else 'SIP paper temps reel requis')
                write_status(folder,**status);store.export(folder)
                note=(day,state,store.position)
                if note!=last_note:print(f'{now}: {state} ; QQQ={store.position} ; compte net realise={store.balance:.2f}',flush=True);last_note=note
            except (APIError,ConnectionError,ValueError,PendingOrder) as error:
                reason=str(error) if isinstance(error,(APIError,ValueError,PendingOrder)) else type(error).__name__
                write_status(folder,state='error_no_new_entries',mode=a.mode,feed=a.feed,reason=reason,
                             managed_qty=store.position,utc=datetime.now(timezone.utc).isoformat())
                print(f'Entrees suspendues : {reason}',flush=True)
                if a.mode=='paper' and store.position:
                    try:
                        controller.reconcile_live(closing=True)
                        if broker.clock()['is_open']:controller._flatten_paper(str(now.date()),now)
                    except (APIError,ConnectionError,ValueError,PendingOrder):pass
                if a.once:return 1
            if a.once:return 0
            time.sleep(a.poll_seconds)
    except KeyboardInterrupt:
        if store and controller is not None and a.mode=='paper' and not a.check:
            store.pause('operator stopped bot')
            try:
                controller.reconcile_live(closing=True)
                stop_clock=broker.clock()
                stop_time=pd.Timestamp(stop_clock['timestamp']).tz_convert('America/New_York')
                if stop_clock['is_open']:controller._flatten_paper(str(stop_time.date()),stop_time)
            except (APIError,ConnectionError,ValueError,PendingOrder):pass
        if store:write_status(folder,state='stopped',mode=a.mode,feed=a.feed,managed_qty=store.position)
        print('Arrete. Verifier QQQ dans le compte paper si managed_qty est non nul.',flush=True);return 0
    except (APIError,ConnectionError,ValueError,RuntimeError,PendingOrder) as error:
        reason=str(error) if isinstance(error,(APIError,ValueError,RuntimeError,PendingOrder)) else type(error).__name__
        write_status(folder,state='startup_failed',mode=a.mode,feed=a.feed,reason=reason)
        print(f'Demarrage non termine : {reason}',flush=True);return 1
    finally:
        if store:store.close()
        transport.clear()
        resources.close()


if __name__=='__main__':sys.exit(main())
