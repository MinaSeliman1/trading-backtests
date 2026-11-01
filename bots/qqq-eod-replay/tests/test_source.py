from pathlib import Path
import json
import pandas as pd
import pytest
from qqq_eod import source as s

def frame():
 return pd.DataFrame(dict(open=[100.],high=[101.],low=[99.],close=[100.5],volume=[10.]),index=pd.to_datetime(['2026-11-02T14:30:00Z']))

def test_quote_validation_never_fills_missing_minutes():
 f=frame();z=s.canonical_frame(f);assert len(z)==1 and str(z.index.tz)=='UTC'
 f.loc[f.index[0],'low']=102.
 with pytest.raises(ValueError):s.canonical_frame(f)

def test_conflicting_duplicate_rejected():
 f=frame();g=f.copy();g['close']=100.75
 with pytest.raises(ValueError):s.canonical_frame(pd.concat([f,g]))
 assert len(s.canonical_frame(pd.concat([f,f])))==1

class Fake:
 def __init__(self):self.calls=[]
 def request(self,*args,**kwargs):self.calls.append((args,kwargs));return {'ok':True}

def test_transport_is_data_only_even_with_valid_credentials():
 f=Fake();t=s.QQQDataOnly(f)
 assert t.request('https://data.alpaca.markets','/v2/stocks/QQQ/bars',params={'feed':'sip','timeframe':'1Min','adjustment':'raw'})=={'ok':True}
 for origin,path,method in [('https://paper-api.alpaca.markets','/v2/account','GET'),('https://paper-api.alpaca.markets','/v2/orders','POST'),('https://data.alpaca.markets','/v2/stocks/SPY/bars','GET'),('https://data.alpaca.markets','/v2/stocks/QQQ/bars','POST')]:
  with pytest.raises(ValueError):t.request(origin,path,method,params={'feed':'sip'})
 assert len(f.calls)==1

def test_captures_are_append_only_and_hashable(tmp_path):
 f=frame();a=s.capture(tmp_path,f,{'kind':'test'});b=s.capture(tmp_path,f,{'kind':'test'})
 assert a['directory']!=b['directory'] and a['bars_sha256']==b['bars_sha256']
 old=Path(a['directory'])/'bars.csv';assert old.exists()
 assert json.loads((Path(a['directory'])/'receipt.json').read_text())['bars_sha256']==s.sha(old)


def test_source_snapshot_is_pinned_to_commit_not_workspace(tmp_path):
 import hashlib,subprocess
 repo=tmp_path/'repo';repo.mkdir();subprocess.run(['git','init','-q',str(repo)],check=True)
 f=repo/'bots/qqq-noise-area/qqq_paper/__init__.py';f.parent.mkdir(parents=True);f.write_bytes(b'OLD = True\n')
 subprocess.run(['git','-C',str(repo),'add','.'],check=True)
 subprocess.run(['git','-C',str(repo),'-c','user.name=Test','-c','user.email=test@example.invalid','commit','-qm','fixture'],check=True)
 commit=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip();relative=f.relative_to(repo).as_posix();lock={'strategy_commit':commit,'source_files':{relative:hashlib.sha256(f.read_bytes()).hexdigest()}}
 f.write_bytes(b'CHANGED = True\n');target=s.freeze_sources(repo,lock,tmp_path/'pinned')
 assert (target/relative).read_bytes()==b'OLD = True\n'
 (target/relative).write_bytes(b'CORRUPTED\n')
 with pytest.raises(ValueError):s.freeze_sources(repo,lock,target)
