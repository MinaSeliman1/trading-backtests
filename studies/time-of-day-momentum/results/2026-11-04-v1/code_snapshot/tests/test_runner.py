from pathlib import Path
import importlib.util,sys,uuid,shutil
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from test_engine import market


def test_full_runner_executes_all_96_synthetic_accounts_without_market_data(monkeypatch):
    root=Path(__file__).resolve().parents[1]
    spec=importlib.util.spec_from_file_location('seasonal_runner',root/'scripts/run_study.py');runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
    spy=market();spy.symbol='SPY';qqq=market(negative=True);qqq.symbol='QQQ'
    dates=[str(x.date()) for x in spy.dates]
    monkeypatch.setattr(runner,'PERIODS',dict(ALL=(dates[0],dates[-1]),A=(dates[0],dates[34]),B=(dates[35],dates[-1])))
    monkeypatch.setattr(runner,'load_sources',lambda:({'SPY':spy,'QQQ':qqq},{},dict(synthetic_fixture=True)))
    out=root/'runtime'/('synthetic-'+uuid.uuid4().hex)
    monkeypatch.setattr(sys,'argv',['run_study.py','--out',str(out)])
    try:
        runner.main()
        import json,pandas as pd
        assert len(pd.read_csv(out/'comparison_all.csv'))==96
        assert json.loads((out/'RUN_COMPLETE.json').read_text())['executions']==96
        assert json.loads((out/'PRE_EXECUTION_PROTOCOL.json').read_text())['source']['synthetic_fixture']
        assert (out/'SCREENING.json').exists() and (out/'QQQ_ALL_controls.json').exists()
    finally:
        # This directory is an exclusively owned synthetic fixture under ignored runtime.
        assert out.resolve().is_relative_to((root/'runtime').resolve())
        shutil.rmtree(out,ignore_errors=True)
