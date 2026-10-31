from pathlib import Path
import importlib.util
import pytest
from test_engine import setup,run
from relative.engine import Config
path=Path(__file__).resolve().parents[1]/'scripts/run_study.py';spec=importlib.util.spec_from_file_location('relative_runner_test',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

def test_summary_row_merges_config_and_statistics_without_duplicate_keyword():
 r=run(setup());row=module.assemble('sample','ALL','reference','2024-02-06','2024-02-06',Config(),r)
 assert row['label']=='sample' and row['pairs']==1 and row['initial_capital']==100000
 assert row['net_pnl']==pytest.approx(71.78425)
