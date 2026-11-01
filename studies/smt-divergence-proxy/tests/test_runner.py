from pathlib import Path
import sys,importlib.util
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
p=Path(__file__).resolve().parents[1]/'scripts/run.py'
spec=importlib.util.spec_from_file_location('runner',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def test_trade_record_merges_overlapping_fields_and_drops_marks():
 r=m.trade_record({'model':'H1','policy':'SMT'},{'model':'H1','status':'eligible'},{'status':'filled','net_pnl':-3.5,'marks':[0,-3.5]})
 assert r=={'model':'H1','policy':'SMT','status':'filled','net_pnl':-3.5}
def test_frozen_files_include_pre_pnl_input_profile():
 assert any(p.name=='DATA_PROFILE_PREPNL.json' for p in m.core_files())

def test_full_pipeline_on_two_synthetic_days(tmp_path,monkeypatch):
 import numpy as np
 import pandas as pd
 from types import SimpleNamespace
 from smt.data import FIELDS
 dates=pd.to_datetime(['2026-02-26','2026-03-02'])
 arrays={symbol:{k:np.full((2,720),v,float) for k,v in dict(open=100.,high=100.25,low=99.75,close=100.).items()} for symbol in ('ES','NQ')}
 arrays['ES']['high'][:,331]=113.
 valid={symbol:np.ones((2,720),bool) for symbol in arrays}
 ds=SimpleNamespace(dates=dates,evaluation=np.ones(2,bool),valid=valid,arrays=arrays,roll=np.zeros(2,bool),profile={'inputs':{s:{'sha256':'synthetic'} for s in arrays}})
 levels=[{'name':name,'ES':{'high':110.+i,'low':90.-i},'NQ':{'high':102.+i,'low':98.-i}} for i,name in enumerate(('London','Premarket','Previous'))]
 context=dict(eligible={b:True for b in ('A','B','C')},reasons={b:[] for b in ('A','B','C')},bias={'A':1,'B':1,'C':None},levels=levels,complete=True)
 monkeypatch.setattr(m,'OUT',tmp_path);monkeypatch.setattr(m,'check_freeze',lambda:{})
 monkeypatch.setattr(m,'load_sources',lambda:ds);monkeypatch.setattr(m,'day_context',lambda ds,i:context)
 monkeypatch.setattr(m,'news_calendar',lambda:pd.DataFrame({'date':[],'kind':[]}))
 original_sha=m.sha;monkeypatch.setattr(m,'sha',lambda p:original_sha(p) if Path(p).exists() else 'synthetic')
 m.run()
 import json
 gates=json.loads((tmp_path/'gates.json').read_text(encoding='utf-8'));assert len(gates)==6 and not any(g['passes_proxy_phase2'] for g in gates)
 ledger=pd.read_csv(tmp_path/'ledger_1_H1_A.csv');assert (ledger.policy=='SMT').sum()==2
 draws=pd.read_csv(tmp_path/'control_draws.csv');assert draws.shape==(2,1002)
 assert len(pd.read_csv(tmp_path/'candidate_grid_1.csv'))==2*2*2*89
 assert len(pd.read_csv(tmp_path/'random_portfolios.csv'))==2*6*3*1000
