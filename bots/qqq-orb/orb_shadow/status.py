"""Best-effort ORB telemetry: a Windows reader must not stop position management."""
from pathlib import Path
import errno,json,logging,time,uuid

LOG=logging.getLogger('orb_shadow')


def write_json(path,fields):
    path=Path(path)
    payload=json.dumps(fields,ensure_ascii=False,indent=2,allow_nan=False)
    temp=path.with_name('.'+path.name+'.'+uuid.uuid4().hex+'.tmp')
    try:
        for attempt in range(4):
            try:
                temp.write_text(payload,encoding='utf-8')
                temp.replace(path)
                return True
            except OSError as error:
                retry=(error.errno in (errno.EACCES,errno.EPERM,errno.EBUSY) or getattr(error,'winerror',None) in (5,32,33))
                if retry and attempt<3:
                    time.sleep((.05,.15,.35)[attempt])
                    continue
                # No exception text, paths, local values or credentials in the log.
                LOG.warning('Telemetry write deferred: type=%s errno=%s winerror=%s',type(error).__name__,error.errno,getattr(error,'winerror',None))
                return False
    finally:
        try:temp.unlink(missing_ok=True)
        except OSError:pass


def write_status(folder,**fields):
    return write_json(Path(folder)/'status.json',fields)
