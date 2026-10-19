from dataclasses import dataclass, replace, asdict
from math import floor, ceil
import pandas as pd
import numpy as np

MINUTE = pd.Timedelta(minutes=1)


@dataclass(frozen=True)
class Instrument:
    symbol: str
    tick: float
    point_value: float
    commission: float
    min_commission: float
    margin: float
    max_leverage: float
    futures: bool = False


INSTRUMENTS = {
    "SPY": Instrument("SPY", .01, 1., .005, 1., 1., 1.),
    "QQQ": Instrument("QQQ", .01, 1., .005, 1., 1., 1.),
    "ES": Instrument("ES", .25, 50., 2.50, 0., 25000., 10., True),
    "NQ": Instrument("NQ", .25, 20., 2.50, 0., 40000., 10., True),
}


@dataclass(frozen=True)
class Config:
    initial_capital: float = 100000.
    risk_fraction: float = .005
    stop_variant: str = "A"
    slippage_ticks: int = 1
    spread_ticks: float | None = None  # None => ETF 1 tick, futures 0 (slippage includes spread)
    retest_minutes: int = 15
    confirmation_bars: int = 2
    extra_fee_per_unit: float = .0001  # reserve per side, ETF only
    annual_borrow_rate: float = .01
    max_volume_fraction: float = .01  # known volume of confirmation bar, no future volume


@dataclass(frozen=True)
class Setup:
    direction: int
    formation_time: pd.Timestamp
    retest_time: pd.Timestamp
    signal_time: pd.Timestamp
    entry_time: pd.Timestamp
    fvg_low: float
    fvg_high: float
    stop_a: float
    stop_b: float
    opening_high: float
    opening_low: float
    confirmation_volume: float


def round_tick(price, tick, direction):
    scaled = price/tick
    return (ceil(scaled-1e-8) if direction > 0 else floor(scaled+1e-8))*tick


def friction(ins, config):
    spread=config.spread_ticks
    if spread is None: spread=0. if ins.futures else 1.
    return ins.tick*(config.slippage_ticks+spread/2)


def market_fill(reference, side, ins, config):
    return round_tick(reference+side*friction(ins,config),ins.tick,side)


def fee(quantity, price, ins, config):
    base=max(ins.min_commission,quantity*ins.commission)
    if not ins.futures:
        base=min(base,quantity*price*.01)+quantity*config.extra_fee_per_unit
    return base


def detect_setups(bars, config, tick=.01):
    """Évolution causale au close ; ne lit ni l'open ni le volume de la minute suivante."""
    if len(bars)<8: return []
    if not bars.index.is_monotonic_increasing or bars.index.has_duplicates or not (bars.index.to_series().diff().iloc[1:]==MINUTE).all():
        raise ValueError("bars must be consecutive one-minute timestamps")
    if bars.index[0].strftime("%H:%M")!="09:30":
        raise ValueError("session must start at 09:30 New York")
    h=float(bars.high.iloc[:5].max()); l=float(bars.low.iloc[:5].min())
    candidates=[]; completed=[]
    arr=bars[["open","high","low","close","volume"]].to_numpy(dtype=float)
    for j in range(5,len(bars)):
        now=bars.index[j]+MINUTE
        if now.hour>=11: break
        o,hi,lo,c,vol=arr[j]; prev=arr[j-1]
        keep=[]
        for a in candidates:
            if a["retest"] is None:
                if now>a["formed"]+pd.Timedelta(minutes=config.retest_minutes): continue
                if lo<=a["upper"] and hi>=a["lower"]:
                    a.update(retest=j,low=lo,high=hi)
                else:
                    keep.append(a); continue
            if j-a["retest"]>config.confirmation_bars: continue
            a["low"]=min(a["low"],lo); a["high"]=max(a["high"],hi)
            bull=c>o and prev[3]<prev[0] and o<=prev[3] and c>=prev[0]
            bear=c<o and prev[3]>prev[0] and o>=prev[3] and c<=prev[0]
            if (a["direction"]==1 and bull) or (a["direction"]==-1 and bear):
                d=a["direction"]
                stop_a=round_tick(a["low"]-tick,tick,-1) if d==1 else round_tick(a["high"]+tick,tick,1)
                stop_b=round_tick(a["lower"]-tick,tick,-1) if d==1 else round_tick(a["upper"]+tick,tick,1)
                completed.append(Setup(d,a["formed"],bars.index[a["retest"]]+MINUTE,now,now,
                                       a["lower"],a["upper"],stop_a,stop_b,h,l,vol))
            else: keep.append(a)
        candidates=keep
        if j<7: continue  # first full triple 09:35,36,37
        first=arr[j-2]; middle=arr[j-1]
        direction=0
        if lo>first[1] and middle[0]<=h and middle[3]>h:
            direction=1; lower=first[1]; upper=lo
        elif hi<first[2] and middle[0]>=l and middle[3]<l:
            direction=-1; lower=hi; upper=first[2]
        if direction:
            candidates.append(dict(direction=direction,formed=now,lower=lower,upper=upper,retest=None))
    return sorted(completed,key=lambda s:(s.signal_time,s.formation_time,-s.direction))


def position_size(capital, entry, stop, ins, config, volume=float("inf"), margin=None, direction=1):
    distance=abs(entry-stop)*ins.point_value
    if distance<=0 or capital<=0: return 0
    budget=capital*config.risk_fraction
    # Entry friction is already in entry price; anticipated stop friction and all fees enter budget.
    rounded_friction=ceil(friction(ins,config)/ins.tick-1e-8)*ins.tick
    borrow_per_unit=entry*config.annual_borrow_rate/360 if direction<0 and not ins.futures else 0.
    per=distance+rounded_friction*ins.point_value+borrow_per_unit
    exposure=capital*ins.max_leverage/(entry*ins.point_value)
    collateral=capital/(margin if margin is not None else ins.margin) if ins.futures else capital/entry
    q=max(0,floor(min(budget/per,exposure,collateral,volume*config.max_volume_fraction)))
    while q and (q*per+fee(q,entry,ins,config)+fee(q,stop,ins,config)>budget or
                 (not ins.futures and q*entry+fee(q,entry,ins,config)>capital) or
                 (ins.futures and q*(margin if margin is not None else ins.margin)+fee(q,entry,ins,config)>capital)):
        q-=1
    return q


def exit_fill(bar, direction, stop, target, ins, config):
    """(prix exécuté, motif, référence sans friction), ou None."""
    o=float(bar["open"]); hi=float(bar["high"]); lo=float(bar["low"])
    # Tick multiplication may differ from a parsed equal price by one binary ULP.
    # This tolerance is 1e-8 of a tick, far below an observable subcent price.
    tolerance=ins.tick*1e-8
    if direction*(o-stop)<=tolerance:
        return market_fill(o,-direction,ins,config),"stop_gap",o
    if direction*(o-target)>=-tolerance:
        return market_fill(target,-direction,ins,config),"target",target
    stop_hit=lo<=stop+tolerance if direction==1 else hi>=stop-tolerance
    target_hit=hi>=target-tolerance if direction==1 else lo<=target+tolerance
    if stop_hit: return market_fill(stop,-direction,ins,config),"stop",stop
    if target_hit: return market_fill(target,-direction,ins,config),"target",target
    return None


def run(sessions, ins, config):
    if config.stop_variant not in ("A","B"): raise ValueError("stop_variant must be A or B")
    session_dates=[s.index[0].date() for s in sessions]
    if len(session_dates)!=len(set(session_dates)) or session_dates!=sorted(session_dates):
        raise ValueError("sessions must have unique chronological dates")
    equity=config.initial_capital; trades=[]; marks=[]; rejects=[]
    for bars in sessions:
        day=str(bars.index[0].date()); chosen=None
        for s in detect_setups(bars,config,ins.tick):
            if s.entry_time not in bars.index: continue
            stop=s.stop_a if config.stop_variant=="A" else s.stop_b
            # Market-order quantity is determined before observing any next-bar price.
            known_close=float(bars.loc[s.signal_time-MINUTE,"close"])
            estimated_entry=market_fill(known_close,s.direction,ins,config)
            reason=None
            if s.direction*(estimated_entry-stop)<=0: reason="invalid_stop_at_order"
            if ins.futures and bars.attrs.get("margin") is not None:
                margin=bars.attrs["margin"]
            else: margin=ins.margin
            q=0 if reason else position_size(equity,estimated_entry,stop,ins,config,s.confirmation_volume,margin,s.direction)
            if not reason and q<1: reason="insufficient_capital_margin_or_volume"
            if not reason and s.direction<0 and bars.attrs.get("shortable",True) is False:
                reason="short_unavailable"
            # The next opening price is consumed only for the execution/broker acceptance event.
            reference=float(bars.loc[s.entry_time,"open"])
            entry=market_fill(reference,s.direction,ins,config)
            if not reason and s.direction*(entry-stop)<=0: reason="invalid_stop"
            if not reason and (q*entry*ins.point_value>equity*ins.max_leverage+1e-7 or
                    (not ins.futures and q*entry+fee(q,entry,ins,config)>equity+1e-7) or
                    (ins.futures and q*margin+fee(q,entry,ins,config)>equity+1e-7)):
                reason="broker_capital_or_exposure_rejection_after_gap"
            if reason:
                rejects.append(dict(date=day,signal_time=s.signal_time,reason=reason)); continue
            chosen=(s,entry,stop,q,reference,estimated_entry); break
        if chosen is None:
            marks.append(dict(timestamp=bars.index[-1]+MINUTE,equity=equity,date=day)); continue
        s,entry,stop,q,ref,estimated_entry=chosen; initial_risk=abs(entry-stop)*q*ins.point_value
        target=round_tick(entry+s.direction*3*abs(entry-stop),ins.tick,s.direction)
        fees_in=fee(q,entry,ins,config); base_equity=equity
        marks.append(dict(timestamp=s.entry_time,equity=equity-fees_in,date=day))
        after=bars.loc[s.entry_time:]
        for timestamp,bar in after.iterrows():
            # A scheduled exit on last minute's open precedes its unknown high/low.
            result=(market_fill(float(bar.open),-s.direction,ins,config),"session_end",float(bar.open)) if timestamp==bars.index[-1] else exit_fill(bar,s.direction,stop,target,ins,config)
            if result:
                out,reason,exit_ref=result
                fees_out=fee(q,out,ins,config)
                borrow=(q*entry*config.annual_borrow_rate/360) if s.direction<0 and not ins.futures else 0.
                gross=(out-entry)*s.direction*q*ins.point_value
                net=gross-fees_in-fees_out-borrow; equity+=net
                slip_entry=(entry-ref)*s.direction*q*ins.point_value
                slip_exit=(exit_ref-out)*s.direction*q*ins.point_value
                row=asdict(s)
                estimated_borrow=q*estimated_entry*config.annual_borrow_rate/360 if s.direction<0 and not ins.futures else 0.
                estimated_loss=(abs(estimated_entry-stop)+abs(stop-market_fill(stop,-s.direction,ins,config)))*q*ins.point_value+fee(q,estimated_entry,ins,config)+fee(q,stop,ins,config)+estimated_borrow
                row.update(date=day,instrument=ins.symbol,contract=bars.attrs.get("contract",ins.symbol),
                           direction="LONG" if s.direction==1 else "SHORT",quantity=q,entry_price=entry,
                           entry_reference=ref,stop=stop,target=target,exit_time=timestamp,exit_price=out,
                           estimated_entry_at_order=estimated_entry,estimated_loss_at_order_usd=estimated_loss,
                           exit_reference=exit_ref,exit_reason=reason,entry_fee=fees_in,exit_fee=fees_out,
                           borrow_fee=borrow,fees=fees_in+fees_out+borrow,slippage_usd=slip_entry+slip_exit,
                           nominal_slippage_usd=2*config.slippage_ticks*ins.tick*q*ins.point_value,
                           gross_pnl=gross,net_pnl=net,result_r=net/initial_risk,initial_risk_usd=initial_risk,
                           risk_fraction=initial_risk/base_equity,planned_loss_usd=initial_risk+abs(stop-market_fill(stop,-s.direction,ins,config))*q*ins.point_value+fees_in+fee(q,stop,ins,config)+borrow,
                           exposure_usd=q*entry*ins.point_value,exposure_fraction=q*entry*ins.point_value/base_equity,
                           margin_usd=q*margin if ins.futures else q*entry,
                           duration_minutes=(timestamp-s.entry_time).total_seconds()/60,
                           duration_upper_minutes=(timestamp+MINUTE-s.entry_time).total_seconds()/60,
                           opening_range_pct=(s.opening_high-s.opening_low)/((s.opening_high+s.opening_low)/2))
                trades.append(row)
                marks.append(dict(timestamp=timestamp+MINUTE,equity=equity,date=day)); break
            mark=base_equity-fees_in+(float(bar.close)-entry)*s.direction*q*ins.point_value
            marks.append(dict(timestamp=timestamp+MINUTE,equity=mark,date=day))
        marks.append(dict(timestamp=bars.index[-1]+MINUTE,equity=equity,date=day))
    return pd.DataFrame(trades),pd.DataFrame(marks),pd.DataFrame(rejects,columns=["date","signal_time","reason"])
