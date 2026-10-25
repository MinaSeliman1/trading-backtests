import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fx_metrics import summarize

def trade(pnl,r,reason='TP'):
    return dict(net_pnl=pnl,net_r=r,commission=10,gross_pnl=pnl+10,exit_reason=reason,entry_time=100,exit_time=200,holding_minutes=1,ambiguous_front_run=False,dual_touch=False,crossed_gap=False,d=1)

class MetricTests(unittest.TestCase):
    def test_net_accounting_and_pf(self):
        out={'trades':[trade(90,.9),trade(-110,-1.1,'SL')],'ending_balance':99980,'ending_equity':99980,'open_position':None,'counters':{},'max_marked_dd_pct':1.1}
        s=summarize(out,0,31557600)
        self.assertEqual(s['closed_trades'],2)
        self.assertAlmostEqual(s['profit_factor'],90/110)
        self.assertAlmostEqual(s['expectancy_r'],-.1)
        self.assertEqual(s['commission'],20)
        self.assertAlmostEqual(s['max_closed_dd_r'],1.1)

    def test_gap_penalties_not_counted_as_resolved(self):
        out={'trades':[trade(-110,-1.1,'COVERAGE_GAP_STOP')],'ending_balance':99890,'ending_equity':99890,'open_position':None,'counters':{},'max_marked_dd_pct':.11}
        s=summarize(out,0,31557600)
        self.assertEqual(s['resolved_closed_trades'],0)
        self.assertEqual(s['coverage_penalty_trades'],1)
        self.assertFalse(s['minimum_100_resolved'])

    def test_no_trades_is_missing_not_zero_wr(self):
        out={'trades':[],'ending_balance':100000,'ending_equity':100000,'open_position':None,'counters':{},'max_marked_dd_pct':0}
        s=summarize(out,0,31557600)
        self.assertIsNone(s['win_rate_pct'])
        self.assertIsNone(s['profit_factor'])
        self.assertIsNone(s['wilson_low_pct'])

if __name__=='__main__': unittest.main()
