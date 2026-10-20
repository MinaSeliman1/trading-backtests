"""Calendrier, historique local et verrou d'instance ; aucun secret sur disque."""
from pathlib import Path
from contextlib import AbstractContextManager
import os
import json
import pandas as pd
import exchange_calendars as xcals
from .strategy import Session
from noise_area.data import read_market


class ProcessLock(AbstractContextManager):
    def __init__(self,path):self.path=Path(path);self.stream=None
    def __enter__(self):
        self.path.parent.mkdir(parents=True,exist_ok=True);self.stream=self.path.open('a+b')
        if self.path.stat().st_size==0:self.stream.write(b'0');self.stream.flush()
        self.stream.seek(0)
        try:
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(self.stream.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(self.stream.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError:
            self.stream.close();raise RuntimeError('another bot instance owns this state directory') from None
        return self
    def __exit__(self,*args):
        if self.stream:
            self.stream.seek(0)
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(self.stream.fileno(),msvcrt.LK_UNLCK,1)
            else:
                import fcntl
                fcntl.flock(self.stream.fileno(),fcntl.LOCK_UN)
            self.stream.close()


def calendar(day):
    d=pd.Timestamp(day)
    return xcals.get_calendar('XNYS',start=d-pd.Timedelta(days=120),end=d+pd.Timedelta(days=10))


def session_for(day):
    cal=calendar(day);date=pd.Timestamp(day)
    if not cal.is_session(date):return None
    row=cal.schedule.loc[date]
    return Session(pd.Timestamp(row['open']).tz_convert('America/New_York'),pd.Timestamp(row['close']).tz_convert('America/New_York'))


def load_history(data,session,folder,feed):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    end=session.open.normalize();start=end-pd.Timedelta(days=100)
    bars=data.bars(start,end,feed)
    if bars.empty:raise ValueError('empty history')
    path=folder/f'history-{feed}-{end.date()}.csv';bars.to_csv(path,index_label='timestamp')
    market=read_market([path],'QQQ')
    previous=calendar(end.date()).previous_session(pd.Timestamp(end.date()))
    if pd.Timestamp(market.dates[-1]).date()!=pd.Timestamp(previous).date():raise ValueError('previous NYSE session missing from history')
    if len(market.dates)<15 or not market.valid[-15:].all():raise ValueError('15 consecutive valid previous closes required; history contains incomplete sessions')
    return market


def write_status(folder,**fields):
    path=Path(folder)/'status.json';temp=path.with_suffix('.tmp')
    temp.write_text(json.dumps(fields,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8');temp.replace(path)
