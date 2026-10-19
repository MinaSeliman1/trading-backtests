from pathlib import Path
import json
from math import sqrt
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def _streak(values, positive):
    current=best=0
    for x in values:
        current=current+1 if ((x>0) if positive else (x<0)) else 0
        best=max(best,current)
    return best


def metrics(trades,equity,config,session_count):
    pnl=trades.net_pnl.to_numpy() if len(trades) else np.array([])
    r=trades.result_r.to_numpy() if len(trades) else np.array([])
    win=pnl>0; loss=pnl<0
    curve=np.r_[config.initial_capital,equity.equity.to_numpy() if len(equity) else []]
    peaks=np.maximum.accumulate(curve); dd=peaks-curve
    gains=float(pnl[win].sum()); losses=float(-pnl[loss].sum())
    avgwin=float(r[win].mean()) if win.any() else None
    avgloss=float(r[loss].mean()) if loss.any() else None
    total=float(pnl.sum()); n=len(pnl)
    p=float(win.mean()) if n else None
    if n:
        z=1.95996398454; center=(p+z*z/(2*n))/(1+z*z/n)
        width=z*sqrt(p*(1-p)/n+z*z/(4*n*n))/(1+z*z/n)
        win_ci=[center-width,center+width]
    else: win_ci=None
    return dict(trades=n,winners=int(win.sum()),losers=int(loss.sum()),breakeven=int((pnl==0).sum()),
                win_rate=p,win_rate_wilson_95=win_ci,profit_factor=gains/losses if losses else None,
                profit_factor_status="no_losses" if n and not losses else "defined" if losses else "no_trades",
                net_pnl=total,net_return_pct=total/config.initial_capital*100,
                expectancy_r=float(r.mean()) if n else None,average_win_r=avgwin,average_loss_r=avgloss,
                win_loss_ratio=avgwin/abs(avgloss) if avgwin is not None and avgloss else None,
                max_drawdown_usd=float(dd.max()),max_drawdown_pct=float((dd/peaks*100).max()),
                longest_loss_streak=_streak(pnl,False),longest_win_streak=_streak(pnl,True),
                actual_risk_mean_usd=float(trades.initial_risk_usd.mean()) if n else None,
                actual_risk_max_usd=float(trades.initial_risk_usd.max()) if n else None,
                actual_risk_mean_pct=float(trades.risk_fraction.mean()*100) if n else None,
                planned_loss_max_usd=float(trades.planned_loss_usd.max()) if n else None,
                max_exposure_usd=float(trades.exposure_usd.max()) if n else 0.,
                max_exposure_pct=float(trades.exposure_fraction.max()*100) if n and "exposure_fraction" in trades else None,
                average_duration_minutes=float(trades.duration_minutes.mean()) if n else None,
                total_fees=float(trades.fees.sum()) if n else 0.,valid_sessions=session_count,
                trades_per_five_sessions=n/session_count*5 if session_count else None,
                pnl_excluding_best_3_trades=float(pnl.sum()-np.sort(pnl[pnl>0])[-3:].sum()) if n else 0.)


def split_sessions(sessions,span_days):
    if len(sessions)<252 or span_days<365: return {"exploratoire":sessions}
    boundary=int(len(sessions)*.7)
    return {"IS":sessions[:boundary],"OOS":sessions[boundary:]}


def bootstrap_sessions(trades,dates,reps=5000,block=1,seed=20261019):
    if len(trades)<20 or len(dates)<60:
        return dict(status="insufficient",trades=len(trades),sessions=len(dates),
                    minimum_trades=20,minimum_sessions=60,block_sessions=block)
    stats=trades.groupby("date").result_r.agg(["sum","count"]).reindex(dates,fill_value=0).to_numpy()
    rng=np.random.default_rng(seed); estimates=[]; n=len(dates)
    for offset in range(0,reps,128):
        m=min(128,reps-offset)
        starts=rng.integers(0,n,size=(m,int(np.ceil(n/block))))
        indices=(starts[:,:,None]+np.arange(block))%n
        indices=indices.reshape(m,-1)[:,:n]
        sampled=stats[indices].sum(axis=1)
        estimates.extend((sampled[:,0]/np.where(sampled[:,1]>0,sampled[:,1],np.nan)).tolist())
    samples=np.array(estimates); samples=samples[np.isfinite(samples)]
    return dict(status="computed",repetitions=reps,seed=seed,block_sessions=block,
                expectancy_r_ci95=np.quantile(samples,[.025,.975]).tolist(),
                fraction_bootstrap_expectancy_positive=float(np.mean(samples>0)),
                note="percentile bootstrap; fraction positive is not a Bayesian posterior or a p-value")


def table(frame):
    if frame.empty: return "Aucune observation."
    def fmt(x):
        if x is None or (isinstance(x,(float,np.floating)) and not np.isfinite(x)): return "—"
        return f"{x:.4f}" if isinstance(x,(float,np.floating)) else str(x).replace("|","/")
    return "| "+" | ".join(map(str,frame.columns))+" |\n|"+"|".join(["---"]*len(frame.columns))+"|\n"+"\n".join("| "+" | ".join(fmt(v) for v in row)+" |" for row in frame.itertuples(index=False,name=None))


def export_run(out,trades,equity,rejects,sessions,config,label,bootstrap_reps=5000,volatility_thresholds=None):
    out=Path(out); out.mkdir(parents=True,exist_ok=True)
    dates=[str(s.index[0].date()) for s in sessions]
    summary=metrics(trades,equity,config,len(sessions)); summary["label"]=label
    summary["first_session"]=dates[0] if dates else None; summary["last_session"]=dates[-1] if dates else None
    summary["bootstrap_iid"]=bootstrap_sessions(trades,dates,reps=bootstrap_reps)
    summary["bootstrap_block5"]=bootstrap_sessions(trades,dates,reps=bootstrap_reps,block=5)
    if len(trades):
        trades=trades.copy()
        trades["entry_hour"]=pd.to_datetime(trades.entry_time).dt.strftime("%H:00")
        if volatility_thresholds is not None:
            a,b=volatility_thresholds
            trades["volatility_regime"]=pd.cut(trades.opening_range_pct,[-np.inf,a,b,np.inf],labels=["low","middle","high"],include_lowest=True)
        else: trades["volatility_regime"]="unclassified_exploratory"
        for column in ["direction","entry_hour","volatility_regime"]:
            grouped=trades.groupby(column,observed=True).agg(trades=("net_pnl","size"),net_pnl=("net_pnl","sum"),expectancy_r=("result_r","mean"),win_rate=("net_pnl",lambda s:(s>0).mean()))
            grouped.to_csv(out/f"by_{column}.csv")
    else:
        trades=pd.DataFrame(columns=["date","instrument","direction","signal_time","entry_time","entry_price","stop","target","exit_time","exit_price","fees","slippage_usd","net_pnl","result_r"])
        for column in ["direction","entry_hour","volatility_regime"]:
            pd.DataFrame(columns=[column,"trades","net_pnl","expectancy_r","win_rate"]).to_csv(out/f"by_{column}.csv",index=False)
    trades.to_csv(out/"trades.csv",index=False)
    equity.to_csv(out/"equity_intraday.csv",index=False); rejects.to_csv(out/"rejected_signals.csv",index=False)
    daily=pd.DataFrame(index=pd.Index(dates,name="date"))
    daily["net_pnl"]=trades.groupby("date").net_pnl.sum().reindex(dates,fill_value=0) if len(trades) else 0.
    daily["equity"]=config.initial_capital+daily.net_pnl.cumsum()
    daily["month"]=[d[:7] for d in dates]
    monthly=daily.groupby("month").agg(net_pnl=("net_pnl","sum"),sessions=("net_pnl","size"),equity=("equity","last"))
    if len(monthly): monthly["return_pct"]=monthly.net_pnl/(monthly.equity-monthly.net_pnl)*100
    monthly.to_csv(out/"monthly.csv"); daily.to_csv(out/"daily.csv")
    if dates:
        weekly=daily.copy(); weekly["week"]=pd.to_datetime(weekly.index).to_period("W-SUN").astype(str)
        counts=trades.assign(week=pd.to_datetime(trades.date).dt.to_period("W-SUN").astype(str)).groupby("week").size() if len(trades) else pd.Series(dtype=float)
        weeks=sorted(set(weekly.week)); summary["trades_per_calendar_week"]=float(counts.reindex(weeks,fill_value=0).mean())
        pnl=daily.net_pnl.to_numpy()
        summary["pnl_excluding_best_3_sessions"]=float(pnl.sum()-np.sort(pnl[pnl>0])[-3:].sum())
    fig,axs=plt.subplots(2,2,figsize=(13,8),layout="constrained")
    fig.suptitle(label+" — données réelles" if "fixture" not in label else label+" — test artificiel")
    if len(equity):
        y=np.r_[config.initial_capital,equity.equity.to_numpy()]
        x=pd.to_datetime([sessions[0].index[0]]+list(equity.timestamp),utc=True)
        axs[0,0].plot(x,y,linewidth=1.2); axs[0,0].tick_params(axis="x",rotation=20)
        dd=100*(y/np.maximum.accumulate(y)-1)
        axs[0,1].fill_between(x,dd,0,color="#c44e52",alpha=.6); axs[0,1].tick_params(axis="x",rotation=20)
    axs[0,0].set(title="Capital (USD)",ylabel="USD")
    axs[0,1].set(title="Drawdown observé aux closes 1 minute",ylabel="%")
    if len(monthly): axs[1,0].bar(monthly.index,monthly.net_pnl,color="#4c72b0")
    axs[1,0].set(title="P&L mensuel net",ylabel="USD")
    if len(trades): axs[1,1].hist(trades.result_r,bins=min(25,max(3,len(trades))),color="#4c72b0",edgecolor="white")
    axs[1,1].set(title="Résultats nets par trade",xlabel="R",ylabel="Nombre")
    for ax in axs.flat: ax.grid(alpha=.2)
    fig.savefig(out/"diagnostics.png",dpi=150); plt.close(fig)
    (out/"summary.json").write_text(json.dumps(summary,indent=2,ensure_ascii=False,allow_nan=False),encoding="utf-8")
    return summary
