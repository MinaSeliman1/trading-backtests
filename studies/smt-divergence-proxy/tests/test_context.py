from pathlib import Path
from types import SimpleNamespace
import sys
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from smt.context import random_controls

def test_control_seed_is_date_keyed_and_shared():
 dates=pd.to_datetime(['2026-01-05','2026-01-06','2026-01-07'])
 sides,minutes=random_controls(dates);s2,m2=random_controls(dates[1:])
 assert np.array_equal(sides[1:],s2) and np.array_equal(minutes[:,1:],m2)
 assert minutes.shape==(1000,3) and minutes.min()>=332 and minutes.max()<=420
