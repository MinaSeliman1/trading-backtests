"""Reproduce the frozen ES/NQ proxy experiment without broker access."""
from pathlib import Path
import sys,json,hashlib,datetime,platform,argparse
from collections import Counter
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from smt.data import ROOT,load_sources,news_calendar,sha
from smt.context import day_context,random_controls,period
from smt.engine import Config,make_plan,scan,execute
from smt.stats import portfolio,contrast,holm,bootstrap_indices
OUT=ROOT/'results'

def clean(v):
 if isinstance(v,dict):return {str(k):clean(x) for k,x in v.items()}
 if isinstance(v,(list,tuple)):return [clean(x) for x in v]
 if isinstance(v,np.ndarray):return clean(v.tolist())
 if isinstance(v,(np.integer,np.bool_)):return v.item()
 if isinstance(v,(float,np.floating)):return float(v) if np.isfinite(v) else None
 return v

def js(path,v):Path(path).write_text(json.dumps(clean(v),ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8',newline='\n')
def csv(name,rows):
 pd.DataFrame(rows).to_csv(OUT/name,index=False,encoding='utf-8',lineterminator='\n',float_format='%.12g')

def core_files():
 return sorted([p for sub in ('smt','tests','scripts') for p in (ROOT/sub).rglob('*.py')]+[ROOT/'PROTOCOL_EXECUTION.md',ROOT/'DESIGN.md',ROOT/'sources/news_calendar.csv',ROOT/'sources/bls_calendar_rows.json',ROOT/'sources/fed_calendar.html',ROOT/'sources/DATA_PROFILE_PREPNL.json'])
def input_hashes():
 raw=ROOT.parents[2]/'data/free_sources/BARS'
 return {str(p.resolve()):sha(p) for p in [raw/'ES_1m_raw.csv.gz',raw/'NQ_1m_raw.csv.gz',raw/'ES_1m_raw.csv.gz.provenance.json',raw/'NQ_1m_raw.csv.gz.provenance.json',raw/'README.md',raw/'catalog.json']}

def trade_record(meta,signal,result):return {**meta,**signal,**{k:v for k,v in result.items() if k!='marks'}}

def freeze():
 if OUT.exists() and any(OUT.iterdir()):raise RuntimeError('refuse freeze after historical results')
 p=ROOT/'FREEZE.json'
 if p.exists():raise RuntimeError('already frozen')
 js(p,dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),seed=20261031,input_hashes=input_hashes(),files={str(x.relative_to(ROOT)).replace('\\','/'):sha(x) for x in core_files()},python=platform.python_version(),numpy=np.__version__,pandas=pd.__version__,split_A_end='2026-02-27',split_B_start='2026-03-02',principal_variants=6))
 print('Frozen before historical PnL',flush=True)

def check_freeze():
 f=json.loads((ROOT/'FREEZE.json').read_text(encoding='utf-8'))
 for name,digest in f['files'].items():
  if sha(ROOT/name)!=digest:raise RuntimeError('frozen file changed: '+name)
 if f['input_hashes']!=input_hashes():raise RuntimeError('frozen input changed')
 return f

def run():
 frozen=check_freeze();OUT.mkdir(exist_ok=True);ds=load_sources();ctx={i:day_context(ds,i) for i in np.flatnonzero(ds.evaluation)}
 coins,draws=random_controls(ds.dates);calendar=news_calendar();news={str(k):';'.join(g['kind']) for k,g in calendar.groupby('date')}
 csv('quality.csv',[dict(date=str(ds.dates[i].date()),period=period(ds.dates[i].date()),roll_guard=bool(ds.roll[i]),previous_roll_guard=bool(ds.roll[i-1]) if i else False,complete=c['complete'],eligible_A=c['eligible']['A'],eligible_B=c['eligible']['B'],eligible_C=c['eligible']['C'],excluded_A=';'.join(c['reasons']['A']),excluded_B=';'.join(c['reasons']['B']),bias_A=c['bias']['A'],bias_B=c['bias']['B'],news=news.get(str(ds.dates[i].date()),'')) for i,c in ctx.items()])
 csv('levels.csv',[dict(date=str(ds.dates[i].date()),level=l['name'],symbol=s,**l[s]) for i,c in ctx.items() for l in c['levels'] for s in ('ES','NQ')])
 csv('control_draws.csv',[dict(date=str(ds.dates[i].date()),coin_C=coins[i],**{'rep_'+str(j):draws[j,i] for j in range(1000)}) for i in ctx])
 js(OUT/'data_profile.json',ds.profile)
 all_summary=[];all_daily=[];all_random=[];all_contrasts=[];gates=[];diagnostics=[];by_level=[]
 for friction in (1,2):
  cfg=Config(slip_ticks_side=friction);grid={};grid_rows=[]
  for i,c in ctx.items():
   if not c['eligible']['B']:continue
   nq={k:v[i] for k,v in ds.arrays['NQ'].items()}
   for model in ('H1','H2'):
    for side in (-1,1):
     for slot in range(332,421):
      p=make_plan(nq,c['levels'],model,side,slot,cfg);x=execute(nq,p,cfg)
      if x is not None and x['status']!='filled':raise RuntimeError('unknown outcome in conditional complete sample')
      row=dict(date=str(ds.dates[i].date()),friction=friction,**p,plan_status=p['status'])
      if x:row.update(x)
      else:row.update(net_pnl=0.,risk_usd=0.,holding_minutes=0,status=p['status'])
      grid[(i,model,side,slot)]=row;grid_rows.append(row)
  csv('candidate_grid_'+str(friction)+'.csv',grid_rows)
  print('Friction',friction,'candidate rows',len(grid_rows),flush=True)
  for vi,(model,biasname) in enumerate((m,b) for m in ('H1','H2') for b in ('A','B','C')):
   indices=[i for i,c in ctx.items() if c['eligible'][biasname]];n=len(indices)
   dates=np.array([str(ds.dates[i].date()) for i in indices]);parts=np.array([period(d) for d in dates]);ann=np.array([bool(news.get(d,'')) for d in dates])
   pp={p:np.zeros(n) for p in ('SMT','bias')};tr={p:np.zeros(n,bool) for p in pp};risk={p:np.zeros(n) for p in pp};mins={p:np.zeros(n) for p in pp}
   rr=np.zeros((1000,n));rt=np.zeros((1000,n),bool);rk=np.zeros((1000,n));rm=np.zeros((1000,n));status_counts=Counter();ledgers=[];smt_sides=[];smt_slots=[];smtr=[]
   for j,i in enumerate(indices):
    c=ctx[i];day=dates[j];nq={k:v[i] for k,v in ds.arrays['NQ'].items()};es={k:v[i] for k,v in ds.arrays['ES'].items()};bias=c['bias'][biasname]
    signal=scan(es,nq,c['levels'],model,bias,cfg);smt_sides.append(signal.get('side',0));smt_slots.append(signal.get('entry_slot') if signal['status']=='eligible' else None)
    row=None
    if signal['status']=='eligible':
     row=grid[(i,model,signal['side'],signal['entry_slot'])];x=execute(nq,signal,cfg,marks=True)
     if abs(x['net_pnl']-row['net_pnl'])>1e-9:raise AssertionError('grid/scan mismatch')
     record=trade_record(dict(date=day,period=parts[j],friction=friction,model=model,bias=biasname,policy='SMT',news=news.get(day,'')),signal,x)
     ledgers.append(record)
     pp['SMT'][j]=row['net_pnl'];tr['SMT'][j]=True;risk['SMT'][j]=row['risk_usd'];mins['SMT'][j]=row['holding_minutes']
    smtr.append(row);control_side=int(coins[i] if biasname=='C' else bias)
    control=grid[(i,model,control_side,332)] if control_side else None
    if control is not None:
     pp['bias'][j]=control['net_pnl'];tr['bias'][j]=control['status']=='filled';risk['bias'][j]=control['risk_usd'];mins['bias'][j]=control['holding_minutes']
     if control['status']=='filled':ledgers.append(dict(control,policy='bias',period=parts[j],bias=biasname,news=news.get(day,'')))
     pool=[grid[(i,model,control_side,slot)] for slot in range(332,421)]
     dd=draws[:,i]-332
     rr[:,j]=np.array([r['net_pnl'] for r in pool])[dd];rt[:,j]=np.array([r['status']=='filled' for r in pool])[dd];rk[:,j]=np.array([r['risk_usd'] for r in pool])[dd];rm[:,j]=np.array([r['holding_minutes'] for r in pool])[dd]
     status_counts.update('random:'+pool[k]['status'] for k in dd)
    else:status_counts.update({'random:neutral_bias':1000})
    status_counts.update(['SMT:'+signal['status'],'bias:'+(control['status'] if control else 'neutral_bias')])
    all_daily.append(dict(date=day,period=parts[j],friction=friction,model=model,bias=biasname,news=news.get(day,''),control_side=control_side,smt_status=signal['status'],smt_side=signal.get('side',0),source_level=signal.get('source_level'),smt_entry_slot=signal.get('entry_slot'),smt_net=pp['SMT'][j],smt_traded=tr['SMT'][j],smt_risk=risk['SMT'][j],smt_minutes=mins['SMT'][j],bias_status=control['status'] if control else 'neutral_bias',bias_net=pp['bias'][j],bias_traded=tr['bias'][j],bias_risk=risk['bias'][j],bias_minutes=mins['bias'][j],random_mean_net=rr[:,j].mean(),random_trade_fraction=rt[:,j].mean(),random_mean_risk=rk[:,j].mean(),random_mean_minutes=rm[:,j].mean()))
   csv('ledger_'+str(friction)+'_'+model+'_'+biasname+'.csv',ledgers)
   diagnostics.append(dict(friction=friction,model=model,bias=biasname,diagnostic='exclusions',counts=dict(status_counts)))
   gate=dict(friction=friction,model=model,bias=biasname)
   for part in ('A','B','ALL'):
    mask=parts==part if part!='ALL' else np.ones(n,bool)
    for pol in pp:
     s=portfolio(pp[pol][mask],tr[pol][mask],risk[pol][mask],mins[pol][mask]);all_summary.append(dict(friction=friction,model=model,bias=biasname,period=part,policy=pol,**s))
     if pol=='SMT':gate.update({part+'_trades':s['trades'],part+'_net':s['net_usd'],part+'_zero_risk':s['zero_risk_trades']})
    totals=rr[:,mask].sum(axis=1);counts=rt[:,mask].sum(axis=1)
    r_values=np.divide(rr[:,mask],rk[:,mask],out=np.zeros_like(rr[:,mask]),where=rk[:,mask]>0)
    for rep in range(1000):all_random.append(dict(friction=friction,model=model,bias=biasname,period=part,rep=rep,net_usd=totals[rep],trades=counts[rep],risk_usd_sum=rk[rep,mask].sum(),exposure_minutes=rm[rep,mask].sum(),net_r=r_values[rep].sum(),mean_r_trade=r_values[rep].sum()/int((rt[rep,mask]&(rk[rep,mask]>0)).sum()) if (rt[rep,mask]&(rk[rep,mask]>0)).any() else None,defined_r_trades=int((rt[rep,mask]&(rk[rep,mask]>0)).sum()),zero_risk_trades=int((rt[rep,mask]&(rk[rep,mask]==0)).sum()),commission=counts[rep]*2.5,friction_cost=counts[rep]*cfg.slip*4))
    rank=(1+int((totals>=pp['SMT'][mask].sum()-1e-10).sum()))/1001
    for block in (5,20):
     for cmp,control_pnl in [('bias',pp['bias']),('random',rr.mean(axis=0))]:
      contrast_result=contrast((pp['SMT']-control_pnl)[mask],block,vi*10+(0 if part=='A' else 1 if part=='B' else 2))
      all_contrasts.append(dict(friction=friction,model=model,bias=biasname,period=part,comparator=cmp,block=block,random_rank_p=rank,**contrast_result))
      if part=='A' and block==20:gate['A_delta_'+cmp]=contrast_result['mean']
      if part=='B' and block==20:gate['B_low_'+cmp]=contrast_result['ci_low'];gate['B_p_'+cmp]=contrast_result['p_centered']
    if part=='B':gate['B_random_rank_p']=rank
    # These are descriptive announced-calendar strata, never selection criteria.
    for tag,sub in [('retained_announcements',ann),('outside_retained_calendar',~ann)]:
     mm=mask&sub
     diagnostics.append(dict(friction=friction,model=model,bias=biasname,diagnostic='news_stratum',period=part,stratum=tag,**portfolio(pp['SMT'][mm],tr['SMT'][mm],risk['SMT'][mm],mins['SMT'][mm])))
   # C future-signal-side controls, explicitly non-tradable and outside all gates.
   if biasname=='C':
    for part in ('A','B','ALL'):
     jj=[j for j in range(n) if tr['SMT'][j] and (part=='ALL' or parts[j]==part)];b=[];rand=[]
     for j in jj:
      i=indices[j];side=smt_sides[j];b.append(grid[(i,model,side,332)]['net_pnl']);rand.append([grid[(i,model,side,int(slot))]['net_pnl'] for slot in draws[:,i]])
     diagnostics.append(dict(friction=friction,model=model,bias=biasname,period=part,diagnostic='contrefactuel, non tradable',matched_smt_days=len(jj),smt_net=float(pp['SMT'][jj].sum()),bias_same_future_side_net=float(np.sum(b)),random_same_future_side_mean_net=float(np.asarray(rand).sum()/1000) if len(jj) else 0.))
   # Permute (entry time, direction, no-entry) cards; statistical placebo, not a policy.
   for part in ('A','B'):
    jj=np.flatnonzero(parts==part);rng=np.random.default_rng(np.random.SeedSequence([20261031,3,vi,0 if part=='A' else 1]));totals=[]
    groups={s:[j for j in jj if ctx[indices[j]]['bias'][biasname]==s] for s in (-1,0,1)} if biasname!='C' else {0:list(jj)}
    for rep in range(1000):
     total=0.
     for group in groups.values():
      for dest,src in zip(group,rng.permutation(group)):
       if smt_slots[src] is not None:total+=grid[(indices[dest],model,smt_sides[src],smt_slots[src])]['net_pnl']
     totals.append(total)
    diagnostics.append(dict(friction=friction,model=model,bias=biasname,period=part,diagnostic='minute_direction_cards_permutation_nontradable',smt_net=float(pp['SMT'][jj].sum()),placebo_q025=float(np.quantile(totals,.025)),placebo_mean=float(np.mean(totals)),placebo_q975=float(np.quantile(totals,.975)),rank_p=(1+int((np.array(totals)>=pp['SMT'][jj].sum()-1e-10).sum()))/1001))
   gates.append(gate)
   print('Completed',friction,model,biasname,'eligible sessions',n,flush=True)
  # Per-level discovery-only diagnostic, after principal results; no selection.
  if friction==1:
   for model in ('H1','H2'):
    for bn in ('A','B','C'):
     for lname in ('London','Premarket','Previous'):
      pnl=[];filled=[]
      for i,c in ctx.items():
       if not c['eligible'][bn] or period(ds.dates[i].date())!='A':continue
       nq={k:v[i] for k,v in ds.arrays['NQ'].items()};es={k:v[i] for k,v in ds.arrays['ES'].items()};ls=[l for l in c['levels'] if l['name']==lname];p=scan(es,nq,ls,model,c['bias'][bn],cfg,plan_levels=c['levels']);x=execute(nq,p,cfg)
       pnl.append(x['net_pnl'] if x else 0.);filled.append(bool(x))
      by_level.append(dict(model=model,bias=bn,level=lname,period='A ONLY - diagnostic, never selection',**portfolio(pnl,filled)))
 # Joint Holm family consists of exactly the six baseline variants.
 base=[g for g in gates if g['friction']==1];stress={(g['model'],g['bias']):g for g in gates if g['friction']==2}
 p=[max(g['B_p_bias'],g['B_p_random'],g['B_random_rank_p']) for g in base]
 for g,praw,padj in zip(base,p,holm(p)):
  s=stress[(g['model'],g['bias'])];g.update(B_joint_p=praw,B_holm_p=padj,B_stress_net=s['B_net'])
  checks=dict(sample=g['ALL_trades']>=100 and g['B_trades']>=25,positive_A_B=g['A_net']>0 and g['B_net']>0,A_incremental=g['A_delta_bias']>0 and g['A_delta_random']>0,B_incremental_CI=g['B_low_bias']>0 and g['B_low_random']>0,multiplicity=padj<=.05,stress=s['B_net']>0,defined_R=g['ALL_zero_risk']==0)
  g['checks']=checks;g['passes_proxy_phase2']=all(checks.values())
 csv('summary.csv',all_summary);csv('daily_comparisons.csv',all_daily);csv('random_portfolios.csv',all_random);csv('contrasts.csv',all_contrasts);csv('discovery_level_diagnostic.csv',by_level)
 js(OUT/'gates.json',base);js(OUT/'diagnostics.json',diagnostics)
 h3=[]
 for i,c in ctx.items():
  if ds.roll[i] or not ds.valid['ES'][i,:330].all() or not ds.valid['NQ'][i,:420].all():continue
  ev={}
  for sym in ('ES','NQ'):
   a=ds.arrays[sym];ev[sym]=bool(a['high'][i,180:330].max()>=a['high'][i,:180].max()+.25 or a['low'][i,180:330].min()<=a['low'][i,:180].min()-.25)
  day=str(ds.dates[i].date());a=ds.arrays['NQ'];r=float(a['high'][i,330:420].max()-a['low'][i,330:420].min())
  h3.append(dict(date=day,period=period(day),news=news.get(day,''),sweep_ES=ev['ES'],sweep_NQ=ev['NQ'],any_sweep=any(ev.values()),group='both' if all(ev.values()) else 'ES_only' if ev['ES'] else 'NQ_only' if ev['NQ'] else 'none',range_points=r,range_bps=r/a['open'][i,330]*10000))
 csv('h3_daily.csv',h3);h=pd.DataFrame(h3);hs=[]
 for part in ('A','B','ALL'):
  for news_tag in ('all','outside_retained_calendar'):
   t=h if part=='ALL' else h[h.period==part]
   if news_tag!='all':t=t[t.news=='']
   for group in ('none','ES_only','NQ_only','both','any'):
    z=t[t.any_sweep] if group=='any' else t[t.group==group]
    hs.append(dict(period=part,calendar=news_tag,group=group,n=len(z),mean_points=float(z.range_points.mean()),median_points=float(z.range_points.median()),mean_bps=float(z.range_bps.mean()),median_bps=float(z.range_bps.median())))
   for block in (5,20):
    idx=bootstrap_indices(len(t),block,100+(0 if part=='A' else 1 if part=='B' else 2));a=t.any_sweep.to_numpy(bool);r=t.range_bps.to_numpy();boot=[]
    for row in idx:
     ar=a[row];v=r[row]
     if ar.any() and (~ar).any():boot.append(v[ar].mean()-v[~ar].mean())
    hs.append(dict(period=part,calendar=news_tag,group='any_minus_none_bootstrap',block=block,n=len(t),mean_bps=float(r[a].mean()-r[~a].mean()) if a.any() and (~a).any() else None,ci_low=float(np.quantile(boot,.025)) if boot else None,ci_high=float(np.quantile(boot,.975)) if boot else None,bootstrap_valid=len(boot)))
 csv('h3_summary.csv',hs)
 check_freeze();js(OUT/'run_receipt.json',dict(completed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),freeze_sha256=sha(ROOT/'FREEZE.json'),source_hashes={s:p['sha256'] for s,p in ds.profile['inputs'].items()},principal_variants=6,random_repetitions=1000,bootstrap_repetitions=3000,files={p.name:sha(p) for p in sorted(OUT.iterdir()) if p.is_file() and p.name!='run_receipt.json'}))
 print('Experiment finished; proxy passes',sum(g['passes_proxy_phase2'] for g in base),flush=True)

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--freeze',action='store_true');parser.add_argument('--run',action='store_true');a=parser.parse_args()
 if a.freeze:freeze()
 elif a.run:run()
 else:parser.error('choose --freeze or --run')
