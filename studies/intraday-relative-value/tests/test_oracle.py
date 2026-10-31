from dataclasses import asdict
from types import SimpleNamespace
from pathlib import Path
import sys,importlib.util,math
import pytest
from test_engine import markets,setup,bar
from relative.engine import Config
path=Path(__file__).resolve().parents[1]/'audit/independent.py'
spec=importlib.util.spec_from_file_location('scalar_relative_oracle',path);oracle=importlib.util.module_from_spec(spec);spec.loader.exec_module(oracle)

def h():return ('ready',{j:(0.,.001) for j in range(29,300,5)})

def test_scalar_same_clock_estimator_has_hand_computed_values():
 reason,stats=oracle.histories(markets(),20)[-1]
 assert reason=='ready' and stats[29][0]==pytest.approx(.00005) and stats[29][1]==pytest.approx(math.sqrt(35)*.0001)

def test_scalar_pair_has_hand_computed_four_fees_and_net():
 m=setup();r=oracle.replay_day(m,21,SimpleNamespace(**asdict(Config())),100000,h())
 assert r['reason']=='eligible' and r['pair']['net_pnl']==pytest.approx(71.78425)
 assert r['pair']['commission']==pytest.approx(7.007) and len(r['legs'])==2

def test_scalar_unknown_holding_preserves_known_costs():
 m=setup();bar(m,'SPY',30,close=math.nan);r=oracle.replay_day(m,21,SimpleNamespace(**asdict(Config())),100000,h())
 assert r['reason']=='unresolved_execution' and r['pair'] is None
 assert r['unknown']['known_entry_commission']==pytest.approx(3.5035)
 assert r['unknown']['known_entry_friction']==pytest.approx(10.01) and r['unknown']['known_borrow']==pytest.approx(1.38875)
