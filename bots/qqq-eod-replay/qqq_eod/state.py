"""Authenticated private state archives for a public Actions repository."""
from pathlib import Path,PurePosixPath
import base64,io,json,os,stat,zipfile
MAGIC=b'QQQEOD1\x00'
MAX_CIPHER=4*1024*1024
MAX_UNPACKED=128*1024*1024
MAX_MEMBERS=10000

def aad(identity):return json.dumps(identity,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')
def key_bytes(value):
 try:key=base64.b64decode(value,validate=True)
 except Exception:raise ValueError('invalid state key format') from None
 if len(key)!=32:raise ValueError('state key must contain 32 bytes')
 return key

def safe_name(name):
 p=PurePosixPath(name)
 if '\\' in name or p.is_absolute() or '..' in p.parts or not p.parts:raise ValueError('unsafe archive path')
 allowed=name in ('statistical.sqlite','operational.sqlite','state.json','checkpoint.json') or p.parts[0] in ('inputs','attempts','exports')
 if not allowed or p.suffix not in ('.json','.csv','.sqlite'):raise ValueError('unexpected state member')
 return p

def seal_folder(folder,key,identity):
 from cryptography.hazmat.primitives.ciphers.aead import AESGCM
 root=Path(folder).resolve();buf=io.BytesIO();total=0;files=0
 with zipfile.ZipFile(buf,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
  for path in sorted(root.rglob('*')):
   if path.is_symlink():raise ValueError('state symlink refused')
   if not path.is_file():continue
   if path.name.endswith(('-wal','-shm')):
    if path.stat().st_size:raise ValueError('SQLite must be closed or consistently backed up')
    continue
   name=path.relative_to(root).as_posix();safe_name(name);total+=path.stat().st_size;files+=1
   if total>MAX_UNPACKED or files>MAX_MEMBERS:raise ValueError('state storage safety limit')
   archive.write(path,name)
 nonce=os.urandom(12);blob=MAGIC+nonce+AESGCM(key_bytes(key)).encrypt(nonce,buf.getvalue(),aad(identity))
 if len(blob)>MAX_CIPHER:raise ValueError('state exceeds free-storage budget; archive review needed')
 return blob

def open_folder(blob,key,identity,target):
 from cryptography.hazmat.primitives.ciphers.aead import AESGCM
 from cryptography.exceptions import InvalidTag
 target=Path(target)
 if target.exists() and any(target.iterdir()):raise ValueError('state overwrite refused')
 if len(blob)>MAX_CIPHER or not blob.startswith(MAGIC) or len(blob)<len(MAGIC)+28:raise ValueError('invalid encrypted state')
 pos=len(MAGIC);nonce=blob[pos:pos+12]
 try:raw=AESGCM(key_bytes(key)).decrypt(nonce,blob[pos+12:],aad(identity))
 except (InvalidTag,ValueError):raise ValueError('state authentication failed') from None
 with zipfile.ZipFile(io.BytesIO(raw)) as archive:
  infos=archive.infolist()
  if len(infos)>MAX_MEMBERS or sum(i.file_size for i in infos)>MAX_UNPACKED:raise ValueError('state archive limits exceeded')
  names=[]
  for info in infos:
   name=safe_name(info.filename)
   if info.is_dir() or stat.S_ISLNK(info.external_attr>>16) or str(name) in names:raise ValueError('unsafe or duplicate archive member')
   names.append(str(name))
  target.mkdir(parents=True,exist_ok=True)
  for info in infos:
   path=target/PurePosixPath(info.filename);path.parent.mkdir(parents=True,exist_ok=True)
   with path.open('xb') as stream:stream.write(archive.read(info))
 return target
