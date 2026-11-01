"""Trusted Actions checkpoint selection. Never fall back after a lost head."""
import base64,json,re,io,zipfile
from urllib.request import Request,build_opener,HTTPRedirectHandler,urlopen
from urllib.error import HTTPError
from urllib.parse import urlencode,urlparse
import pandas as pd
REPOSITORY='MinaSeliman1/trading-backtests'
WORKFLOW='qqq-eod-replay.yml'

class CloudError(Exception):
 def __init__(self,status):self.status=status;super().__init__('GitHub read failed; details omitted')

def select_head(runs,artifacts,identity):
 candidates=[r for r in runs if r.get('active') and r.get('repository')==identity['repository'] and r.get('workflow_id')==identity['workflow_id'] and r.get('branch')==identity['branch'] and r.get('generation')==identity['generation']]
 if not candidates:return None
 run=max(candidates,key=lambda r:(r['run_number'],r['run_attempt']))
 if run['status']!='completed':raise ValueError('previous active generation is not finished')
 name=f"qqq-eod-state-{identity['generation']}-{run['id']}-{run['run_attempt']}"
 matches=[a for a in artifacts if a.get('name')==name and a.get('run_id')==run['id'] and a.get('run_attempt')==run['run_attempt']]
 if len(matches)!=1:raise ValueError('latest state missing; old checkpoint fallback refused')
 a=matches[0]
 if a.get('expired') or a.get('head_sha')!=run['head_sha'] or a.get('branch')!=identity['branch']:raise ValueError('latest checkpoint provenance mismatch')
 return dict(a,run=run)

def may_initialize(first_day,now,previously_active):
 t=pd.Timestamp(now)
 if t.tz is None:raise ValueError('timezone required')
 return not previously_active and str(t.tz_convert('America/New_York').date())<str(first_day)

class NoRedirect(HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):return None

class GitHubReadOnly:
 def __init__(self,token,repository=REPOSITORY):
  if repository!=REPOSITORY or not token:raise ValueError('approved GitHub repository/token required')
  self.repository=repository;self.headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28','User-Agent':'QQQEODReplay/1'};self.opener=build_opener(NoRedirect())
 def clear(self):self.headers.clear()
 def _request(self,path,params=None):
  base='/repos/'+self.repository
  allowed=bool(re.fullmatch(re.escape(base)+r'/actions/(?:workflows/[A-Za-z0-9_.-]+(?:/runs)?|runs/\d+(?:/(?:jobs|artifacts))?|artifacts(?:/\d+/zip)?)',path)) or path==base+'/contents/bots/qqq-eod-replay/activation.json'
  if not allowed:raise ValueError('GitHub route is read-only and scoped')
  url='https://api.github.com'+path+('?' +urlencode(params) if params else '')
  return Request(url,headers=self.headers,method='GET')
 def get_json(self,path,params=None,missing_ok=False):
  try:
   with self.opener.open(self._request(path,params),timeout=30) as response:return json.load(response)
  except HTTPError as e:
   if missing_ok and e.code==404:return None
   raise CloudError(e.code) from None
 def activation(self,sha):
  if not re.fullmatch('[0-9a-f]{40}',sha):raise ValueError('head SHA required')
  obj=self.get_json('/repos/'+self.repository+'/contents/bots/qqq-eod-replay/activation.json',{'ref':sha},missing_ok=True)
  return json.loads(base64.b64decode(obj['content'])) if obj else {'enabled':False}
 def prior_state(self,current_run_id,generation):
  root='/repos/'+self.repository+'/actions';workflow=self.get_json(root+'/workflows/'+WORKFLOW);wid=workflow['id'];runs=[];arts=[]
  for page in range(1,31):
   batch=self.get_json(root+'/workflows/'+str(wid)+'/runs',{'per_page':100,'page':page})['workflow_runs']
   for r in batch:
    if str(r['id'])==str(current_run_id) or r['head_branch']!='main' or r['event'] not in ('schedule','workflow_dispatch','push'):continue
    config=self.activation(r['head_sha'])
    if not config.get('enabled') or config.get('generation')!=generation:continue
    jobs=self.get_json(root+'/runs/'+str(r['id'])+'/jobs',{'filter':'latest','per_page':100})['jobs']
    active=any(st['name']=='Active generation checkpoint' and st['conclusion']=='success' for job in jobs for st in job.get('steps',[]))
    if not active:continue
    run=dict(id=r['id'],run_number=r['run_number'],run_attempt=r['run_attempt'],head_sha=r['head_sha'],repository=self.repository,workflow_id=wid,branch='main',generation=generation,active=True,status=r['status'],conclusion=r['conclusion']);runs.append(run)
    rows=self.get_json(root+'/runs/'+str(r['id'])+'/artifacts',{'per_page':100})['artifacts']
    for a in rows:
     arts.append(dict(id=a['id'],name=a['name'],run_id=r['id'],run_attempt=r['run_attempt'],head_sha=a.get('workflow_run',{}).get('head_sha'),branch=a.get('workflow_run',{}).get('head_branch'),expired=a['expired'],digest=a.get('digest')))
    identity=dict(repository=self.repository,workflow_id=wid,generation=generation,branch='main')
    return select_head(runs,arts,identity),identity
   if len(batch)<100:break
  return None,dict(repository=self.repository,workflow_id=wid,generation=generation,branch='main')
 def artifact_bytes(self,artifact_id):
  path='/repos/'+self.repository+'/actions/artifacts/'+str(int(artifact_id))+'/zip'
  try:
   with self.opener.open(self._request(path),timeout=30) as response:raw=response.read(8*1024*1024+1)
  except HTTPError as e:
   if e.code not in (301,302,303,307):raise CloudError(e.code) from None
   location=e.headers.get('Location','');u=urlparse(location);host=u.hostname or ''
   allowed=u.scheme=='https' and not u.username and u.port in (None,443) and (host.endswith('.blob.core.windows.net') or host.endswith('.githubusercontent.com') or host.endswith('.s3.amazonaws.com'))
   if not allowed:raise ValueError('unapproved artifact download redirect')
   # The GitHub Authorization header is deliberately absent on the signed blob request.
   with urlopen(Request(location,headers={'User-Agent':'QQQEODReplay/1'}),timeout=30) as response:raw=response.read(8*1024*1024+1)
  if len(raw)>8*1024*1024:raise ValueError('artifact exceeds project size limit')
  with zipfile.ZipFile(io.BytesIO(raw)) as archive:
   members=archive.infolist()
   if len(members)!=1 or members[0].filename!='state.enc' or members[0].file_size>4*1024*1024:raise ValueError('unexpected outer artifact layout')
   return archive.read('state.enc')
