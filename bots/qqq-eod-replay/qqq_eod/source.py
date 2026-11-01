"""Read-only transport and append-only market evidence; no broker access."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,uuid,re
import numpy as np
import pandas as pd
FIELDS=('open','high','low','close','volume')
DATA='https://data.alpaca.markets'

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def canonical_frame(frame):
 if not isinstance(frame.index,pd.DatetimeIndex) or frame.index.tz is None:raise ValueError('aware minute index required')
 if any(k not in frame for k in FIELDS):raise ValueError('missing OHLCV columns')
 f=frame.loc[:,list(FIELDS)].copy();f.index=f.index.tz_convert('UTC');f.index.name='timestamp'
 if not (f.index==f.index.floor('min')).all():raise ValueError('off-minute quote')
 f=f.reset_index().drop_duplicates().set_index('timestamp').sort_index()
 if f.index.has_duplicates:raise ValueError('conflicting minute prices')
 for k in FIELDS:f[k]=pd.to_numeric(f[k],errors='raise').astype(float)
 x=f.loc[:,['open','high','low','close']];v=f.volume
 if len(f) and ((~np.isfinite(x).all(axis=1))|(x.min(axis=1)<=0)|(~np.isfinite(v))|(v<0)|(f.high<x.max(axis=1))|(f.low>x.min(axis=1))).any():raise ValueError('invalid OHLCV')
 return f

class QQQDataOnly:
 def __init__(self,transport):self.transport=transport
 def request(self,origin,path,method='GET',params=None,body=None):
  if origin!=DATA or method!='GET' or body is not None:raise ValueError('replay permits only QQQ data GET')
  p=params or {}
  bars=path=='/v2/stocks/QQQ/bars' and p.get('feed')=='sip' and p.get('timeframe')=='1Min' and p.get('adjustment')=='raw'
  dividend=path=='/v1/corporate-actions' and p.get('symbols')=='QQQ'
  if not (bars or dividend):raise ValueError('unapproved replay data route')
  return self.transport.request(origin,path,method,params=params)
 def clear(self):self.transport.clear()

def capture(folder,frame,metadata):
 if any(re.search(r'key|secret|token|authorization|password',str(k),re.I) for k in metadata):raise ValueError('sensitive metadata key refused')
 f=canonical_frame(frame);now=datetime.now(timezone.utc);root=Path(folder)/('capture-'+now.strftime('%Y%m%dT%H%M%S%fZ')+'-'+uuid.uuid4().hex[:12]);root.mkdir(parents=True,exist_ok=False)
 target=root/'bars.csv'
 with target.open('x',encoding='utf-8',newline='') as stream:f.to_csv(stream,index_label='timestamp',lineterminator='\n',float_format='%.17g')
 receipt=dict(schema=1,captured_utc=now.isoformat(),rows=len(f),bars_sha256=sha(target),metadata=metadata)
 with (root/'receipt.json').open('x',encoding='utf-8') as stream:json.dump(receipt,stream,indent=2,allow_nan=False)
 return dict(receipt,directory=str(root.resolve()))


def verify_sources(folder,lock):
 root=Path(folder).resolve()
 for relative,digest in lock['source_files'].items():
  target=(root/relative).resolve()
  if not target.is_relative_to(root) or not target.is_file() or sha(target)!=digest:raise ValueError('pinned strategy source mismatch')
 return root

def freeze_sources(repo,lock,folder):
 import subprocess
 if not re.fullmatch(r'[0-9a-f]{40}',lock['strategy_commit']):raise ValueError('full commit SHA required')
 root=Path(folder).resolve();root.mkdir(parents=True,exist_ok=True)
 for relative,digest in lock['source_files'].items():
  target=(root/relative).resolve()
  if not target.is_relative_to(root) or not relative.endswith('.py'):raise ValueError('unsafe source path')
  if target.exists():
   if sha(target)!=digest:raise ValueError('pinned source overwrite refused')
   continue
  raw=subprocess.check_output(['git','show',lock['strategy_commit']+':'+relative],cwd=repo,stderr=subprocess.DEVNULL)
  if hashlib.sha256(raw).hexdigest()!=digest:raise ValueError('Git source mismatch')
  target.parent.mkdir(parents=True,exist_ok=True)
  with target.open('xb') as stream:stream.write(raw)
 return verify_sources(root,lock)

def activate_sources(folder,lock):
 import sys
 root=verify_sources(folder,lock)
 prefixes=('qqq_paper','orb_shadow','noise_area','orb')
 for name,module in list(sys.modules.items()):
  if name.split('.')[0] in prefixes and getattr(module,'__file__',None) and not Path(module.__file__).resolve().is_relative_to(root):raise RuntimeError('another strategy version is already imported')
 paths=['bots/qqq-noise-area','bots/qqq-orb','studies/intraday-momentum-noise-area','studies/opening-range-5m']
 for path in reversed(paths):sys.path.insert(0,str(root/path))
 return root
