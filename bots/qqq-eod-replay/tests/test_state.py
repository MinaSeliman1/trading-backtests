import base64,json,zipfile,io,os
from pathlib import Path
import pytest
from qqq_eod import state as s
KEY=base64.b64encode(bytes(range(32))).decode()
ID={'generation':'test','strategy':'sha','deps':'pinned','rule':'sha'}

def test_state_roundtrip_is_private_and_non_deterministic(tmp_path):
 root=tmp_path/'state';root.mkdir();(root/'state.json').write_text('{"private":"marketdata"}')
 a=s.seal_folder(root,KEY,ID);b=s.seal_folder(root,KEY,ID)
 assert a!=b and b'marketdata' not in a
 s.open_folder(a,KEY,ID,tmp_path/'restored')
 assert (tmp_path/'restored/state.json').read_text()=='{"private":"marketdata"}'

def test_tamper_wrong_version_and_wrong_key_fail(tmp_path):
 root=tmp_path/'state';root.mkdir();(root/'state.json').write_text('{}');blob=s.seal_folder(root,KEY,ID)
 for value,key,identity in [(blob[:-1]+bytes([blob[-1]^1]),KEY,ID),(blob,base64.b64encode(bytes(32)).decode(),ID),(blob,KEY,dict(ID,rule='changed'))]:
  with pytest.raises(ValueError):s.open_folder(value,key,identity,tmp_path/'restored')
 assert not (tmp_path/'restored/state.json').exists()

def test_no_sqlite_wal_or_unsafe_files_in_snapshot(tmp_path):
 (tmp_path/'statistical.sqlite-wal').write_bytes(b'pending')
 with pytest.raises(ValueError):s.seal_folder(tmp_path,KEY,ID)

def test_restore_refuses_overwrite(tmp_path):
 root=tmp_path/'state';root.mkdir();(root/'state.json').write_text('{}');blob=s.seal_folder(root,KEY,ID)
 with pytest.raises(ValueError):s.open_folder(blob,KEY,ID,root)

def test_authenticated_zip_still_cannot_escape_target(tmp_path):
 root=tmp_path/'x';root.mkdir();(root/'state.json').write_text('{}');s.seal_folder(root,KEY,ID)
 from cryptography.hazmat.primitives.ciphers.aead import AESGCM
 f=io.BytesIO()
 with zipfile.ZipFile(f,'w') as z:z.writestr('../escaped.json','bad')
 nonce=os.urandom(12);blob=s.MAGIC+nonce+AESGCM(base64.b64decode(KEY)).encrypt(nonce,f.getvalue(),s.aad(ID))
 with pytest.raises(ValueError):s.open_folder(blob,KEY,ID,tmp_path/'restore')
 assert not (tmp_path/'escaped.json').exists()
