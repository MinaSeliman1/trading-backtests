from dataclasses import dataclass
from pathlib import Path
import hashlib
import pandas as pd
import numpy as np
import exchange_calendars as xcals


@dataclass
class Dataset:
    sessions: list
    quality: pd.DataFrame
    manifest: dict


def _timestamps(series, timezone):
    # ISO offsets may differ across DST. Convert aware timestamps together via UTC.
    samples=series.astype(str)
    if samples.str.fullmatch(r"\d+(\.\d+)?").all():
        numeric=pd.to_numeric(series)
        return pd.DatetimeIndex(pd.to_datetime(numeric,unit="ms" if numeric.median()>1e11 else "s",utc=True))
    has_zone=samples.str.contains(r"(?:Z|[+-]\d\d:\d\d)$",regex=True)
    if has_zone.all(): return pd.DatetimeIndex(pd.to_datetime(series,utc=True,format="mixed"))
    if has_zone.any(): raise ValueError("mixed aware/naive timezone timestamps")
    if timezone is None: raise ValueError("naive timestamps require --timezone")
    return pd.DatetimeIndex(pd.to_datetime(series,format="mixed")).tz_localize(timezone,ambiguous="raise",nonexistent="raise").tz_convert("UTC")


def dated_value(path, day, symbol, value):
    d=pd.read_csv(path,dtype={"contract":str})
    if "instrument" in d: d=d[d.instrument==symbol]
    d=d[d.effective_date.astype(str)<=day].sort_values("effective_date")
    if d.empty: raise ValueError(f"no {value} effective before {day}")
    return d.iloc[-1][value]


def load_csv(path, symbol, timezone=None, timestamp_at="open", rolls=None,
             margins=None, calendar=None, allow_continuous=False, strict_futures=False):
    path=Path(path); df=pd.read_csv(path)
    df.columns=[str(c).strip().lower() for c in df.columns]
    df=df.rename(columns={"time":"timestamp","datetime":"timestamp","date":"timestamp","vol":"volume","ts_event":"timestamp","symbol":"contract"})
    required=["timestamp","open","high","low","close","volume"]
    if any(c not in df for c in required): raise ValueError(f"required columns: {required}")
    index=_timestamps(df.pop("timestamp"),timezone).tz_convert("America/New_York")
    if timestamp_at=="close": index=index-pd.Timedelta(minutes=1)
    elif timestamp_at!="open": raise ValueError("timestamp_at must be open or close")
    df.index=index
    for col in required[1:]: df[col]=pd.to_numeric(df[col],errors="coerce")
    if df.empty: raise ValueError("empty input")
    futures=symbol in ("ES","NQ")
    if futures and not allow_continuous and ("contract" not in df or rolls is None):
        raise ValueError("futures require contract identity and a dated rolls CSV; continuous only with --allow-continuous")
    if futures and strict_futures and (margins is None or calendar is None):
        raise ValueError("strict futures require dated margins and explicit CME/cash-window calendar")
    if futures and allow_continuous and "contract" not in df: df["contract"]=symbol+"_CONTINUOUS_UNVERIFIED"
    before=len(df); df=df.reset_index(names="timestamp").drop_duplicates().set_index("timestamp")
    removed=before-len(df); df=df.sort_index()
    dates=sorted(set(df.index.strftime("%Y-%m-%d")))
    start=dates[0]; end=dates[-1]
    cal=xcals.get_calendar("XNYS",start=pd.Timestamp(start)-pd.Timedelta(days=7),end=pd.Timestamp(end)+pd.Timedelta(days=7))
    schedule=cal.schedule.loc[start:end]
    if calendar:
        schedule=pd.read_csv(calendar).set_index("date")
        schedule["open"]=pd.to_datetime(schedule["open"],utc=True)
        schedule["close"]=pd.to_datetime(schedule["close"],utc=True)
        schedule=schedule.loc[(schedule.index>=start)&(schedule.index<=end)]
    sessions=[]; reports=[]
    expected_dates=set()
    for day_label,row in schedule.iterrows():
        day=str(day_label)[:10]; expected_dates.add(day)
        opening=pd.Timestamp(row["open"]).tz_convert("America/New_York")
        closing=pd.Timestamp(row["close"]).tz_convert("America/New_York")
        # Explicit calendar can only narrow the specified American window.
        opening=max(opening,pd.Timestamp(day+" 09:30",tz="America/New_York"))
        closing=min(closing,pd.Timestamp(day+" 16:00",tz="America/New_York"))
        if closing<=opening: continue
        raw=df[(df.index>=opening)&(df.index<closing)].copy()
        contract=symbol
        if futures and rolls:
            contract=str(dated_value(rolls,day,symbol,"contract"))
            raw=raw[raw.contract.astype(str)==contract]
        elif futures and not raw.empty:
            unique=raw.contract.unique()
            contract=str(unique[0]) if len(unique)==1 else "MIXED"
        expected=pd.date_range(opening,closing,freq="min",inclusive="left")
        missing=expected.difference(raw.index)
        duplicates=int(raw.index.duplicated(keep=False).sum())
        off_grid=int((~raw.index.isin(expected)).sum())
        prices=raw[["open","high","low","close"]]
        invalid=(~np.isfinite(prices).all(axis=1))|(prices.min(axis=1)<=0)|(~np.isfinite(raw.volume))|(raw.volume<0)
        invalid|=(raw.high<raw[["open","low","close"]].max(axis=1))|(raw.low>raw[["open","high","close"]].min(axis=1))
        first_missing=len(expected[:5].difference(raw.index))
        reasons=[]
        if missing.size: reasons.append("missing_minutes")
        if duplicates: reasons.append("conflicting_duplicates")
        if off_grid: reasons.append("off_minute_timestamps")
        if invalid.sum(): reasons.append("invalid_ohlcv")
        if contract=="MIXED": reasons.append("multiple_contracts")
        if opening.strftime("%H:%M")!="09:30": reasons.append("missing_opening_range")
        reports.append(dict(date=day,status="excluded" if reasons else "accepted",reason="|".join(reasons),
                            expected_minutes=len(expected),observed_minutes=len(raw),missing_minutes=len(missing),
                            missing_opening_minutes=first_missing,conflicting_rows=duplicates,invalid_ohlcv=int(invalid.sum()),
                            off_grid_rows=off_grid,session_close=str(closing),contract=contract))
        if not reasons:
            raw.attrs.update(contract=contract,close=str(closing))
            if margins:
                margin=float(dated_value(margins,day,symbol,"margin_per_unit"))
                if not np.isfinite(margin) or margin<=0: raise ValueError("margin must be positive")
                raw.attrs["margin"]=margin
            sessions.append(raw)
    for day in set(dates)-expected_dates:
        reports.append(dict(date=day,status="excluded",reason="non_session_day"))
    manifest=dict(path=str(path.resolve()),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),instrument=symbol,
                  first_timestamp=str(df.index.min()),last_timestamp=str(df.index.max()),raw_rows=before,
                  identical_duplicates_removed=removed,valid_sessions=len(sessions),calendar="explicit" if calendar else "XNYS",
                  timestamp_at=timestamp_at,source_timezone=timezone or "offset_or_epoch_in_file",
                  continuous_unverified=bool(futures and allow_continuous),strict_futures=strict_futures)
    for key,p in [("rolls",rolls),("margins",margins),("calendar_override",calendar)]:
        if p: manifest[key]={"path":str(Path(p).resolve()),"sha256":hashlib.sha256(Path(p).read_bytes()).hexdigest()}
    return Dataset(sessions,pd.DataFrame(reports).sort_values("date"),manifest)
