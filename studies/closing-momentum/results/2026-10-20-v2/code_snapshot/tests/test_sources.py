from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import pytest
from run_study import verify_hashes,validate_market,main
from test_engine import market


def test_tampered_source_fails_before_loading(tmp_path):
    (tmp_path/'data').write_bytes(b'abcd')
    with pytest.raises(ValueError,match='hash mismatch'):verify_hashes(tmp_path,{'data':'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad'})


def test_complete_calendar_is_required_not_just_sorted_dates():
    m=market();m.dates=m.dates.map(lambda d:d.replace(day=26) if d.day==29 else d)
    with pytest.raises(ValueError,match='continuity'):validate_market(m)


def test_non_float64_data_is_refused():
    m=market();m.arrays['open']=m.arrays['open'].astype('float32')
    with pytest.raises(ValueError,match='precision'):validate_market(m)


def test_existing_execution_is_never_overwritten(tmp_path):
    p=tmp_path/'saved.txt';p.write_text('existing evidence')
    with pytest.raises(SystemExit,match='overwrite'):main(['--out',str(tmp_path)])
    assert p.read_text()=='existing evidence'
