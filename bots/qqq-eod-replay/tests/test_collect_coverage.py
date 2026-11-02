from pathlib import Path
import importlib.util

def script():
 path=Path(__file__).resolve().parents[1]/'scripts/collect_live.py';spec=importlib.util.spec_from_file_location('collect_coverage',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def test_missing_and_unresolved_cloud_dates_are_not_reported_as_complete():
 m=script();stats=dict(first_day='2026-11-02',sessions=[])
 assert not m.coverage_errors(stats,'2026-11-02T03:00:00Z')
 errors=m.coverage_errors(stats,'2026-11-02T23:35:00Z');assert len(errors)==2 and stats['sessions']==[]
 stats['sessions']=[dict(bot='noise',day='2026-11-02',status='complete'),dict(bot='orb',day='2026-11-02',status='unresolved')]
 errors=m.coverage_errors(stats,'2026-11-02T23:35:00Z');assert len(errors)==1 and errors[0]['bot']=='orb'

def test_halfday_coverage_deadline_uses_actual_exchange_close():
 m=script();stats=dict(first_day='2026-11-27',sessions=[])
 assert not m.coverage_errors(stats,'2026-11-27T18:16:00Z')
 assert len(m.coverage_errors(stats,'2026-11-27T18:18:00Z'))==2
