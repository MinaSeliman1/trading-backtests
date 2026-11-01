"""Causal pooled SMT plans and one-contract execution at micro economics."""
from dataclasses import dataclass
import math
import numpy as np
from .data import price_valid

@dataclass(frozen=True)
class Config:
 tick:float=.25
 multiplier:float=2.
 commission_side:float=1.25
 slip_ticks_side:int=1
 first_entry:int=332
 last_entry:int=420
 force_exit:int=450
 def __post_init__(self):
  if self.tick!=.25 or self.multiplier!=2. or self.commission_side!=1.25:raise ValueError('fixed instrument/commission specification')
  if self.slip_ticks_side not in (1,2):raise ValueError('only declared friction cases')
  if (self.first_entry,self.last_entry,self.force_exit)!=(332,420,450):raise ValueError('fixed window')
 @property
 def slip(self):return self.tick*self.slip_ticks_side

def make_plan(nq,levels,model,side,entry,cfg):
 if model not in ('H1','H2') or side not in (-1,1):raise ValueError('model/side')
 p=dict(status='eligible',model=model,side=int(side),entry_slot=int(entry),signal_slot=int(entry)-1,stop=None,target=None,target_level=None,estimated_entry=None,estimated_risk=None,estimated_rr=None)
 if not cfg.first_entry<=entry<=cfg.last_entry:return dict(p,status='outside_window')
 end=entry;start=end-10 if model=='H1' else 330
 if not price_valid({k:v[start:end] for k,v in nq.items()}).all():return dict(p,status='unknown_plan')
 close=float(nq['close'][end-1]);stop=float(np.min(nq['low'][start:end])-cfg.tick) if side==1 else float(np.max(nq['high'][start:end])+cfg.tick)
 estimate=close+side*cfg.slip;risk=side*(estimate-stop);p.update(stop=stop,estimated_entry=estimate,estimated_risk=risk)
 if risk<=0:return dict(p,status='invalid_estimated_risk')
 if model=='H2':return dict(p,estimated_rr=2.)
 for lev in levels:
  target=float(lev['NQ']['high' if side==1 else 'low'])
  if side*(target-estimate)>1e-10:
   ratio=side*(target-estimate)/risk;p.update(target=target,target_level=lev['name'],estimated_rr=ratio)
   return dict(p,status='eligible' if ratio>=1-1e-10 else 'rr_below1')
 return dict(p,status='no_target')

def scan(es,nq,levels,model,bias,cfg,plan_levels=None):
 """bias=None permits both sides; bias=0 is a known neutral bias."""
 empty=dict(status='no_signal',model=model,side=0,sweep_slot=None,source_level=None,source_edge=None)
 if bias==0:return dict(empty,status='neutral_bias')
 good=price_valid(es)&price_valid(nq)
 es_hi=es_lo=nq_hi=nq_lo=None;pending=None
 for i in range(330,cfg.last_entry):
  if not good[i]:return dict(empty,status='unknown_scan')
  prevhi=es_hi;prevlo=es_lo;eh=float(es['high'][i]);el=float(es['low'][i]);nh=float(nq['high'][i]);nl=float(nq['low'][i])
  es_hi=eh if es_hi is None else max(es_hi,eh);es_lo=el if es_lo is None else min(es_lo,el)
  nq_hi=nh if nq_hi is None else max(nq_hi,nh);nq_lo=nl if nq_lo is None else min(nq_lo,nl)
  if pending is not None:
   edge=pending['source_edge'];lev=next(x for x in levels if x['name']==pending['source_level'])
   invalid=nq_hi>=lev['NQ']['high']+cfg.tick-1e-10 if edge=='high' else nq_lo<=lev['NQ']['low']-cfg.tick+1e-10
   if invalid:return dict(pending,status='smt_cancelled')
  if i+1<cfg.first_entry:continue
  if pending is None:
   for lev in levels:
    candidates=[]
    for edge in ('high','low'):
     high=edge=='high';eslevel=lev['ES'][edge];nqlevel=lev['NQ'][edge]
     fresh=(eh>=eslevel+cfg.tick-1e-10 and (prevhi is None or prevhi<eslevel+cfg.tick-1e-10)) if high else (el<=eslevel-cfg.tick+1e-10 and (prevlo is None or prevlo>eslevel-cfg.tick+1e-10))
     unmatched=nq_hi<nqlevel+cfg.tick-1e-10 if high else nq_lo>nqlevel-cfg.tick+1e-10
     side=(1 if high else -1)*(1 if model=='H1' else -1)
     if fresh and unmatched and (bias is None or bias==side):candidates.append((edge,side))
    if len(candidates)>1:return dict(empty,status='ambiguous_same_bar',sweep_slot=i,source_level=lev['name'])
    if candidates:
     edge,side=candidates[0];pending=dict(empty,side=side,sweep_slot=i,source_level=lev['name'],source_edge=edge,status='pending');break
  if pending is not None:
   lev=next(x for x in levels if x['name']==pending['source_level']);edge=pending['source_edge'];reclaimed=float(es['close'][i])<lev['ES']['high'] if edge=='high' else float(es['close'][i])>lev['ES']['low']
   if model=='H1' or reclaimed:
    plan=make_plan(nq,levels if plan_levels is None else plan_levels,model,pending['side'],i+1,cfg);return dict(pending,**plan)
 return dict(pending,status='no_confirmation') if pending is not None else empty

def execute(nq,plan,cfg,marks=False):
 if plan['status']!='eligible':return None
 side=plan['side'];left=plan['entry_slot'];stop=plan['stop'];o=float(nq['open'][left])
 if not math.isfinite(o) or o<=0:return dict(status='unknown_execution',reason='missing_entry_open',first_unknown_slot=left)
 entry=o+side*cfg.slip;risk=abs(entry-stop);target=plan['target'] if plan['model']=='H1' else entry+side*2*max(0.,side*(entry-stop))
 path=[0.,-cfg.commission_side-cfg.slip*cfg.multiplier];lo=hi=entry;held=0
 for j in range(left,cfg.force_exit+1):
  op=float(nq['open'][j])
  if not math.isfinite(op) or op<=0:return dict(status='unknown_execution',reason='missing_active_open',first_unknown_slot=j)
  if side*(op-stop)<=0:ref=op;why='entry_marketable_stop' if j==left else 'stop_gap';resolution='bar_open';ambiguous=False;break
  if side*(op-target)>=0:ref=op;why='entry_marketable_target' if j==left else 'target_gap';resolution='bar_open';ambiguous=False;break
  if j==cfg.force_exit:ref=op;why='forced_1130';resolution='bar_open';ambiguous=False;break
  h,l,c=[float(nq[k][j]) for k in ('high','low','close')]
  if not all(math.isfinite(v) for v in (h,l,c)) or l<=0 or h<max(op,c) or l>min(op,c):return dict(status='unknown_execution',reason='invalid_active_bar',first_unknown_slot=j)
  stophit=l<=stop if side==1 else h>=stop;targethit=h>=target if side==1 else l<=target
  if stophit or targethit:
   ref=stop if stophit else target;why='stop_intrabar' if stophit else 'target_intrabar';resolution='intrabar_unknown';ambiguous=bool(stophit and targethit);break
  held+=1;lo=min(lo,l);hi=max(hi,h)
  if marks:path.append(side*(c-entry)*cfg.multiplier-cfg.commission_side)
 exit_price=ref-side*cfg.slip;net=side*(exit_price-entry)*cfg.multiplier-2*cfg.commission_side;lo=min(lo,exit_price);hi=max(hi,exit_price)
 if marks:path.append(net)
 close=float(nq['close'][left-1]);gap=o-close
 out=dict(status='filled',entry_reference=o,entry_price=entry,exit_slot=j,exit_reference=float(ref),exit_price=float(exit_price),stop=stop,target=target,
  risk_points=risk,risk_usd=risk*cfg.multiplier,net_r=net/(risk*cfg.multiplier) if risk>0 else None,zero_risk=bool(risk==0),
  gross_price_pnl=side*(ref-o)*cfg.multiplier,friction_cost=2*cfg.slip*cfg.multiplier,commission=2*cfg.commission_side,net_pnl=net,
  ecart_ouverture=gap,ecart_ouverture_ticks=gap/cfg.tick,entry_gap=bool(abs(gap)>1e-10),actual_target_r=side*(target-entry)/risk if risk>0 else None,
  gap_rr_below1=bool(plan['model']=='H1' and (risk<=0 or side*(target-entry)<risk-1e-10)),exit_reason=why,exit_resolution=resolution,ambiguous_stop_target=ambiguous,
  holding_minutes=j-left+int(resolution=='intrabar_unknown'),mae_price_usd=((lo-entry) if side==1 else (entry-hi))*cfg.multiplier,mfe_price_usd=((hi-entry) if side==1 else (entry-lo))*cfg.multiplier)
 if marks:out['marks']=path
 assert abs(out['gross_price_pnl']-out['friction_cost']-out['commission']-net)<1e-8
 return out
