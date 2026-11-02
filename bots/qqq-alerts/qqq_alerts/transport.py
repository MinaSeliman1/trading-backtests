"""Fixed-host ntfy transport, generic templates; no raw error/URL logging."""
import json,re
from urllib.request import Request,build_opener,HTTPRedirectHandler
from urllib.error import HTTPError
CODES={
 'process_stopped':'processus arrete','engine_stale':'statut moteur trop ancien','operator_stop':'STOP demande',
 'unexpected_configuration':'configuration de simulation inattendue','ledger_paused':'journal en pause','pending_orders':'ordre simule non resolu',
 'journal_unavailable':'journal ou statut illisible','position_unresolved':'position simulee non resolue','engine_error':'moteur en erreur',
 'decision_missing':'decision attendue absente','decision_late':'decision observee en retard','data_delayed':'donnees retardees ou incompletes',
 'orb_missed_entry':'observation ORB matinale manquee','orb_observation_gap':'lacune observation ORB',
 'cloud_failed':'replay GitHub en echec','cloud_unresolved':'replay GitHub non resolu','risk_stop':'STOP statistique preenregistre',
 'cloud_summary_unavailable':'resume cloud indisponible','watchdog_unavailable':'surveillance locale indisponible'}
class SendError(Exception):pass
class NoRedirect(HTTPRedirectHandler):
 def redirect_request(self,*a,**k):return None

def validate_topics(alert,health):
 if not all(isinstance(v,str) and re.fullmatch(r'qsim_[a-f0-9]{48}',v) for v in (alert,health)) or alert==health:raise ValueError('invalid notification configuration')
 return dict(alert=alert,health=health)

class Ntfy:
 def __init__(self,alert,health,open_request=None):
  self.topics=validate_topics(alert,health);self.open=open_request or build_opener(NoRedirect()).open
 def request(self,kind,body='',headers=None,sequence=None,method='POST'):
  if kind not in ('alert','health') or method not in ('POST','GET','DELETE'):raise ValueError('invalid notification operation')
  if sequence is not None and not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',sequence):raise ValueError('invalid sequence')
  url='https://ntfy.sh/'+self.topics[kind]+('/'+sequence if sequence else '')
  h={'Content-Type':'text/plain; charset=utf-8',**(headers or {})};raw=body.encode('utf-8') if method=='POST' else None
  if raw is not None and len(raw)>2048:raise ValueError('notification too large')
  try:
   with self.open(Request(url,data=raw,headers=h,method=method),timeout=10) as response:
    data=response.read(65537)
   if len(data)>65536:raise SendError('notification response oversized')
   return data
  except HTTPError as e:raise SendError('notification HTTP '+str(e.code)) from None
  except Exception:raise SendError('notification transport failed; details omitted') from None
 def notice(self,bot,codes,stamp,key):
  if bot not in ('noise','orb','cloud','watchdog'):raise ValueError('unknown notification source')
  if not set(codes)<=CODES.keys():raise ValueError('unknown diagnostic code')
  text=', '.join(CODES[c] for c in sorted(codes)) if codes else 'controle positif : plus aucune anomalie active (les lacunes historiques restent conservees)'
  name={'noise':'QQQ Noise Area','orb':'QQQ ORB','cloud':'QQQ cloud','watchdog':'QQQ surveillance'}[bot]
  self.request('alert',name+' : '+text+'. Simulation uniquement. '+stamp,{'Title':'QQQ SIMULATION','Priority':'4' if codes else '3','Tags':'warning' if codes else 'white_check_mark'},key)
 def guard(self,stamp):
  return self.request('alert','QQQ : signal de vie local absent (PC, reseau ou surveillance). Verifier les deux simulations ; aucun ordre courtier.',{'Title':'QQQ SIMULATION - surveillance absente','Priority':'4','At':stamp},'local-watchdog')
 def cancel_guard(self):return self.request('alert',sequence='local-watchdog',method='DELETE')
 def health(self,stamp,issues):
  if set(issues)!={'noise','orb'} or any(not set(v)<=CODES.keys() for v in issues.values()):raise ValueError('invalid health snapshot')
  data=dict(version=1,utc=stamp,issues={b:sorted(v) for b,v in issues.items()})
  return self.request('health',json.dumps(data,separators=(',',':')),{'Firebase':'no'},'technical-health')
 def life(self,stamp,labels,session_day):
  if set(labels)!={'noise','orb'} or any(v not in ('controle recent sain','attention','non verifie','hors seance') for v in labels.values()):raise ValueError('invalid life labels')
  text='Vie quotidienne QQQ : Noise Area '+labels['noise']+' ; ORB '+labels['orb']+'. '+('Seance XNYS.' if session_day else 'Jour sans seance XNYS.')+' Simulation uniquement. '+stamp
  return self.request('alert',text,{'Title':'QQQ SIMULATION - vie quotidienne','Priority':'3'},'daily-'+stamp[:10])
 def test(self):
  return self.request('alert','TEST de notification QQQ Noise Area + ORB. Aucun incident reel, aucune transaction. Simulation uniquement.',{'Title':'QQQ SIMULATION - TEST','Priority':'3'},'installation-test')

 def read_health(self):
  url='https://ntfy.sh/'+self.topics['health']+'/json?poll=1&since=15m'
  try:
   with self.open(Request(url,method='GET'),timeout=10) as response:raw=response.read(65537)
   if len(raw)>65536:raise SendError('health response oversized')
   return [json.loads(line) for line in raw.decode('utf-8').splitlines() if line.strip()]
  except Exception:raise SendError('health unavailable; details omitted') from None
