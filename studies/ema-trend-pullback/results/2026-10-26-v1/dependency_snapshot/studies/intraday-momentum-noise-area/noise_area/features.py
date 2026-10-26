"""Indicateurs calculés avec le passé disponible à chaque minute terminée."""
import numpy as np
import pandas as pd


def compute_features(market, dividends, lookback=14):
    a=market.arrays
    opening=a['open'][:,0]
    closes=a['close'][np.arange(len(market.dates)),market.lengths-1].copy()
    closes[~market.valid]=np.nan
    previous=pd.Series(closes).shift(1).to_numpy()
    cash=np.array([float(dividends.get(str(day.date()),0.)) for day in market.dates])
    daily_returns=closes/previous-1
    volatility=pd.Series(daily_returns).rolling(14,min_periods=14).std(ddof=1).shift(1).to_numpy()
    moves=pd.DataFrame(np.abs(a['close']/opening[:,None]-1),index=market.dates)
    moves.loc[~market.valid,:]=np.nan
    # Missing afternoon clocks on an early close do not become zero observations.
    sigma=moves.apply(lambda s:s.dropna().shift(1).rolling(lookback,min_periods=lookback).mean().reindex(moves.index)).to_numpy()
    typical=(a['high']+a['low']+a['close'])/3
    volume=np.nancumsum(a['volume'],axis=1)
    with np.errstate(divide='ignore',invalid='ignore'):
        vwap=np.nancumsum(typical*a['volume'],axis=1)/volume
    adjusted=previous-cash
    return dict(sigma=sigma,vwap=vwap,upper=np.maximum(opening,adjusted)[:,None]*(1+sigma),
                lower=np.minimum(opening,adjusted)[:,None]*(1-sigma),volatility=volatility,
                previous_close=previous,previous_close_adjusted=adjusted,daily_returns=daily_returns,
                dividends=cash,closes=closes)


def desired_position(position, price, upper, lower, vwap, stop='combined'):
    if not np.isfinite([price,upper,lower,vwap]).all(): return 0
    entry=1 if price>upper and price>vwap else -1 if price<lower and price<vwap else 0
    if position==0: return entry
    if stop not in ('combined','band','vwap'): raise ValueError('unknown stop')
    long_stop=upper if stop=='band' else vwap if stop=='vwap' else max(upper,vwap)
    short_stop=lower if stop=='band' else vwap if stop=='vwap' else min(lower,vwap)
    exit_now=price<long_stop if position==1 else price>short_stop
    return entry if exit_now else position
