"""Post-export independent aggregation/bootstrap/draw reconstruction, no tuning."""
from pathlib import Path
import argparse,json,math,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
from seasonal.data import source


def reconstructed(values,seed,repetitions=3000):
    x=np.asarray(values,float);mask=np.isfinite(x);n=len(x)
    if not mask.any():return {}
    mean=x[mask].mean();a=np.where(mask,x,0.);z=np.where(mask,x-mean,0.);rng=np.random.default_rng(seed);out={}
    for block in (5,20):
        starts=rng.integers(0,n,size=(repetitions,int(np.ceil(n/block))));sums=np.zeros(repetitions);nulls=np.zeros(repetitions);counts=np.zeros(repetitions)
        for j in range(starts.shape[1]):
            length=min(block,n-j*block);indices=(starts[:,j,None]+np.arange(length))%n
            sums+=a[indices].sum(axis=1);nulls+=z[indices].sum(axis=1);counts+=mask[indices].sum(axis=1)
        valid=counts>0;v=sums[valid]/counts[valid];null=nulls[valid]/counts[valid]
        out[str(block)]=dict(mean_ci95=np.quantile(v,[.025,.975]).tolist(),p_one_sided=(1+int((null>=mean).sum()))/(int(valid.sum())+1))
    return out


def close(a,b):assert np.allclose(a,b,rtol=1e-8,atol=1e-10,equal_nan=True),(a,b)


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);out=p.parse_args().out.resolve();comparisons=0;panels=[];maxp={}
    for symbol in ('SPY','QQQ'):
        for period in ('ALL','A','B'):
            primary=pd.read_csv(out/f'{symbol}_{period}_reference/daily.csv');u=json.loads((out/f'{symbol}_{period}_uncertainty.json').read_text())['observed_calendar_blocks']
            rebuilt=reconstructed(primary.observed_return.to_numpy(),20261104)
            for block,v in rebuilt.items():close(v['mean_ci95'],u['blocks'][block]['mean_ci95']);close(v['p_one_sided'],u['blocks'][block]['p_one_sided'])
            comparisons+=1;pairs=json.loads((out/f'{symbol}_{period}_controls.json').read_text())
            for j,name in enumerate(('control_same_clock_long','control_fixed_clock','control_random_clock')):
                control=pd.read_csv(out/f'{symbol}_{period}_{name}/daily.csv');assert primary.date.equals(control.date)
                known=~primary.conditionally_excluded&~control.conditionally_excluded;delta=(primary.return_net-control.return_net).where(known,np.nan).to_numpy()
                close(np.nanmean(delta)*10000,pairs[name]['mean_difference_bps'])
                assert int((known&(primary.trades>0)&(control.trades>0)).sum())==pairs[name]['paired_signal_dates']
                rebuilt=reconstructed(delta,20261104+j)
                for block,v in rebuilt.items():close(v['mean_ci95'],pairs[name]['uncertainty']['blocks'][block]['mean_ci95']);close(v['p_one_sided'],pairs[name]['uncertainty']['blocks'][block]['p_one_sided'])
                comparisons+=1
            if period=='ALL':maxp[symbol]=max(v['p_one_sided'] for v in pairs.values())
        panel=json.loads((out/f'{symbol}_random_clock_panel.json').read_text());d=pd.read_csv(out/f'{symbol}_random_clock_daily.csv');draws=pd.read_csv(out/f'{symbol}_random_clock_draws.csv');rng=np.random.default_rng(panel['seed']);values=np.zeros(panel['repetitions'])
        for row in d.to_dict('records'):
            allowed=sorted(int(k.split('_')[1]) for k,v in row.items() if k.startswith('clock_') and pd.notna(v))
            choices=rng.integers(0,len(allowed),size=panel['repetitions']);values+=np.array([row[f'clock_{k}_net_usd'] for k in allowed])[choices]
        close(values,draws.normalized_net_usd.to_numpy());close(d.reference_net_usd.sum(),panel['normalized_reference_total_usd'])
        close(np.quantile(values,[.025,.975]),panel['random_total_usd_ci95']);assert len(d)==panel['paired_signal_dates'] and len(draws)==1000;panels.append(dict(symbol=symbol,dates=len(d),draws=len(draws)))
    screen=json.loads((out/'SCREENING.json').read_text());ordered=sorted(maxp,key=maxp.get);previous=0.
    for rank,s in enumerate(ordered):
        expected=min(1.,max(previous,(len(ordered)-rank)*maxp[s]));close(expected,screen['results'][s]['holm_p']);previous=expected
    source.write_json(out/'ADDITIONAL_CHECKS.json',dict(passed=True,bootstrap_comparisons=comparisons,holm_verified=True,random_panels=panels,method='Independent calendar-block summation, observed masks, both-trading counts, paired arithmetic, Holm and deterministic random-clock draw reconstruction; no decision changes.'))
    print('Additional checks passed:',comparisons,'bootstrap comparisons and two random panels.')
if __name__=='__main__':main()
