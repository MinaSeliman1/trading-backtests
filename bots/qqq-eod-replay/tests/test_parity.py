import pytest
from qqq_eod.parity import capital_matched

def test_noise_revalue_uses_frozen_minimum_fee_and_rounding(pinned_sources):
 stat=dict(bot='noise',status='complete',decisions=[{'opening':100,'volatility':.02,'quantity':200}],fills=[dict(action='open',actual=100.,sign=1,timestamp='2024-04-30T10:00:00-04:00'),dict(action='close',actual=101.,sign=-1,timestamp='2024-04-30T15:59:00-04:00')])
 x=capital_matched(stat,1050)
 assert x['fills'][0]['qty']==10 and x['net_pnl']==pytest.approx(9.1)
 assert stat['decisions'][0]['quantity']==200 and x['diagnostic_only']

def test_orb_revalue_accounts_for_micro_account_minimum_and_borrow(pinned_sources):
 stat=dict(bot='orb',status='complete',decisions=[dict(sign=-1,quantity=100,stop=101.,sizing_price=100.)],trades=[dict(sign=-1,direction='SHORT',entry_price=99.99,exit_price=98.01,quantity=100)])
 x=capital_matched(stat,1000)
 assert x['trades'][0]['quantity']==10
 assert x['net_pnl']==pytest.approx(10*1.98-.7-10*99.99*.01/360)
 assert stat['decisions'][0]['quantity']==100
