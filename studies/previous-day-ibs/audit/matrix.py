"""Bind every scenario and summary to the pre-execution Cartesian product."""
import json,math
import pandas as pd
def equal(expected,actual):
    if expected is None:
        return bool(pd.isna(actual) or isinstance(actual,(int,float)) and not math.isfinite(actual))
    if isinstance(expected,(int,float)) and not isinstance(expected,bool):
        return math.isclose(float(expected),float(actual),rel_tol=1e-12,abs_tol=1e-10)
    return bool(expected==actual)

def validate_matrix(matrix,out):
    frozen=json.loads((out/'PRE_EXECUTION_PROTOCOL.json').read_text(encoding='utf-8'))
    expected={(s,p,v):f'{s}_{p}_{v}' for s in frozen['symbols'] for p in frozen['periods'] for v in frozen['specifications']}
    assert len(expected)==frozen['executions']==len(matrix),'scenario count'
    assert matrix.label.is_unique and not matrix.duplicated(['symbol','period','variant']).any(),'duplicate scenarios'
    actual={(r.symbol,r.period,r.variant):r.label for r in matrix.itertuples()}
    assert actual==expected,'scenario membership'
    checks=3
    for _,row in matrix.iterrows():
        assert [row.start,row.end]==frozen['periods'][row.period],'period boundaries';checks+=1
        for field,value in frozen['specifications'][row.variant].items():
            assert equal(value,row[field]),f'{row.label} frozen {field}';checks+=1
        summary=json.loads((out/row.label/'summary.json').read_text(encoding='utf-8'))
        assert set(summary)==set(matrix.columns),f'{row.label} summary schema';checks+=1
        for field,value in summary.items():
            assert equal(value,row[field]),f'{row.label} summary {field}';checks+=1
    return checks
