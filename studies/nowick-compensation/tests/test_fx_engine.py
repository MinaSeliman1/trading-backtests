import sys
from pathlib import Path
import unittest
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import fx_engine as fx

def order(d=1):
    return {'d':d,'entry':1000,'sl':900 if d==1 else 1100,'tp':1100 if d==1 else 900,'extreme':1040 if d==1 else 960}

class ExecutionTests(unittest.TestCase):
    def test_limit_requires_penetration(self):
        self.assertEqual(fx.pending_event(order(),[1020,1040,991,1010],10,'cancel_first')[0],'wait')
        self.assertEqual(fx.pending_event(order(),[1020,1040,990,1010],10,'cancel_first')[0],'fill')

    def test_front_run_strict(self):
        self.assertEqual(fx.pending_event(order(),[1020,1041,1001,1030],10,'cancel_first')[0],'cancel')

    def test_ambiguous_front_run_both_models(self):
        q=[1020,1041,990,1010]
        self.assertEqual(fx.pending_event(order(),q,10,'cancel_first'),('cancel',True,False))
        self.assertEqual(fx.pending_event(order(),q,10,'fill_first'),('fill',True,False))

    def test_open_resolves_entry_before_front_run(self):
        self.assertEqual(fx.pending_event(order(),[990,1050,980,1020],10,'cancel_first'),('fill',False,True))

    def test_open_resolves_front_run_before_entry(self):
        self.assertEqual(fx.pending_event(order(),[1041,1050,980,1020],10,'fill_first'),('cancel',False,False))

    def test_front_run_off(self):
        self.assertEqual(fx.pending_event(order(),[1041,1050,980,1020],10,'off')[0],'fill')

    def test_short_limit(self):
        self.assertEqual(fx.pending_event(order(-1),[980,1010,960,990],10,'cancel_first')[0],'fill')

    def test_short_ambiguity(self):
        self.assertEqual(fx.pending_event(order(-1),[980,1010,959,990],10,'cancel_first'),('cancel',True,False))

    def test_stop_first_on_dual_touch(self):
        self.assertEqual(fx.position_event(order(),[1000,1110,890,1000],10),('SL',900,True))

    def test_short_stop_first(self):
        self.assertEqual(fx.position_event(order(-1),[1000,1110,890,1000],10),('SL',1100,True))

    def test_stop_gap_is_worse(self):
        self.assertEqual(fx.position_event(order(),[880,910,870,900],10),('SL_GAP',880,False))
        self.assertEqual(fx.position_event(order(-1),[1120,1130,1090,1100],10),('SL_GAP',1120,False))

    def test_open_target_precedes_later_stop(self):
        self.assertEqual(fx.position_event(order(),[1120,1130,890,1000],10),('TP',1100,False))

    def test_target_requires_penetration(self):
        self.assertIsNone(fx.position_event(order(),[1000,1109,980,1000],10)[0])
        self.assertEqual(fx.position_event(order(),[1000,1110,980,1000],10)[0],'TP')

    def test_entry_minute_wick_not_profit(self):
        self.assertIsNone(fx.position_event(order(),[1020,1110,990,1000],10,new_intramin=True)[0])

    def test_entry_minute_close_proves_target(self):
        self.assertEqual(fx.position_event(order(),[1020,1120,990,1110],10,new_intramin=True)[0],'TP')

    def test_entry_minute_stop_allowed(self):
        self.assertEqual(fx.position_event(order(),[1020,1110,890,1110],10,new_intramin=True)[0],'SL')

    def test_short_entry_minute_wick(self):
        self.assertIsNone(fx.position_event(order(-1),[980,1010,890,1000],10,new_intramin=True)[0])

    def test_short_entry_minute_close(self):
        self.assertEqual(fx.position_event(order(-1),[980,1010,880,890],10,new_intramin=True)[0],'TP')

    def test_ttl(self):
        self.assertEqual([fx.pending_expired(i,100,9) for i in [100,101,108,109,110]],[False,False,False,True,True])

    def test_pivot_rightmost_tie(self):
        h=np.array([1,2,3,3,2,1,0])
        l=-h
        ph,pl=fx.confirm_pivots(h,l,np.ones(7,bool),np.arange(7)*900,2)
        self.assertTrue(np.isnan(ph[4]))
        self.assertEqual(ph[5],3)
        self.assertEqual(pl[5],-3)

    def test_pivot_no_future_or_gap(self):
        h=np.array([1,2,5,2,1]); l=-h
        ph,_=fx.confirm_pivots(h,l,np.ones(5,bool),np.arange(5)*900,2)
        self.assertTrue(np.isnan(ph[:4]).all())
        self.assertEqual(ph[4],5)
        times=np.arange(5)*900; times[-1]+=900
        self.assertTrue(np.isnan(fx.confirm_pivots(h,l,np.ones(5,bool),times,2)[0]).all())

    def test_partial_bar_no_pivot(self):
        h=np.array([1,2,5,2,1]); c=np.ones(5,bool); c[1]=False
        self.assertTrue(np.isnan(fx.confirm_pivots(h,-h,c,np.arange(5)*900,2)[0]).all())

    def test_sessions_dst(self):
        self.assertTrue(fx.entry_time_allowed(pd.Timestamp('2024-01-03T07:00Z').timestamp()))
        self.assertTrue(fx.entry_time_allowed(pd.Timestamp('2024-07-03T06:00Z').timestamp()))
        self.assertFalse(fx.entry_time_allowed(pd.Timestamp('2024-07-03T12:00Z').timestamp()))

    def test_quote_pip_cost(self):
        self.assertAlmostEqual(fx.fee_cash(100000,'GBPUSD',1),10)
        self.assertAlmostEqual(fx.fee_cash(100000,'USDJPY',1),1000)

    def test_signal_stop_bounds(self):
        self.assertTrue(fx.stop_valid(50))
        self.assertTrue(fx.stop_valid(300))
        self.assertFalse(fx.stop_valid(49))
        self.assertFalse(fx.stop_valid(301))

    def test_position_risk(self):
        q=fx.risk_quantity(100000,100,'GBPUSD')
        self.assertEqual(q,1000000)
        self.assertEqual(fx.risk_quantity(-1,100,'GBPUSD'),0)

    def test_rr_rounding(self):
        self.assertEqual(fx.levels(1,1001,1030,950,1.5,False),(1001,920,1122))
        self.assertEqual(fx.levels(-1,1001,980,1050,1.5,False),(1001,1080,883))

    def test_features_prefix_invariant(self):
        raw=fx.fixture_minutes(1200)
        full=fx.prepare_market(raw,'GBPUSD').features
        part=fx.prepare_market({k:v[:900] for k,v in raw.items()},'GBPUSD').features
        pd.testing.assert_frame_equal(full.iloc[:len(part)].reset_index(drop=True),part.reset_index(drop=True))

    def test_engine_accounting_known_trade(self):
        market=fx.fixture_trade_market()
        out=fx.simulate(market,fx.Config(),market.t[0],market.t[-1]+60)
        self.assertEqual(len(out['trades']),1)
        trade=out['trades'][0]
        self.assertEqual(trade['exit_reason'],'TP')
        self.assertAlmostEqual(trade['net_pnl'],trade['gross_pnl']-trade['commission'])
        self.assertAlmostEqual(out['ending_balance'],100000+trade['net_pnl'])
        self.assertEqual(trade['entry_ticks'],100000)

    def test_gap_position_penalized_not_deleted(self):
        market=fx.fixture_trade_market(gap=True)
        out=fx.simulate(market,fx.Config(),market.t[0],market.t[-1]+60)
        self.assertEqual(len(out['trades']),1)
        self.assertEqual(out['trades'][0]['exit_reason'],'COVERAGE_GAP_STOP')
        self.assertLess(out['trades'][0]['net_r'],-1)

    def test_no_forced_final_exit(self):
        market=fx.fixture_trade_market(no_exit=True)
        out=fx.simulate(market,fx.Config(),market.t[0],market.t[-1]+60)
        self.assertEqual(out['trades'],[])
        self.assertIsNotNone(out['open_position'])

    def test_drawdown_includes_entry_fee_before_recovery(self):
        market=fx.fixture_trade_market()
        out=fx.simulate(market,fx.Config(),market.t[0],market.t[-1]+60)
        half=out['trades'][0]['commission']/2
        self.assertGreaterEqual(out['max_marked_dd_pct']+1e-12,100*half/100000)

if __name__=='__main__': unittest.main()
