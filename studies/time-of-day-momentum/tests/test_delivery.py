from pathlib import Path
import importlib.util,sys,hashlib
import pytest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
spec=importlib.util.spec_from_file_location('seasonal_verify',ROOT/'scripts/verify_delivery.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)


def fixture(tmp_path):
    repo=tmp_path/'repo';study=repo/'study';out=study/'results/run';(out/'code_snapshot').mkdir(parents=True)
    code=study/'code.py';code.write_text('original');(out/'code_snapshot/code.py').write_bytes(code.read_bytes())
    f=dict(code_sha256={'code.py':hashlib.sha256(code.read_bytes()).hexdigest()},dependencies_sha256={})
    return repo,study,out,code,f


def test_current_source_mutation_cannot_be_sealed_with_old_snapshot(tmp_path):
    repo,study,out,code,f=fixture(tmp_path);mod.verify_freeze(f,out,study,repo)
    code.write_text('changed after freeze')
    with pytest.raises(AssertionError,match='current code'):mod.verify_freeze(f,out,study,repo)


def test_corrupt_snapshot_is_refused(tmp_path):
    repo,study,out,code,f=fixture(tmp_path);(out/'code_snapshot/code.py').write_text('corrupt')
    with pytest.raises(AssertionError,match='frozen code'):mod.verify_freeze(f,out,study,repo)


def test_execution_folder_must_stay_inside_study(tmp_path):
    study=tmp_path/'study';study.mkdir()
    with pytest.raises(ValueError):mod.execution_folder(tmp_path/'outside',study)


def test_protocol_text_and_current_document_are_bound(tmp_path):
    repo,study,out,code,f=fixture(tmp_path);doc=study/'PROTOCOL_EXECUTION.md';doc.write_text('fixed rules')
    f['protocols']={'PROTOCOL_EXECUTION.md':dict(text='fixed rules',sha256=hashlib.sha256(doc.read_bytes()).hexdigest())}
    mod.verify_freeze(f,out,study,repo);doc.write_text('changed rules')
    with pytest.raises(AssertionError,match='current protocol'):mod.verify_freeze(f,out,study,repo)


def test_delivery_cannot_seal_ignored_runtime_output(tmp_path):
    study=tmp_path/'study';study.mkdir()
    with pytest.raises(ValueError):mod.execution_folder(study/'runtime/hidden',study)
