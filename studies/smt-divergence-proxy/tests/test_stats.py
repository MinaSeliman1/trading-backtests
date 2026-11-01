from pathlib import Path
import sys
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from smt.stats import holm,contrast,portfolio

def test_holm_is_monotone_in_rank_and_handles_six():
 p=np.array([.001,.02,.5,.3,.04,.9]);q=holm(p)
 assert np.allclose(q,[.006,.1,1.,.9,.16,1.])
def test_constant_positive_contrast_and_zero_null():
 x=contrast(np.ones(30),20,99);z=contrast(np.zeros(30),20,99)
 assert x['mean']==1 and x['ci_low']==1 and x['p_centered']<.001
 assert z['ci_low']==0 and z['p_centered']==1

def test_portfolio_cash_days_counts_costs_and_drawdown():
 p=portfolio(np.array([10.,0.,-4.,-8.]),np.array([True,False,True,True]))
 assert p['trades']==3 and p['net_usd']==-2 and p['max_drawdown_closed_usd']==12 and p['win_rate']==1/3 and p['profit_factor']==10/12
