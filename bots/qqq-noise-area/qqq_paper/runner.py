"""Ordres paper idempotents ; les retournements ferment avant de rouvrir."""
import time
import pandas as pd
from .alpaca import APIError,OrderNotSent
from .strategy import signal,day_size,decision_times


class PendingOrder(Exception):pass


def paper_due(now,decision):
    elapsed=(pd.Timestamp(now)-pd.Timestamp(decision)).total_seconds()
    return 0<=elapsed<=20


class Executor:
    def __init__(self,store,broker,wait_seconds=15,sleep=time.sleep):
        self.store=store;self.broker=broker;self.wait_seconds=wait_seconds;self.sleep=sleep
    @staticmethod
    def cid(day,clock,action,sign):
        return f'naqqq-{day.replace("-","")}-{clock.replace(":","")}-{action[0]}{"b" if sign==1 else "s"}'
    def reconcile(self,cancel_open=False):
        for intent in self.store.pending():
            snapshot=self.broker.get_order(intent['cid'])
            if snapshot is None:raise PendingOrder('prepared order not found; no blind resend')
            self.store.apply(snapshot)
            if cancel_open and snapshot['status'] not in ('filled','canceled','expired','rejected') and snapshot.get('id'):
                self.broker.cancel(snapshot['id']);snapshot=self.broker.get_order(intent['cid'])
                if snapshot is None:raise PendingOrder('cancel not confirmed')
                self.store.apply(snapshot)
            if snapshot['status'] not in ('filled','canceled','expired','rejected'):raise PendingOrder('paper order remains pending')
    def execute(self,day,clock,action,sign,qty):
        cid=self.cid(day,clock,action,sign)
        prior=self.store.order(cid)
        # This read precedes persistence: failure here cannot mean a POST was sent.
        first_snapshot=self.broker.get_order(cid) if prior is None else None
        if prior is None and first_snapshot is not None:raise ValueError('order id exists outside this state; refusing adoption')
        fresh=self.store.intent(cid,day,action,sign,qty,clock)
        old=self.store.order(cid)
        if old['status']=='filled':return True
        if old['status'] in ('canceled','expired','rejected'):return False
        snapshot=first_snapshot if fresh else self.broker.get_order(cid)
        if snapshot is None:
            if not fresh:raise PendingOrder('prepared order not found; no blind resend')
            try:snapshot=self.broker.submit(cid,action,sign,qty)
            except OrderNotSent:
                self.store.apply(dict(client_order_id=cid,filled_qty='0',filled_avg_price=None,status='rejected'));return False
            except APIError as e:
                if e.status in (400,401,403,422):
                    self.store.apply(dict(client_order_id=cid,filled_qty='0',filled_avg_price=None,status='rejected'));return False
                snapshot=self.broker.get_order(cid)
            except (TimeoutError,ConnectionError):snapshot=self.broker.get_order(cid)
        if snapshot is None:raise PendingOrder('ambiguous order send; lookup required')
        deadline=time.monotonic()+self.wait_seconds
        while True:
            self.store.apply(snapshot)
            if snapshot['status']=='filled':return True
            if snapshot['status'] in ('canceled','expired','rejected'):return False
            if time.monotonic()>=deadline:break
            self.sleep(.5);snapshot=self.broker.get_order(cid)
            if snapshot is None:raise PendingOrder('accepted order not found')
        if snapshot.get('id'):self.broker.cancel(snapshot['id'])
        for _ in range(5):
            snapshot=self.broker.get_order(cid)
            if snapshot is not None:
                self.store.apply(snapshot)
                if snapshot['status']=='filled':return True
                if snapshot['status'] in ('canceled','expired','rejected'):return False
            self.sleep(.5)
        raise PendingOrder('cancel outcome uncertain; new entries suspended')
    def target(self,target,quantity,day,clock):
        if target not in (-1,0,1):raise ValueError('target')
        side=1 if self.store.position>0 else -1 if self.store.position<0 else 0
        if side==target:return True
        if side:
            if not self.execute(day,clock,'close',-side,abs(self.store.position)):return False
            if self.store.position:raise PendingOrder('close not complete')
        if target:return self.execute(day,clock,'open',target,quantity)
        return True


class Controller:
    def __init__(self,store,executor=None,mode='shadow'):
        if mode=='paper' and executor is None:raise ValueError('paper executor required')
        self.store=store;self.executor=executor;self.mode=mode
    def reconcile_live(self,closing=False):
        self.executor.reconcile(cancel_open=closing)
        b=self.executor.broker
        external=[o for o in b.open_orders() if self.store.order(o.get('client_order_id','')) is None]
        if external or b.position()!=self.store.position:
            self.store.pause('external position/order mismatch');raise ValueError('external QQQ position/order mismatch')
    def _target(self,target,quantity,day,clock,reference,at):
        if self.mode=='paper':
            ok=self.executor.target(target,quantity,day,clock)
            if not ok:self.store.pause('order rejected or partial; no new entries')
            return ok
        side=1 if self.store.position>0 else -1 if self.store.position<0 else 0
        if target==side:return True
        actions=[]
        if side:actions.append(('close',-side,abs(self.store.position)))
        if target:actions.append(('open',target,quantity))
        for action,direction,qty in actions:
            cid='shadow-'+Executor.cid(day,clock,action,direction)
            self.store.intent(cid,day,action,direction,int(qty),clock)
            self.store.apply(dict(client_order_id=cid,id=cid,filled_qty=str(qty),filled_avg_price=str(reference),status='filled',filled_at=str(at)))
        return True
    def _flatten_paper(self,day,now):
        if not self.store.position:return
        self.executor.reconcile(cancel_open=True)
        if not self.store.pending():
            self._target(0,0,day,'flat'+now.strftime('%H%M%S'),0.,now)
    def must_flatten(self,session,asof):
        day=str(session.open.tz_convert('America/New_York').date())
        return self.mode=='paper' and (asof>=session.flatten or bool(self.store.get('paused')) or
            self.store.get('paused_day')==day or bool(self.store.position and self.store.position_day!=day))
    def step(self,history,frame,session,asof,dividend=0.):
        asof=pd.Timestamp(asof);day=str(session.open.tz_convert('America/New_York').date())
        if asof<session.open:return
        if self.mode=='shadow' and self.store.position and self.store.position_day!=day:
            self.store.pause('shadow position from prior session; reconstruct missed decisions before continuing')
            raise ValueError('shadow position from prior session; replay required before continuing')
        if self.mode=='paper' and self.store.position and self.store.position_day!=day:
            self.store.pause('inherited overnight position; close first and inspect before resuming')
        if self.must_flatten(session,asof):
            self._flatten_paper(day,asof);return
        for at in decision_times(session):
            if at>asof:break
            key=f'{day}:{at.strftime("%H%M")}'
            if self.store.recorded(key):continue
            if self.mode=='shadow' and at+pd.Timedelta(minutes=1)>asof:continue
            if self.mode=='paper' and not paper_due(asof,at):
                self.store.record(key,dict(status='skipped_late',decision_time=str(at)))
                if self.store.position or self.store.get('awaiting_slot')==key:
                    with self.store.db:self.store.put('paused_day',day)
                    self._flatten_paper(day,asof);return
                continue
            if self.store.get('paused_day')==day or self.store.get('paused'):continue
            if self.mode=='paper' and isinstance(frame.index,pd.DatetimeIndex) and frame.index.tz is not None:
                wanted=pd.date_range(session.open,at,inclusive='left',freq='min')
                missing=wanted.difference(frame.index)
                if len(missing)==1 and missing[0]==at-pd.Timedelta(minutes=1):
                    with self.store.db:self.store.put('awaiting_slot',key)
                    continue
            side=1 if self.store.position>0 else -1 if self.store.position<0 else 0
            try:
                x=signal(history,frame,session,at,side,dividend)
                size=self.store.set_day(day,day_size(self.store.balance,x.opening,x.volatility),x.opening,x.volatility)
                quantity=int(size['quantity'])
                if quantity<=0:raise ValueError('zero day quantity')
                reference=float(frame.loc[at,'open']) if self.mode=='shadow' else x.price
                if not pd.notna(reference) or reference<=0:raise ValueError('next open unavailable')
            except (ValueError,KeyError) as error:
                with self.store.db:self.store.put('paused_day',day)
                self.store.record(key,dict(status='data_unavailable',reason=str(error),decision_time=str(at)))
                if self.mode=='paper':self._flatten_paper(day,asof)
                break
            ok=self._target(x.target,quantity,day,at.strftime('%H%M'),reference,at)
            self.store.record(key,dict(status='processed' if ok else 'partial_or_rejected',**vars(x),quantity=quantity,observed_at=str(asof)))
            if not ok:break
        if self.mode=='shadow' and asof>=session.close and self.store.position:
            try:reference=float(frame.loc[session.flatten,'open'])
            except KeyError:raise ValueError('last minute open missing; shadow position remains open') from None
            self._target(0,0,day,'flatten',reference,session.flatten)
