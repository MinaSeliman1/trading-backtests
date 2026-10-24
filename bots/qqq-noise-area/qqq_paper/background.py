"""Supervision locale sans console. Mode fixe : shadow SIP, aucun ordre."""
import argparse
from contextlib import redirect_stdout,redirect_stderr
from datetime import datetime,timezone
import io
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import sys
import time
from . import __main__ as app
from .runtime import ProcessLock,write_status
from .power import PowerGuard
from .windows_vault import WindowsVault


class LogStream(io.TextIOBase):
    def __init__(self,logger,level):self.logger=logger;self.level=level;self.pending=''
    def write(self,value):
        self.pending+=value
        while '\n' in self.pending:
            line,self.pending=self.pending.split('\n',1)
            if line:self.logger.log(self.level,line)
        return len(value)
    def flush(self):
        if self.pending:self.logger.log(self.level,self.pending);self.pending=''


def wait_for_stop(path,seconds):
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
        if path.exists():return True
        time.sleep(min(1.,max(0.,deadline-time.monotonic())))
    return path.exists()


def serve(runtime):
    runtime=Path(runtime).resolve();folder=runtime/'windows';folder.mkdir(parents=True,exist_ok=True)
    stop=runtime/'STOP_SHADOW.flag'
    logger=logging.getLogger('qqq_shadow_background');logger.setLevel(logging.INFO);logger.propagate=False
    handler=RotatingFileHandler(folder/'background.log',maxBytes=2_000_000,backupCount=5,encoding='utf-8')
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'));logger.addHandler(handler)
    stdout=LogStream(logger,logging.INFO);stderr=LogStream(logger,logging.ERROR)
    try:
        with ProcessLock(runtime/'background.lock'),redirect_stdout(stdout),redirect_stderr(stderr),PowerGuard(runtime):
            attempt=0
            while not stop.exists():
                attempt+=1
                write_status(folder,state='supervising_shadow',mode='shadow',feed='sip',pid=os.getpid(),attempt=attempt,
                    utc=datetime.now(timezone.utc).isoformat(),executable=Path(sys.executable).name,power_guard=True)
                try:
                    code=app.main(['--mode','shadow','--feed','sip','--runtime',str(runtime),'--stop-file',str(stop)],credentials=WindowsVault().load())
                    logger.info('Shadow engine returned code %s',code)
                except Exception as error:
                    logger.error('Shadow startup interrupted: %s; no credential values logged',type(error).__name__)
                if stop.exists():break
                write_status(folder,state='retrying_shadow_startup',mode='shadow',feed='sip',pid=os.getpid(),attempt=attempt,utc=datetime.now(timezone.utc).isoformat(),power_guard=True)
                if wait_for_stop(stop,60):break
            write_status(folder,state='stopped',mode='shadow',feed='sip',pid=os.getpid(),utc=datetime.now(timezone.utc).isoformat(),power_guard=True)
            return 0
    finally:
        stdout.flush();stderr.flush();logger.removeHandler(handler);handler.close()


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--runtime',type=Path,default=Path('runtime'));a=p.parse_args(argv)
    try:return serve(a.runtime)
    except RuntimeError:return 1


if __name__=='__main__':sys.exit(main())
