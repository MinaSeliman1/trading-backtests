from pathlib import Path
import sys, json, os
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pytest
from orb_shadow.status import write_status


def test_temporary_replace_denial_is_retried(tmp_path,monkeypatch):
    original=Path.replace;attempts=[]
    def replace(self,target):
        attempts.append(True)
        if len(attempts)<3:raise PermissionError(13,'locked')
        return original(self,target)
    monkeypatch.setattr(Path,'replace',replace)
    assert write_status(tmp_path,state='active',utc='test')
    assert len(attempts)==3 and json.loads((tmp_path/'status.json').read_text())['state']=='active'
    assert not list(tmp_path.glob('*.tmp'))


def test_persistent_io_failure_preserves_old_status_and_does_not_raise(tmp_path,monkeypatch):
    (tmp_path/'status.json').write_text('{"state":"old"}')
    def deny(*args):raise PermissionError(13,'private provider text must not be logged')
    monkeypatch.setattr(Path,'replace',deny)
    assert write_status(tmp_path,state='active') is False
    assert json.loads((tmp_path/'status.json').read_text())['state']=='old'
    assert not list(tmp_path.glob('*.tmp'))


@pytest.mark.skipif(os.name!='nt',reason='native Windows file sharing')
def test_windows_reader_without_delete_sharing_cannot_kill_writer(tmp_path):
    import ctypes
    from ctypes import wintypes
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.CreateFileW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE]
    kernel.CreateFileW.restype=wintypes.HANDLE
    kernel.CloseHandle.argtypes=[wintypes.HANDLE]
    path=tmp_path/'status.json';path.write_text('{"state":"old"}')
    handle=kernel.CreateFileW(str(path),0x80000000,1|2,None,3,0,None)
    assert handle!=ctypes.c_void_p(-1).value
    try:
        other=tmp_path/'old-writer.tmp';other.write_text('{}')
        with pytest.raises(PermissionError):other.replace(path)
        assert write_status(tmp_path,state='active') is False
        assert json.loads(path.read_text())['state']=='old'
    finally:kernel.CloseHandle(handle)
    assert write_status(tmp_path,state='active')
    assert json.loads(path.read_text())['state']=='active'
