"""Independent scalar oracle: imports no trading engine, context or statistics."""
from pathlib import Path
import sys,json,datetime,math
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from smt.data import ROOT,load_sources,sha
O=ROOT/'results'

def plan(a,lev,model,side,slot,friction):
 start=slot-10 if model=='H1' else 330
 stop=min(a['low'][start:slot])-.25 if side==1 else max(a['high'][start:slot])+.25
 estimated=float(a['close'][slot-1])+side*.25*friction;risk=side*(estimated-stop)
 p=dict(status='eligible',side=side,entry_slot=slot,stop=stop,target=None,estimated_entry=estimated,estimated_risk=risk,estimated_rr=2.,target_level=None,model=model)
 if risk<=0:p['status']='invalid_estimated_risk';return p
 if model=='H1':
  p['status']='no_target';p['estimated_rr']=None
  for v in lev:
   target=v['NQ']['high' if side==1 else 'low']
   if side*(target-estimated)>1e-10:
    p.update(target=target,target_level=v['name'],estimated_rr=side*(target-estimated)/risk);p['status']='eligible' if p['estimated_rr']>=1-1e-10 else 'rr_below1';break
 return p

def fill(a,p,friction):
 side=p['side'];slot=p['entry_slot'];slip=.25*friction;raw=float(a['open'][slot]);entry=raw+side*slip;stop=p['stop'];risk=abs(entry-stop)
 target=p['target'] if p['model']=='H1' else entry+side*2*max(0.,side*(entry-stop))
 for j in range(slot,451):
  op=float(a['open'][j]);amb=False
  if (op<=stop if side==1 else op>=stop):ref=op;why='entry_marketable_stop' if j==slot else 'stop_gap';resolution='bar_open'
  elif (op>=target if side==1 else op<=target):ref=op;why='entry_marketable_target' if j==slot else 'target_gap';resolution='bar_open'
  elif j==450:ref=op;why='forced_1130';resolution='bar_open'
  else:
   sh=a['low'][j]<=stop if side==1 else a['high'][j]>=stop
   th=a['high'][j]>=target if side==1 else a['low'][j]<=target
   if not sh and not th:continue
   ref=stop if sh else target;why='stop_intrabar' if sh else 'target_intrabar';resolution='intrabar_unknown';amb=bool(sh and th)
  exit_price=ref-side*slip;net=2*side*(exit_price-entry)-2.5
  return dict(status='filled',entry_reference=raw,entry_price=entry,exit_slot=j,exit_reference=float(ref),exit_price=float(exit_price),stop=stop,target=target,risk_points=risk,risk_usd=2*risk,net_r=net/(2*risk) if risk else None,zero_risk=risk==0,gross_price_pnl=2*side*(ref-raw),friction_cost=4*slip,commission=2.5,net_pnl=net,ecart_ouverture=raw-a['close'][slot-1],ecart_ouverture_ticks=(raw-a['close'][slot-1])/.25,holding_minutes=j-slot+int(resolution=='intrabar_unknown'),ambiguous_stop_target=amb,exit_reason=why)
 raise AssertionError('unclosed')

def first_hit(values,threshold,high):
 hits=np.flatnonzero(values>=threshold if high else values<=threshold)
 return 330+int(hits[0]) if len(hits) else 10000

def signal(es,nq,lev,model,bias,friction):
 if bias==0:return dict(status='neutral_bias',side=0)
 candidates=[]
 for priority,l in enumerate(lev):
  for edge in ('high','low'):
   high=edge=='high';side=(1 if high else -1)*(1 if model=='H1' else -1)
   if bias is not None and side!=bias:continue
   et=first_hit(es[edge][330:420],l['ES'][edge]+(.25 if high else -.25),high)
   nt=first_hit(nq[edge][330:420],l['NQ'][edge]+(.25 if high else -.25),high)
   if 331<=et<=419 and nt>et:candidates.append((et,priority,edge,side,nt))
 if not candidates:return dict(status='no_signal',side=0)
 candidates.sort();et,priority,edge,side,nt=candidates[0];same=[v for v in candidates if v[:2]==(et,priority)]
 if len(same)>1:return dict(status='ambiguous_same_bar',side=0,source_level=lev[priority]['name'])
 meta=dict(side=side,source_level=lev[priority]['name'])
 if model=='H1':return dict(meta,**plan(nq,lev,model,side,et+1,friction))
 for j in range(et,420):
  if nt<=j:return dict(meta,status='smt_cancelled')
  reclaimed=es['close'][j]<lev[priority]['ES'][edge] if edge=='high' else es['close'][j]>lev[priority]['ES'][edge]
  if reclaimed:return dict(meta,**plan(nq,lev,model,side,j+1,friction))
 return dict(meta,status='no_confirmation')

def near(x,y,label):
 if x is None or (isinstance(x,(float,np.floating)) and np.isnan(x)):
  assert y is None or pd.isna(y),str((label,x,y));return
 if isinstance(x,(str,bool,np.bool_)):
  assert x==y,str((label,x,y));return
 assert np.isclose(float(x),float(y),rtol=2e-10,atol=1e-7),str((label,x,y))

def run():
 ds=load_sources();dates={str(d.date()):i for i,d in enumerate(ds.dates)}
 ll=pd.read_csv(O/'levels.csv');levels={}
 for day,g in ll.groupby('date'):
  levels[day]=[dict(name=name,**{s:g[(g.level==name)&(g.symbol==s)].iloc[0][['high','low']].to_dict() for s in ('ES','NQ')}) for name in ('London','Premarket','Previous')]
 checks=0;rows=0
 for friction in (1,2):
  grid=pd.read_csv(O/f'candidate_grid_{friction}.csv')
  for row in grid.itertuples(index=False):
   i=dates[row.date];a={k:v[i] for k,v in ds.arrays['NQ'].items()};p=plan(a,levels[row.date],row.model,row.side,row.entry_slot,friction)
   near(p['status'],row.plan_status,'plan_status');checks+=1
   for k in ('stop','estimated_entry','estimated_risk','estimated_rr','target_level'):
    near(p[k],getattr(row,k),k);checks+=1
   if p['status']=='eligible':
    x=fill(a,p,friction)
    for k,v in x.items():near(v,getattr(row,k),(row.date,row.model,row.side,row.entry_slot,k));checks+=1
   else:near(0.,row.net_pnl,'no order cash');checks+=1
   rows+=1
  print('Oracle grid',friction,len(grid),flush=True)
 q=pd.read_csv(O/'quality.csv').set_index('date');daily=pd.read_csv(O/'daily_comparisons.csv');signals=0
 for row in daily.itertuples(index=False):
  i=dates[row.date];es={k:v[i] for k,v in ds.arrays['ES'].items()};a={k:v[i] for k,v in ds.arrays['NQ'].items()};bias=None if row.bias=='C' else int(q.loc[row.date,'bias_'+row.bias]);p=signal(es,a,levels[row.date],row.model,bias,row.friction)
  near(p['status'],row.smt_status,'signal status');near(p['side'],row.smt_side,'signal side');near(p.get('source_level'),row.source_level,'source level');checks+=3
  if p['status']=='eligible':
   near(p['entry_slot'],row.smt_entry_slot,'signal entry');x=fill(a,p,row.friction);near(x['net_pnl'],row.smt_net,'signal net');checks+=2
  else:near(0.,row.smt_net,'no signal cash');checks+=1
  signals+=1
 # Independently recompute daily sums/counts and closed drawdown from published series.
 summary=pd.read_csv(O/'summary.csv');summarychecks=0
 for row in summary.itertuples(index=False):
  d=daily[(daily.friction==row.friction)&(daily.model==row.model)&(daily.bias==row.bias)]
  if row.period!='ALL':d=d[d.period==row.period]
  prefix='smt' if row.policy=='SMT' else 'bias';p=d[prefix+'_net'].to_numpy();t=d[prefix+'_traded'].to_numpy(bool);curve=np.r_[0.,np.cumsum(p)]
  for value,expected,label in [(p.sum(),row.net_usd,'net'),(t.sum(),row.trades,'count'),(len(d),row.sessions,'sessions'),((np.maximum.accumulate(curve)-curve).max(),row.max_drawdown_closed_usd,'closedDD')]:near(value,expected,label);summarychecks+=1
 # Validate announced H3 measures independently against the raw-aligned array.
 h3=pd.read_csv(O/'h3_daily.csv');hc=0
 for row in h3.itertuples(index=False):
  i=dates[row.date];a=ds.arrays['NQ'];r=max(a['high'][i,330:420])-min(a['low'][i,330:420]);near(r,row.range_points,'H3range');near(r/a['open'][i,330]*10000,row.range_bps,'H3bps');hc+=2
  for s in ('ES','NQ'):
   a=ds.arrays[s];swept=max(a['high'][i,180:330])>=max(a['high'][i,:180])+.25 or min(a['low'][i,180:330])<=min(a['low'][i,:180])-.25
   near(bool(swept),getattr(row,'sweep_'+s),'H3sweep');hc+=1
 receipt=dict(completed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),candidate_rows=rows,field_checks=checks,signal_days=signals,summary_checks=summarychecks,h3_checks=hc,oracle_sha256=sha(__file__),freeze_sha256=sha(ROOT/'FREEZE.json'),run_receipt_sha256=sha(O/'run_receipt.json'),engine_imported=False,context_imported=False,stats_imported=False)
 (ROOT/'audit/oracle_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8');print(json.dumps(receipt),flush=True)
if __name__=='__main__':run()
