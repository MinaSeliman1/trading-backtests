"""A refused reproduction must preserve the original prepared price history."""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import unittest
import uuid
from unittest.mock import patch

SCRIPT=Path(__file__).resolve().parents[1]/'scripts/download_fxcm.py'
spec=importlib.util.spec_from_file_location('fx_acquisition_preservation',SCRIPT)
download=importlib.util.module_from_spec(spec)
spec.loader.exec_module(download)


@contextlib.contextmanager
def workspace_scratch():
    base=(SCRIPT.parents[1]/'.test_tmp_acquisition').resolve()
    root=base/uuid.uuid4().hex
    root.mkdir(parents=True)
    try:
        yield root
    finally:
        target=root.resolve()
        assert target.is_relative_to(base) and target!=base
        shutil.rmtree(target)


class AcquisitionPreservationTests(unittest.TestCase):
    def refused_reproduction(self,changed_archive):
        with workspace_scratch() as tmp:
            root=Path(tmp)
            archives=[]; prepared={}; originals={}
            for pair in ['GBPUSD','USDJPY','AUDUSD']:
                rawpath=f'data/fxcm_raw/{pair}/2015/1.csv.gz'
                payload=('raw-'+pair).encode()
                archives.append({'pair':pair,'year':2015,'week':1,'status':200,'path':rawpath,'sha256':hashlib.sha256(payload).hexdigest()})
                path=root/f'data/prepared/{pair}_m1.npz'
                path.parent.mkdir(parents=True,exist_ok=True)
                data=('original-prepared-'+pair).encode()
                path.write_bytes(data); originals[path]=data
                prepared[pair]={'path':path.relative_to(root).as_posix(),'sha256':hashlib.sha256(data).hexdigest()}
            baseline=root/'results/2026-10-24-python/source_manifest.json'
            baseline.parent.mkdir(parents=True)
            baseline.write_text(json.dumps({'complete':True,'archives':archives,'prepared':prepared}))
            old_manifest=baseline.read_bytes()

            def one(item):
                pair,year,week=item
                if year!=2015 or week!=1:
                    return {'pair':pair,'year':year,'week':week,'status':404,'sha256':'unused'}
                record=next(a for a in archives if a['pair']==pair).copy()
                payload=('raw-'+pair+('-changed' if changed_archive and pair=='GBPUSD' else '')).encode()
                target=root/record['path']; target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(payload)
                return record|{'sha256':hashlib.sha256(payload).hexdigest()}

            with patch.object(download,'ROOT',root),patch.object(download,'one',one), \
                 patch.object(download.gzip,'decompress',lambda value:value), \
                 patch.object(download,'decode_csv',lambda *args:None), \
                 patch.object(download,'combine_frames',lambda frames:({},{})), \
                 patch.object(download,'save_prepared',lambda frame,path:path.write_bytes(b'changed-preparation')), \
                 contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaises(SystemExit):
                    download.main()
            self.assertEqual(old_manifest,baseline.read_bytes())
            for path,data in originals.items():
                self.assertEqual(data,path.read_bytes(),'A refused reproduction replaced original data')

    def test_changed_vendor_archive_preserves_prepared_data(self):
        self.refused_reproduction(changed_archive=True)

    def test_changed_preparation_preserves_prepared_data(self):
        self.refused_reproduction(changed_archive=False)
