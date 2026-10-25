import importlib.util
from pathlib import Path
import math
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('nowick_reference', ROOT / 'reference.py')
ref = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ref)


class ReferenceTests(unittest.TestCase):
    def test_pips(self):
        self.assertEqual(ref.pip_size('JPY'), .01)
        self.assertEqual(ref.pip_size('USD'), .0001)

    def test_verify_ticks(self):
        for pip, tick, expected in [(.01,.001,10),(.0001,.00001,10),(.01,.01,1),(.0001,.0001,1)]:
            self.assertEqual(ref.verify_ticks(pip,tick),expected)

    def test_wilson_empty(self):
        self.assertIsNone(ref.wilson(0,0))

    def test_wilson_half(self):
        lo,hi=ref.wilson(50,100)
        self.assertAlmostEqual(lo,.40383153,places=7)
        self.assertAlmostEqual(hi,.59616847,places=7)

    def test_wilson_extremes(self):
        self.assertAlmostEqual(ref.wilson(0,100)[0],0)
        self.assertAlmostEqual(ref.wilson(100,100)[1],1)

    def test_risk_units(self):
        q=ref.risk_qty(100000,.001,1,1)
        self.assertEqual(q,1000000)
        self.assertLessEqual(q*.001,1000)

    def test_risk_rounding(self):
        self.assertEqual(ref.risk_qty(100,.003,1,1000),0)
        self.assertEqual(ref.risk_qty(100000,.00103,1,1000),970000)

    def test_invalid_risk(self):
        for dist in [0,-1,float('nan')]:
            self.assertEqual(ref.risk_qty(100000,dist,1,1),0)

    def test_nowick_zero_tolerance(self):
        self.assertEqual(ref.nowick(1.10,1.12,1.10,1.11,0,.00001),1)
        self.assertEqual(ref.nowick(1.10,1.10,1.08,1.09,0,.00001),-1)
        self.assertEqual(ref.nowick(1.10,1.12,1.09999,1.11,0,.00001),0)
        self.assertEqual(ref.nowick(1.1,1.12,1.08,1.1,0,.00001),0)

    def test_nowick_tolerance(self):
        self.assertEqual(ref.nowick(1.10,1.12,1.09999,1.11,1,.00001),1)

    def test_ttl_exact(self):
        self.assertFalse(ref.pending_live(100,100,9))
        self.assertTrue(ref.pending_live(101,100,9))
        self.assertTrue(ref.pending_live(109,100,9))
        self.assertFalse(ref.pending_live(110,100,9))

    def test_session_dst_winter(self):
        self.assertTrue(ref.in_session('2026-01-05T07:00:00+00:00'))
        self.assertFalse(ref.in_session('2026-01-05T13:00:00+00:00'))

    def test_session_dst_summer(self):
        self.assertTrue(ref.in_session('2026-07-06T06:00:00+00:00'))
        self.assertFalse(ref.in_session('2026-07-06T12:00:00+00:00'))

    def test_news_overlap_and_date(self):
        news='2026-07-06@0715-0800;2026-07-07@0200-0230'
        self.assertTrue(ref.news_overlap('2026-07-06T11:00:00+00:00','2026-07-06T11:30:00+00:00',news))
        self.assertFalse(ref.news_overlap('2026-07-08T11:15:00+00:00','2026-07-08T11:30:00+00:00',news))
        self.assertFalse(ref.news_overlap('2026-07-06T11:00:00+00:00','2026-07-06T11:15:00+00:00',news))

    def test_bad_news(self):
        for text in ['oops','2026-07-06@0800-0700','2026-02-30@0200-0300']:
            with self.assertRaises(ValueError): ref.parse_news(text)

    def test_fill_rejects_cross_session_data_gap(self):
        self.assertFalse(ref.fill_allowed('2026-07-06T07:15:00+00:00','2026-07-07T07:15:00+00:00','2026-07-07T07:30:00+00:00'))

    def test_fill_accepts_contiguous_allowed_bar(self):
        self.assertTrue(ref.fill_allowed('2026-07-06T07:15:00+00:00','2026-07-06T07:15:00+00:00','2026-07-06T07:30:00+00:00'))

    def test_fill_rejects_news_later_in_same_bar(self):
        self.assertFalse(ref.fill_allowed('2026-07-06T10:45:00+00:00','2026-07-06T10:45:00+00:00','2026-07-06T11:00:00+00:00','2026-07-06@0650-0655'))

    def test_fill_rejects_outside_session(self):
        self.assertFalse(ref.fill_allowed('2026-07-06T12:00:00+00:00','2026-07-06T12:00:00+00:00','2026-07-06T12:15:00+00:00'))

    def test_pivot_only_after_confirmation(self):
        values=[1,2,3,4,5,10,5,4,3,2,1]
        self.assertIsNone(ref.confirmed_pivot(values[:10],5,True))
        self.assertEqual(ref.confirmed_pivot(values,5,True),10)

    def test_structure(self):
        self.assertEqual(ref.structure([2,3],[1,2]),1)
        self.assertEqual(ref.structure([3,2],[2,1]),-1)
        self.assertEqual(ref.structure([2,3],[2,1]),0)
        self.assertEqual(ref.structure([2],[1,2]),0)

    def test_sr_strict_between(self):
        self.assertTrue(ref.sr_blocks(1,1.1,1.11,[1.105]))
        self.assertFalse(ref.sr_blocks(1,1.1,1.11,[1.11,1.1]))
        self.assertTrue(ref.sr_blocks(-1,1.1,1.09,[1.095]))

    def test_double_gap(self):
        self.assertEqual([ref.double_blocks(i,100) for i in range(101,106)],[False,True,True,True,False])

    def test_breakeven(self):
        for stop,wr in [(5,.6),(10,.55),(20,.525),(30,31/60)]:
            self.assertAlmostEqual(ref.breakeven(stop,1,1),wr)
        self.assertAlmostEqual(ref.breakeven(10,1,2),1.1/3)

    def test_cost_both_currencies(self):
        self.assertEqual(2*.00005/ref.pip_size('USD'),1)
        self.assertEqual(2*.005/ref.pip_size('JPY'),1)

    def test_stress_never_improves_trade(self):
        for pnl in [1000,-500,-2000]:
            self.assertLessEqual(ref.stressed_pnl(pnl,1000,100,True),pnl)
            self.assertEqual(ref.stressed_pnl(pnl,1000,100,False),pnl)
        self.assertEqual(ref.stressed_pnl(1000,1000,100,True),-1100)

    def test_drawdown_and_streak(self):
        stats=ref.r_stats([1,-1,-1,0,1,-1,-1,-1])
        self.assertEqual(stats['longest_loss_streak'],3)
        self.assertEqual(stats['max_closed_dd_r'],4)
        self.assertEqual(stats['mean_r'],-.375)


if __name__=='__main__': unittest.main()
