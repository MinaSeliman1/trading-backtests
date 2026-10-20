"""Indicateurs sur préfixe terminé, sans masquer le jour courant incomplet."""
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
import hashlib
import math
import sys
import numpy as np
import pandas as pd

STUDY=Path(__file__).resolve().parents[3]/'studies/intraday-momentum-noise-area'
sys.path.insert(0,str(STUDY))
from noise_area.features import desired_position


@dataclass(frozen=True)
class Parameters:
    symbol:str='QQQ'
    lookback:int=14
    volatility_window:int=14
    frequency:int=30
    target_vol:float=.02
    leverage_cap:float=4.
    initial_capital:float=100000.
    commission:float=.0035
    minimum_commission:float=.35
    slippage:float=.01
    borrow_rate:float=.01


@dataclass(frozen=True)
class Session:
    open:pd.Timestamp
    close:pd.Timestamp

    def __post_init__(self):
        if self.open.tz is None or self.close.tz is None or self.close<=self.open:raise ValueError('timezone-aware session required')

    @property
    def flatten(self):return self.close-pd.Timedelta(minutes=1)


def verify_frozen_strategy():
    expected='ecab630d5f850c4def089739c9a13b7acd88de1361527483ff39f0f6a6765664'
    if hashlib.sha256((STUDY/'noise_area/features.py').read_bytes()).hexdigest()!=expected:
        raise ValueError('historical strategy fingerprint changed')


def decision_times(session):
    return list(pd.date_range(session.open+pd.Timedelta(minutes=30),session.flatten,freq='30min'))


def completed_prefix(frame,session,at):
    at=pd.Timestamp(at)
    if at.tz is None or at<=session.open or at>session.close:raise ValueError('invalid completed prefix time')
    if not isinstance(frame.index,pd.DatetimeIndex) or frame.index.tz is None:raise ValueError('timestamps require timezone')
    f=frame.loc[(frame.index>=session.open)&(frame.index<at)].copy()
    f.index=f.index.tz_convert(session.open.tz)
    f=f.reset_index().drop_duplicates().set_index(f.index.name or 'index').sort_index()
    if f.index.has_duplicates:raise ValueError('conflicting minute duplicates')
    expected=pd.date_range(session.open,at,inclusive='left',freq='min')
    if not f.index.equals(expected):raise ValueError('missing or off-grid completed minute')
    prices=f[['open','high','low','close']]
    bad=(~np.isfinite(prices).all(axis=1))|(prices.min(axis=1)<=0)|(~np.isfinite(f.volume))|(f.volume<0)
    bad|=(f.high<prices.max(axis=1))|(f.low>prices.min(axis=1))
    if bad.any() or f.volume.sum()<=0:raise ValueError('invalid OHLCV')
    return f


def day_size(capital,opening,volatility):
    if not all(math.isfinite(v) for v in [capital,opening,volatility]) or capital<=0 or opening<=0 or volatility<0:
        raise ValueError('invalid sizing inputs')
    return math.floor(capital*min(4.,.02/volatility if volatility>0 else 4.)/opening)


def signal(history,today,session,at,position,dividend=0.):
    at=pd.Timestamp(at)
    if at not in decision_times(session):raise ValueError('not a scheduled decision')
    if not math.isfinite(dividend) or dividend<0:raise ValueError('invalid dividend')
    if len(history.dates)<15 or not history.valid[-15:].all():raise ValueError('15 consecutive valid previous closes required')
    if pd.Timestamp(history.dates[-1]).date()>=session.open.tz_convert('America/New_York').date():raise ValueError('history includes current or future session')
    prefix=completed_prefix(today,session,at);j=len(prefix)-1;a=history.arrays
    eligible=np.flatnonzero(history.valid & np.isfinite(a['close'][:,j]))[-14:]
    if len(eligible)!=14:raise ValueError('14 prior clock observations required')
    sigma=float(np.mean(np.abs(a['close'][eligible,j]/a['open'][eligible,0]-1)))
    last=np.arange(len(history.dates)-15,len(history.dates))
    closes=a['close'][last,history.lengths[last]-1]
    volatility=float(np.std(closes[1:]/closes[:-1]-1,ddof=1))
    opening=float(prefix.open.iloc[0]);previous=float(closes[-1])-dividend
    vwap=float((((prefix.high+prefix.low+prefix.close)/3)*prefix.volume).sum()/prefix.volume.sum())
    upper=max(opening,previous)*(1+sigma);lower=min(opening,previous)*(1-sigma);price=float(prefix.close.iloc[-1])
    target=desired_position(position,price,upper,lower,vwap,'combined')
    return SimpleNamespace(target=int(target),price=price,upper=upper,lower=lower,vwap=vwap,sigma=sigma,
                           volatility=volatility,opening=opening,previous_close_adjusted=previous,decision_time=str(at))
