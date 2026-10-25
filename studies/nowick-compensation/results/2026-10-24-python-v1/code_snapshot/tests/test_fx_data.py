import sys
from pathlib import Path
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import fx_data as data

HEADER='DateTime,BidOpen,BidHigh,BidLow,BidClose,AskOpen,AskHigh,AskLow,AskClose\n'

class DataTests(unittest.TestCase):
    def test_decode_tick_sizes_and_utc(self):
        text=HEADER+'01/03/2017 06:00:00.000,1.20001,1.20010,1.20000,1.20005,1.20011,1.20020,1.20010,1.20015\n'
        df=data.decode_csv(text.encode(),'GBPUSD')
        self.assertEqual(df.iloc[0].bo,120001)
        self.assertEqual(str(df.index[0]),'2017-01-03 06:00:00+00:00')

    def test_jpy(self):
        text=HEADER+'01/03/2017 06:00:00.000,115.001,115.010,115.000,115.005,115.011,115.020,115.010,115.015\n'
        self.assertEqual(data.decode_csv(text.encode(),'USDJPY').iloc[0].bo,115001)

    def test_invalid_ohlc_flagged_not_repaired(self):
        text=HEADER+'01/03/2017 06:00:00.000,1.2,1.1,1.0,1.2,1.21,1.22,1.20,1.21\n'
        df=data.decode_csv(text.encode(),'AUDUSD')
        self.assertFalse(df.iloc[0].valid_bid)

    def test_conflicting_duplicates_fail(self):
        a=data.decode_csv((HEADER+'01/03/2017 06:00:00.000,1.2,1.2,1.2,1.2,1.21,1.21,1.21,1.21\n').encode(),'AUDUSD')
        b=a.copy(); b.iloc[0,b.columns.get_loc('bc')]=120001
        with self.assertRaises(ValueError): data.combine_frames([a,b])

    def test_identical_duplicates_counted(self):
        a=data.decode_csv((HEADER+'01/03/2017 06:00:00.000,1.2,1.2,1.2,1.2,1.21,1.21,1.21,1.21\n').encode(),'AUDUSD')
        df,report=data.combine_frames([a,a.copy()])
        self.assertEqual(len(df),1)
        self.assertEqual(report['identical_duplicate_rows'],1)

    def test_subtick_precision_refused(self):
        text=HEADER+'01/03/2017 06:00:00.000,1.200001,1.20001,1.2,1.2,1.21,1.21,1.21,1.21\n'
        with self.assertRaises(ValueError): data.decode_csv(text.encode(),'AUDUSD')

if __name__=='__main__': unittest.main()
