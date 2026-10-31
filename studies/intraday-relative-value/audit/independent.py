"""Independent scalar pair replay. No calls to strategy or statistics functions."""
from pathlib import Path
from decimal import Decimal,ROUND_FLOOR
from types import SimpleNamespace
from datetime import datetime,timezone
import argparse,json,math,hashlib,sys
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from relative.data import load_sources
D=lambda x:Decimal(str(x))

def ok(x):return math.isfinite(float(x)) and x>0

def residual(m,i,j):
 q,s=m['QQQ'].arrays,m['SPY'].arrays
 values=[q['close'][i,j],q['open'][i,0],s['close'][i,j],s['open'][i,0]]
 return math.log(values[0]/values[1])-math.log(values[2]/values[3]) if all(ok(x) for x in values) else math.nan

def histories(m,w):
 q,s=m['QQQ'],m['SPY'];result=[];past=[]
 for i in range(len(q.dates)):
  current={j:residual(m,i,j) for j in range(29,min(300,int(q.lengths[i])),5)}
  reason='warmup' if i<w else 'unknown_history' if any(not q.valid[k] or not s.valid[k] for k in range(i-w,i)) else 'ready'
  stats={}
  if reason=='ready':
   for j in range(29,300,5):
    values=[past[k][j] for k in range(i-w,i) if j<int(q.lengths[k])]
    if len(values)<math.ceil(.75*w) or not all(math.isfinite(v) for v in values):stats[j]=(math.nan,math.nan)
    else:
     mu=math.fsum(values)/len(values);sd=math.sqrt(math.fsum((v-mu)**2 for v in values)/(len(values)-1));stats[j]=(mu,sd)
  result.append((reason,stats));past.append(current)
 return result

def replay_day(m,i,c,capital,hist):
 n=int(m['QQQ'].lengths[i]);reason,stats=hist;order=None;pair=None;legs=[];unknown=None;marks=[capital]
 if reason=='ready':
  reason='no_signal'
  if not all(ok(m[s].arrays['open'][i,0]) for s in ['QQQ','SPY']):reason='unknown_anchor'
  else:
   for j in range(29,min(299,n-2-int(c.delay))+1,5):
    mu,sd=stats[j]
    if not math.isfinite(mu) or not math.isfinite(sd):reason='unknown_history';break
    if sd<=1e-8:continue
    x=residual(m,i,j)
    if not math.isfinite(x):reason='unknown_signal';break
    z=(x-mu)/sd
    if abs(z)<c.entry_z-1e-12 or abs(z)>=c.stop_z-1e-12:continue
    sign=1 if z<0 else -1
    if c.direction=='long_spread_only' and sign<0 or c.direction=='short_spread_only' and sign>0:continue
    pq=float(m['QQQ'].arrays['close'][i,j]);ps=float(m['SPY'].arrays['close'][i,j]);distance=D(sd)*(D(c.stop_z)-abs(D(z)))
    budget=min(D(capital)*D(c.leverage_cap)/2,D(capital)*D(c.risk_budget)/distance)
    qq=int((budget/D(pq)).to_integral_value(rounding=ROUND_FLOOR));qs=int((budget/D(ps)).to_integral_value(rounding=ROUND_FLOOR))
    if min(qq,qs)<=0:reason='zero_quantity';continue
    notion=qq*pq+qs*ps;fees=2*(max(.35,qq*.0035)+max(.35,qs*.0035));friction=2*c.slippage*(qq+qs)
    sq,sp=(qs,ps) if sign>0 else (qq,pq);anticipated=fees+friction+sq*max(0,sp-c.slippage)*.01/360;expected=notion/2*abs(x-mu)
    if c.cost_gate and expected<2*anticipated:reason='cost_filtered';continue
    order=dict(sign=sign,signal_slot=j,entry_slot=j+int(c.delay),z=z,mean=mu,sd=sd,stop_spread=mu-sign*c.stop_z*sd,quantity_qqq=qq,quantity_spy=qs,sizing_qqq=pq,sizing_spy=ps,gross_sizing=notion,proxy_risk_usd=notion/2*float(distance),anticipated_cost=anticipated,expected_reversion_gross=expected);reason='eligible';break
 if capital<=0:reason='insolvent'
 if reason=='eligible' and c.quality=='complete_days' and not (m['QQQ'].valid[i] and m['SPY'].valid[i]):reason='excluded_incomplete_day'
 if reason=='eligible':
  left=order['entry_slot'];sign=order['sign'];qq,qs=order['quantity_qqq'],order['quantity_spy'];quantities={'QQQ':qq,'SPY':qs};side={'QQQ':sign,'SPY':-sign}
  refs={s:float(m[s].arrays['open'][i,left]) for s in side};fills={s:refs[s]+side[s]*c.slippage for s in side}
  known=dict(known_entry_commission=0.,known_entry_friction=0.,known_borrow=0.,entry_legs_known=0)
  for s in side:
   if ok(refs[s]):
    known['known_entry_commission']+=max(.35,quantities[s]*.0035);known['known_entry_friction']+=quantities[s]*c.slippage;known['entry_legs_known']+=1
    if side[s]<0:known['known_borrow']+=quantities[s]*max(0,fills[s])*.01/360
  missing=None;exit_slot=n-1;exit_reason='eod_open'
  if not all(ok(v) for v in refs.values()):missing=('missing_entry_open',left)
  else:
   for j in range(left,n-1):
    x=residual(m,i,j)
    if not math.isfinite(x):missing=('missing_active_close',j);break
    is_stop=sign*(x-order['mean'])<=-c.stop_z*order['sd'];is_mean=sign*(x-order['mean'])>=0
    if is_stop or is_mean:
     exit_slot=min(j+int(c.delay),n-1);exit_reason='eod_open' if j+int(c.delay)>n-1 else 'spread_stop' if is_stop else 'mean_cross';break
  price_marks=[-known['known_entry_friction']]
  if missing is None:
   for j in range(left,exit_slot):
    closes={s:float(m[s].arrays['close'][i,j]) for s in side}
    if not all(ok(v) for v in closes.values()):missing=('missing_active_close',j);break
    price_marks.append(sum(quantities[s]*side[s]*(closes[s]-fills[s]) for s in side))
  if missing is None:
   exits={s:float(m[s].arrays['open'][i,exit_slot]) for s in side}
   if not all(ok(v) for v in exits.values()):missing=('missing_exit_open',exit_slot)
  if missing:
   unknown=dict(reason=missing[0],first_unknown_slot=missing[1],sign=sign,quantity_qqq=qq,quantity_spy=qs,**known);reason='unresolved_execution'
  else:
   for s in ['QQQ','SPY']:
    qty=quantities[s];fee=2*max(.35,qty*.0035);f=2*qty*c.slippage;b=qty*fills[s]*.01/360 if side[s]<0 else 0.;move=qty*side[s]*(exits[s]-refs[s]);gross=move-f;net=gross-fee-b
    legs.append(dict(symbol=s,side=side[s],quantity=qty,entry_reference=refs[s],exit_reference=exits[s],entry_price=fills[s],exit_price=exits[s]-side[s]*c.slippage,price_move_pnl=move,friction_cost=f,commission=fee,borrow_fee=b,gross_pnl=gross,net_pnl=net))
   totals={k:sum(x[k] for x in legs) for k in ['price_move_pnl','friction_cost','commission','borrow_fee','gross_pnl','net_pnl']}
   price_marks.append(totals['gross_pnl']);open_time=pd.Timestamp(m['QQQ'].quality.iloc[i].session_open)
   pair=dict(**order,**totals,exit_slot=exit_slot,exit_reason=exit_reason,entry_time=str(open_time+pd.Timedelta(minutes=left)),exit_time=str(open_time+pd.Timedelta(minutes=exit_slot)),
    entry_reference_qqq=refs['QQQ'],entry_reference_spy=refs['SPY'],exit_reference_qqq=exits['QQQ'],exit_reference_spy=exits['SPY'],gross_entry_reference=qq*refs['QQQ']+qs*refs['SPY'],gross_entry_fill=qq*fills['QQQ']+qs*fills['SPY'],
    holding_minutes=exit_slot-left,mae_price_usd=min(0.,min(price_marks)),mfe_price_usd=max(0.,max(price_marks)),equity_before=capital,equity_after=capital+totals['net_pnl'])
   pair['entry_leverage']=pair['gross_entry_reference']/capital;pair['entry_fill_leverage']=pair['gross_entry_fill']/capital;pair['proxy_risk_pct']=order['proxy_risk_usd']/capital*100
   marks += [capital-known['known_entry_commission']-known['known_borrow']+v for v in price_marks[:-1]]+[pair['equity_after']]
 return dict(reason=reason,sign=order['sign'] if order else 0,pair=pair,legs=legs,unknown=unknown,marks=marks)

def near(a,b):
 if b is None:return pd.isna(a)
 if isinstance(b,(str,bool)):return a==b
 return math.isclose(float(a),float(b),rel_tol=1e-9,abs_tol=2e-6)

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=ROOT/'results/2026-10-31-v1');out=p.parse_args().out.resolve();frozen=json.loads((out/'PRE_EXECUTION_PROTOCOL.json').read_text(encoding='utf-8'));matrix=pd.read_csv(out/'comparison_all.csv')
 expected={f'{p}_{v}' for p in frozen['periods'] for v in frozen['specifications']};assert len(matrix)==42 and set(matrix.label)==expected and matrix.label.is_unique
 markets,_,_=load_sources();h={w:histories(markets,w) for w in [10,20,40]};lookup={str(v.date()):i for i,v in enumerate(markets['QQQ'].dates)};checks=1;failures=[];pairs=days=legs_count=0
 def check(test,label):
  nonlocal checks
  checks+=1
  if not test and len(failures)<30:failures.append(label)
 for cfg in matrix.itertuples():
  for k,v in frozen['specifications'][cfg.variant].items():check(near(getattr(cfg,k),v),cfg.label+' config '+k)
  check([cfg.start,cfg.end]==frozen['periods'][cfg.period],cfg.label+' boundaries')
  summary=json.loads((out/cfg.label/'summary.json').read_text());check(set(summary)==set(matrix.columns),cfg.label+' summary schema')
  for k,v in summary.items():check(near(getattr(cfg,k),v),cfg.label+' summary '+k)
  d=pd.read_csv(out/cfg.label/'daily.csv');t=pd.read_csv(out/cfg.label/'trades.csv');l=pd.read_csv(out/cfg.label/'legs.csv');u=pd.read_csv(out/cfg.label/'unresolved.csv')
  td={x.date:x for x in t.itertuples()};ud={x.date:x for x in u.itertuples()};check(len(td)==len(t) and len(ud)==len(u),cfg.label+' unique dates')
  check(d.date.tolist()==[v for v in lookup if cfg.start<=v<=cfg.end],cfg.label+' full expected calendar')
  capital=100000.;peak=capital;dd=ddusd=0.;expected_t=set();expected_u=set()
  for day in d.itertuples():
   days+=1;i=lookup[day.date];before=capital;r=replay_day(markets,i,cfg,capital,h[int(cfg.lookback)][i]);check(day.eligibility==r['reason'],cfg.label+' '+day.date+' eligibility');check(day.signal_sign==r['sign'],cfg.label+' side')
   excluded=r['reason'].startswith('unknown_') or r['reason'] in ['excluded_incomplete_day','unresolved_execution'];check(bool(day.conditionally_excluded)==excluded,'exclusion')
   pair=r['pair'];net=0.;fees=borrow=friction=held=0.
   if pair:
    expected_t.add(day.date);pairs+=1;check(day.date in td,cfg.label+' missing pair '+day.date)
    if day.date in td:
     for k,v in pair.items():check(near(getattr(td[day.date],k),v),cfg.label+' '+day.date+' pair '+k)
    capital=pair['equity_after'];net=pair['net_pnl'];fees=pair['commission'];borrow=pair['borrow_fee'];friction=pair['friction_cost'];held=pair['holding_minutes']
    exported=l[l.date==day.date];check(len(exported)==2 and set(exported.symbol)=={'QQQ','SPY'},'exact leg membership')
    for leg in r['legs']:
     rows=exported[exported.symbol==leg['symbol']];legs_count+=1
     if len(rows)==1:
      for k,v in leg.items():check(near(rows.iloc[0][k],v),'leg '+k)
   if r['unknown']:
    expected_u.add(day.date);check(day.date in ud,'missing unresolved')
    if day.date in ud:
     for k,v in r['unknown'].items():check(near(getattr(ud[day.date],k),v),'unknown '+k)
   for key,value in dict(net_pnl=net,equity=capital,trades=int(pair is not None),commission=fees,borrow_fee=borrow,friction_cost=friction,holding_minutes=held,return_net=net/before if before>0 else 0.).items():check(near(getattr(day,key),value),'daily '+key)
   check(pd.isna(day.observed_return) if excluded else near(day.observed_return,day.return_net),'observed/missing return')
   for v in r['marks']:peak=max(peak,v);dd=max(dd,(peak-v)/peak*100);ddusd=max(ddusd,peak-v)
   check(near(day.observed_drawdown_pct_so_far,dd),'daily drawdown')
  check(set(td)==expected_t and set(ud)==expected_u,'exact export membership');check(len(l)==2*len(t),'leg count')
  check(near(cfg.final_equity,capital) and near(cfg.net_pnl,capital-100000),'net/final');check(near(cfg.total_return_pct,(capital/100000-1)*100),'return')
  years=((pd.Timestamp(d.date.iloc[-1])-pd.Timestamp(d.date.iloc[0])).days+1)/365.2425;check(near(cfg.cagr_pct,((capital/100000)**(1/years)-1)*100),'CAGR')
  check(near(cfg.observed_drawdown_pct,dd) and near(cfg.observed_drawdown_usd,ddusd),'drawdown');check(cfg.pairs==len(t) and cfg.leg_trades==len(l),'summary counts')
  gains=t.loc[t.net_pnl>0,'net_pnl'].sum();loss=-t.loc[t.net_pnl<0,'net_pnl'].sum()
  if loss:check(near(cfg.profit_factor,gains/loss),'profit factor')
  if len(t):check(near(cfg.win_rate_pct,(t.net_pnl>0).mean()*100),'win rate')
  for k in ['price_move_pnl','friction_cost','commission','borrow_fee']:check(near(getattr(cfg,k),t[k].sum()),'cost '+k)
  for s in ['QQQ','SPY']:check(near(getattr(cfg,s+'_net_contribution_usd'),l.loc[l.symbol==s,'net_pnl'].sum()),'leg contribution')
  rr=d.return_net.copy();rr.loc[d.loc[d.net_pnl>0].nlargest(3,'net_pnl').index]=0;check(near(cfg.return_without_top3_days_pct,((1+rr).prod()-1)*100),'top3 ablation')
  print(cfg.label+' audited',flush=True)
 sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();paths=[out/'comparison_all.csv',out/'PRE_EXECUTION_PROTOCOL.json',*[out/label/name for label in matrix.label for name in ['daily.csv','trades.csv','legs.csv','unresolved.csv','summary.json']]]
 result=dict(utc=datetime.now(timezone.utc).isoformat(),status='passed' if not failures else 'failed',scenarios=42,pair_rows=pairs,leg_rows=legs_count,daily_rows=days,checks=checks,failures=failures,run_id=out.relative_to(ROOT).as_posix(),scope='Independent scalar features/decisions/two-leg fills/four fees/borrow/equity/drawdown replay. Shared verified source loader, not second feed. Rows overlap across scenarios.',export_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in paths})
 (ROOT/'audit/AUDIT_RESULTS.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k!='export_sha256'}))
 if failures:raise SystemExit(1)
if __name__=='__main__':main()
