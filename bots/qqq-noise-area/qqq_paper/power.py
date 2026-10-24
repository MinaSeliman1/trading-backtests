"""Prevent automatic sleep while the shadow supervisor runs on AC; no plan edits."""
from datetime import datetime, timezone
from functools import lru_cache
import ctypes
import logging
import os
from pathlib import Path
import threading

import pandas as pd

from .runtime import session_for


@lru_cache(maxsize=16)
def _session(day):
    return session_for(day)


def protection_window(now):
    now=pd.Timestamp(now)
    if now.tz is None:
        raise ValueError('timezone-aware power observation required')
    session=_session(str(now.tz_convert('America/New_York').date()))
    return bool(session and session.open-pd.Timedelta(minutes=15)<=now<session.close+pd.Timedelta(minutes=20))


class WindowsPower:
    def __init__(self):
        from ctypes import wintypes

        class SystemPowerStatus(ctypes.Structure):
            _fields_=[('ac',ctypes.c_ubyte),('battery_flags',ctypes.c_ubyte),
                      ('battery_percent',ctypes.c_ubyte),('saver',ctypes.c_ubyte),
                      ('battery_seconds',wintypes.DWORD),('full_seconds',wintypes.DWORD)]

        self.status_type=SystemPowerStatus
        self.kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        self.kernel.GetSystemPowerStatus.argtypes=[ctypes.POINTER(SystemPowerStatus)]
        self.kernel.GetSystemPowerStatus.restype=wintypes.BOOL
        self.kernel.SetThreadExecutionState.argtypes=[wintypes.DWORD]
        self.kernel.SetThreadExecutionState.restype=wintypes.DWORD

    def on_ac(self):
        status=self.status_type()
        if not self.kernel.GetSystemPowerStatus(ctypes.byref(status)):
            raise ctypes.WinError(ctypes.get_last_error())
        return True if status.ac==1 else False if status.ac==0 else None

    def system_required(self,enabled):
        # No DISPLAY_REQUIRED or AWAYMODE: the display and explicit sleep remain free.
        flags=0x80000000 | (0x00000001 if enabled else 0)
        if not self.kernel.SetThreadExecutionState(flags):
            raise ctypes.WinError(ctypes.get_last_error())


class PowerGuard:
    def __init__(self,runtime,backend=None,clock=None,interval=15):
        self.folder=Path(runtime)/'windows'
        self.backend=backend
        self.clock=clock or (lambda:datetime.now(timezone.utc))
        self.interval=interval
        self.active=False
        self.previous=None
        self.last_gap=None
        self.last_state=None
        self.stop=threading.Event()
        self.ready=threading.Event()
        self.thread=None
        self.logger=logging.getLogger('qqq_shadow_background')

    def _release(self):
        if self.active:
            self.backend.system_required(False)
            self.active=False

    def _status(self,now,state,**fields):
        self.folder.mkdir(parents=True,exist_ok=True)
        value=dict(state=state,utc=now.isoformat(),system_required=self.active,
                   automatic_sleep_only=True,ac_only=True,display_required=False,**fields)
        if self.last_gap:
            value.update(self.last_gap)
        self._write(value)
        if state!=self.last_state:
            self.logger.info('Power protection: %s',state)
            self.last_state=state

    def _write(self,value):
        # Separate file: never overwrite the supervisor or engine status.
        import json
        path=self.folder/'power_status.json'
        temp=path.with_suffix('.tmp')
        temp.write_text(json.dumps(value,indent=2,allow_nan=False),encoding='utf-8')
        temp.replace(path)

    def tick(self,now=None):
        now=pd.Timestamp(self.clock() if now is None else now).tz_convert('UTC')
        try:
            if self.folder.parent.joinpath('STOP_SHADOW.flag').exists():
                self._release()
                self._status(now,'stop_requested')
                return
            window=protection_window(now)
            if self.previous is not None:
                gap=(now-self.previous).total_seconds()
                if gap>120 and (window or protection_window(self.previous)):
                    self.last_gap=dict(last_gap_seconds=gap,last_gap_utc=now.isoformat())
                    self.logger.warning('Power worker observation gap: %.1f seconds',gap)
            self.previous=now
            if self.backend is None:
                if os.name!='nt':
                    self._status(now,'unsupported',in_session_window=window,on_ac=None)
                    return
                self.backend=WindowsPower()
            ac=self.backend.on_ac()
            # Keep the next session reachable too: releasing overnight could put
            # the process to sleep before it can acquire tomorrow's request.
            wanted=ac is True
            if wanted and not self.active:
                self.backend.system_required(True)
                self.active=True
            elif not wanted:
                self._release()
            state='protected' if wanted else 'on_battery' if ac is False else 'power_unknown'
            self._status(now,state,in_session_window=window,on_ac=ac)
        except Exception as error:
            try:
                self._release()
            except Exception:
                pass
            self._status(now,'error',error_type=type(error).__name__)

    def _run(self):
        try:
            while not self.stop.is_set():
                try:
                    self.tick()
                except Exception as error:
                    self.logger.error('Power status write failed: %s',type(error).__name__)
                finally:
                    self.ready.set()
                self.stop.wait(self.interval)
        finally:
            try:
                self._release()
                self._status(pd.Timestamp(self.clock()).tz_convert('UTC'),'stopped')
            except Exception as error:
                self.logger.error('Power cleanup failed: %s',type(error).__name__)

    def __enter__(self):
        self.thread=threading.Thread(target=self._run,name='qqq-ac-power',daemon=True)
        self.thread.start()
        if not self.ready.wait(5):
            self.__exit__()
            raise RuntimeError('power protection worker did not start')
        return self

    def __exit__(self,*args):
        self.stop.set()
        if self.thread:
            self.thread.join(timeout=5)
