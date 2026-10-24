"""Oracle de cas contrôlés. Ni compilateur Pine, ni moteur de résultats FX."""
from datetime import datetime, timedelta
import math
from zoneinfo import ZoneInfo


def pip_size(quote):
    return .01 if quote == 'JPY' else .0001


def verify_ticks(pip, tick):
    return math.ceil(pip / tick - 1e-9)


def wilson(wins, n):
    if not n:
        return None
    z = 1.959963984540054
    p = wins / n
    divisor = 1 + z*z/n
    centre = (p + z*z/(2*n))/divisor
    half = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))/divisor
    return max(0, centre-half), min(1, centre+half)


def risk_qty(equity, distance, pointvalue, step):
    if not all(math.isfinite(x) and x > 0 for x in [equity,distance,pointvalue,step]):
        return 0
    return math.floor(.01*equity/(distance*pointvalue)/step)*step


def nowick(o,h,l,c,tolerance,tick):
    # Tiny numerical allowance, far below one tick; no economic tolerance added.
    if c > o and o-l <= tolerance*tick+tick*1e-6:
        return 1
    if c < o and h-o <= tolerance*tick+tick*1e-6:
        return -1
    return 0


def pending_live(bar, signal_bar, ttl):
    return 1 <= bar-signal_bar <= ttl


def in_session(iso, tz='America/New_York', start=120, end=480):
    dt=datetime.fromisoformat(iso).astimezone(ZoneInfo(tz))
    minute=dt.hour*60+dt.minute
    return start <= minute < end


def parse_news(text, tz='America/New_York'):
    result=[]
    for token in filter(None,(s.strip() for s in text.split(';'))):
        try:
            date, span=token.split('@')
            first,last=span.split('-')
            a=datetime.fromisoformat(f'{date}T{first[:2]}:{first[2:]}').replace(tzinfo=ZoneInfo(tz))
            b=datetime.fromisoformat(f'{date}T{last[:2]}:{last[2:]}').replace(tzinfo=ZoneInfo(tz))
        except (ValueError,TypeError) as exc:
            raise ValueError('Invalid news window') from exc
        if len(first)!=4 or len(last)!=4 or b<=a:
            raise ValueError('Invalid news window')
        result.append((a,b))
    return result


def news_overlap(start,end,text,tz='America/New_York'):
    a,b=datetime.fromisoformat(start),datetime.fromisoformat(end)
    return any(a<y and b>x for x,y in parse_news(text,tz))


def fill_allowed(previous_close,bar_open,bar_close,news='',tz='America/New_York'):
    prev,a,b=map(datetime.fromisoformat,[previous_close,bar_open,bar_close])
    return a==prev and in_session(bar_open,tz) and in_session((b-timedelta(microseconds=1)).isoformat(),tz) and not news_overlap(bar_open,bar_close,news,tz)


def confirmed_pivot(values,length,high):
    if len(values)<2*length+1:
        return None
    window=values[-(2*length+1):]
    mid=window[length]
    others=window[:length]+window[length+1:]
    # Fixtures use unique extrema; equality tie rules remain the native ta.pivot* rules.
    return mid if (all(mid>x for x in others) if high else all(mid<x for x in others)) else None


def structure(highs,lows):
    if min(len(highs),len(lows))<2:
        return 0
    return 1 if highs[-1]>highs[-2] and lows[-1]>lows[-2] else -1 if highs[-1]<highs[-2] and lows[-1]<lows[-2] else 0


def sr_blocks(direction,entry,tp,levels):
    return any(entry < p < tp if direction==1 else tp < p < entry for p in levels)


def double_blocks(bar,last_accepted):
    return 2 <= bar-last_accepted <= 4


def breakeven(stop_pips,cost_pips,rr):
    return (1+cost_pips/stop_pips)/(1+rr)


def stressed_pnl(pnl,risk,commission,ambiguous):
    return min(pnl,-risk-commission) if ambiguous else pnl


def r_stats(values):
    equity=peak=dd=0.0
    streak=longest=0
    for r in values:
        equity+=r
        peak=max(peak,equity)
        dd=max(dd,peak-equity)
        streak=streak+1 if r<0 else 0
        longest=max(longest,streak)
    return {'mean_r':equity/len(values) if values else None,'max_closed_dd_r':dd,'longest_loss_streak':longest}
