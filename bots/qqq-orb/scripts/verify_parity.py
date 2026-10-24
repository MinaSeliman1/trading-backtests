"""Integration replay: no network/vault/current runtime; not prospective evidence."""
from pathlib import Path
import sys,importlib.util,json
import numpy as np
import pandas as pd
BOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(BOT))
from orb_shadow.core import account,advance,verify_model
from orb_shadow import REPO
from orb.engine import simulate,Config
from qqq_paper.runtime import session_for
from qqq_paper.strategy import Session
spec=importlib.util.spec_from_file_location('orb_parity_sources',REPO/'studies/closing-momentum/scripts/run_study.py')
source=importlib.util.module_from_spec(spec);spec.loader.exec_module(source)


def main():
    verify_model();markets,_,profile=source.load_sources();m=markets['QQQ'];frozen=simulate(m,Config(),'2016-01-04','2026-10-16');a=account();count=days=0;errors=[]
    for i,date in enumerate(m.dates):
        day=str(date.date())
        if not '2016-01-04'<=day<='2026-10-16' or not m.valid[i]:continue
        s=Session(pd.Timestamp(m.quality.iloc[i].session_open),pd.Timestamp(m.quality.iloc[i].session_close));n=int(m.lengths[i]);idx=pd.date_range(s.open,periods=n,freq='min')
        frame=pd.DataFrame({k:v[i,:n] for k,v in m.arrays.items() if k in ('open','high','low','close','volume')},index=idx)
        d=None
        for slot in (5,6,n):a,d=advance(a,d,frame,s,s.open+pd.Timedelta(minutes=slot))
        days+=1
        if days%500==0:print(f'PARITY {days} complete sessions',flush=True)
        if 'trade' in d:
            want=frozen.trades.loc[frozen.trades.date==day].iloc[0];got=d['trade'];count+=1
            for key in ('quantity','entry_price','exit_price','net_pnl','commission','borrow_fee'):
                if not np.isclose(got[key],want[key],atol=1e-7,rtol=1e-10):errors.append([day,key])
    assert count==len(frozen.trades) and not errors
    assert np.isclose(a['balance'],frozen.daily.equity.iloc[-1],atol=1e-6)
    out=BOT/'validation';out.mkdir(exist_ok=True)
    source.write_json(out/'historical_parity_2026-10-24.json',dict(status='passed',historical_replay_not_prospective=True,complete_sessions=days,trades=count,
        final_equity=a['balance'],frozen_final_equity=float(frozen.daily.equity.iloc[-1]),checked_fields=6,source_profile=profile,
        limitation='Integration parity shares frozen trade_path; independent historical trade audit remains in the published ORB study.'))
    print(dict(sessions=days,trades=count,final_equity=a['balance']))


if __name__=='__main__':main()
