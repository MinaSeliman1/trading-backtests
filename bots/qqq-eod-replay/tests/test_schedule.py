import pandas as pd
from qqq_eod import schedule as s

def test_future_and_weekend_are_never_due():
 assert s.due_sessions('2026-11-02',pd.Timestamp('2026-11-01T18:00:00Z'))==[]
 assert s.due_sessions('2026-11-02',pd.Timestamp('2026-11-02T21:16:59Z'))==[]
 assert s.due_sessions('2026-11-02',pd.Timestamp('2026-11-02T21:17:00Z'))==['2026-11-02']

def test_dst_uses_new_york_clock_not_fixed_offset():
 assert s.due_sessions('2026-10-30',pd.Timestamp('2026-10-30T20:17:00Z'))==['2026-10-30']
 assert s.due_sessions('2026-11-02',pd.Timestamp('2026-11-02T20:17:00Z'))==[]

def test_half_day_and_holiday():
 assert s.due_sessions('2026-11-26',pd.Timestamp('2026-11-27T18:16:59Z'))==[]
 assert s.due_sessions('2026-11-26',pd.Timestamp('2026-11-27T18:17:00Z'))==['2026-11-27']

def test_capture_classification_uses_next_actual_session():
 assert s.capture_kind('2026-11-27',pd.Timestamp('2026-11-30T14:29:59Z'))=='timely_eod'
 assert s.capture_kind('2026-11-27',pd.Timestamp('2026-11-30T14:30:00Z'))=='catchup'
