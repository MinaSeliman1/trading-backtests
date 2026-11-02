"""Durable generic event outbox; acknowledge only after successful publication."""
from pathlib import Path
import json,uuid

def atomic(path,value):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);temp=path.with_suffix('.tmp-'+uuid.uuid4().hex)
 temp.write_text(json.dumps(value,indent=2,allow_nan=False),encoding='utf-8');temp.replace(path)

class Outbox:
 def __init__(self,path):
  self.path=Path(path);self.data=json.loads(self.path.read_text(encoding='utf-8')) if self.path.exists() else dict(observed={},pending=[],sent_dates={})
 @property
 def pending(self):return self.data['pending']
 def observe(self,issues,stamp):
  for bot,codes in issues.items():
   current=sorted(codes);previous=self.data['observed'].get(bot,[])
   nonrecovering={'decision_missing','decision_late','data_delayed','orb_missed_entry','orb_observation_gap','ledger_paused'}
   if current!=previous:
    if current or not set(previous)<=nonrecovering:self.pending.append(dict(bot=bot,codes=current,stamp=stamp,key='incident-'+uuid.uuid4().hex))
    self.data['observed'][bot]=current
  atomic(self.path,self.data)
 def flush(self,send,stamp):
  day=stamp[:10];count=self.data['sent_dates'].get(day,0);done=0
  self.data['sent_dates']={d:n for d,n in self.data['sent_dates'].items() if d>=day}
  while self.pending and count<30:
   event=self.pending[0]
   try:send(event['bot'],set(event['codes']),event['stamp'],event['key'])
   except Exception:break
   self.pending.pop(0);count+=1;done+=1;self.data['sent_dates'][day]=count;atomic(self.path,self.data)
  return done
