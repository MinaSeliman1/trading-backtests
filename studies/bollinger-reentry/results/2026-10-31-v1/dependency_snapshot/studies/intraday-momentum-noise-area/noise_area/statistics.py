"""Mesures explicites, benchmarks à temps fixés et bootstrap de séances."""
import numpy as np
import pandas as pd


def sharpe(values,axis=None):
    values=np.asarray(values)
    mean=values.mean(axis=axis)
    count=values.size if axis is None else values.shape[axis]
    if count<2: return np.full_like(mean,np.nan,dtype=float)
    std=values.std(axis=axis,ddof=1)
    with np.errstate(divide='ignore',invalid='ignore'):
        return np.where(std>1e-14,mean/std*np.sqrt(252),np.nan)


def return_statistics(returns,dates):
    r=np.asarray(returns,dtype=float);days=pd.DatetimeIndex(dates)
    eq=100000*np.cumprod(1+r);curve=np.r_[100000,eq]
    peaks=np.maximum.accumulate(curve);dd=1-curve/peaks
    trough=int(np.argmax(dd));peak_index=int(np.argmax(curve[:trough+1]))
    recovered=np.flatnonzero(curve[trough+1:]>=peaks[trough])
    recovery_index=int(trough+1+recovered[0]) if len(recovered) else len(curve)-1
    timeline=pd.DatetimeIndex([days[0]-pd.Timedelta(days=1),*days])
    years=(days[-1]-days[0]).days/365.2425+1/365.2425
    grouped=pd.Series(r,index=days)
    monthly=grouped.groupby(days.strftime('%Y-%m')).apply(lambda x:float(np.prod(1+x)-1))
    yearly=grouped.groupby(days.year).apply(lambda x:float(np.prod(1+x)-1))
    downside=np.sqrt(np.mean(np.minimum(r,0)**2))
    return dict(total_return_pct=float((eq[-1]/100000-1)*100),final_equity=float(eq[-1]),
                cagr_pct=float(((eq[-1]/100000)**(1/years)-1)*100) if eq[-1]>0 else None,
                sharpe=float(sharpe(r)),sortino=float(r.mean()/downside*np.sqrt(252)) if downside>0 else None,
                volatility_annual_pct=float(r.std(ddof=1)*np.sqrt(252)*100) if len(r)>1 else None,daily_mean=float(r.mean()),
                max_daily_close_drawdown_pct=float(dd.max()*100),
                worst_drawdown_duration_calendar_days=int((timeline[recovery_index]-timeline[peak_index]).days),
                worst_drawdown_recovered=bool(len(recovered)),worst_day_pct=float(r.min()*100),
                worst_day=str(days[int(r.argmin())].date()),worst_month_pct=float(monthly.min()*100),
                worst_month=str(monthly.idxmin()),worst_year_pct=float(yearly.min()*100),worst_year=int(yearly.idxmin()),
                sessions=len(r),first_session=str(days[0].date()),last_session=str(days[-1].date()))


def block_bootstrap(returns,benchmark,repetitions=5000,seed=20261019):
    r=np.asarray(returns);b=np.asarray(benchmark);n=len(r);block=5
    rng=np.random.default_rng(seed)
    starts=rng.integers(0,n,size=(repetitions,int(np.ceil(n/block))))
    indices=((starts[:,:,None]+np.arange(block))%n).reshape(repetitions,-1)[:,:n]
    sampled=r[indices];sampled_b=b[indices]
    def interval(values):
        values=np.asarray(values);values=values[np.isfinite(values)]
        return np.quantile(values,[.025,.975]).tolist() if len(values) else None
    return dict(repetitions=repetitions,seed=seed,block_length=block,method='circular day blocks, paired benchmark dates',
                daily_mean_ci95=interval(sampled.mean(axis=1)),sharpe_ci95=interval(sharpe(sampled,axis=1)),
                sharpe_minus_buyhold_ci95=interval(sharpe(sampled,axis=1)-sharpe(sampled_b,axis=1)))


def timed_benchmarks(trades,daily,slippage,borrow_rate,repetitions=1000,seed=20261019):
    rng=np.random.default_rng(seed);capital=np.full(repetitions,100000.);long_capital=100000.
    random_returns=[];long_returns=[]
    groups={date:g for date,g in trades.groupby('date')}
    for row in daily.itertuples():
        previous=capital.copy();long_previous=long_capital
        group=groups.get(row.date)
        if group is not None:
            first=group.iloc[0]
            qty=np.floor(np.maximum(capital,0)*first.target_leverage/first.opening_price)
            long_qty=np.floor(max(long_capital,0)*first.target_leverage/first.opening_price)
            fee=np.where(qty>0,2*np.maximum(.35,qty*.0035),0.)
            long_fee=2*max(.35,long_qty*.0035) if long_qty>0 else 0.
            for trade in group.itertuples():
                sides=rng.choice([-1,1],size=repetitions)
                move=trade.exit_reference-trade.entry_reference
                borrow=np.where(sides<0,qty*(trade.entry_reference-slippage)*borrow_rate/360,0.)
                capital+=qty*(sides*move-2*slippage)-fee-borrow
                long_capital+=long_qty*(move-2*slippage)-long_fee
        random_returns.append(np.divide(capital-previous,previous,out=np.zeros_like(capital),where=previous>0))
        long_returns.append((long_capital-long_previous)/long_previous if long_previous>0 else 0.)
    returns=np.array(random_returns).T
    return dict(repetitions=repetitions,seed=seed,random_final_equity=capital.tolist(),
                random_sharpe=sharpe(returns,axis=1).tolist(),always_long=return_statistics(long_returns,daily.date),
                always_long_daily=long_returns,bankrupt_random_paths=int((capital<=0).sum()))


def summarize(result,benchmark,spy_benchmark):
    daily=result.daily;trades=result.trades;r=daily.return_net.to_numpy();b=np.asarray(benchmark)
    stats=return_statistics(r,daily.date)
    positive=trades[trades.net_pnl>0];negative=trades[trades.net_pnl<0]
    total_profit=float(positive.net_pnl.sum());total_loss=-float(negative.net_pnl.sum())
    losses=0;longest=0
    for pnl in trades.net_pnl:
        losses=losses+1 if pnl<0 else 0;longest=max(longest,losses)
    mean_gain=float(positive.net_pnl.mean()) if len(positive) else None
    mean_loss=float(negative.net_pnl.mean()) if len(negative) else None
    stats.update(net_pnl=float(trades.net_pnl.sum()),trades=len(trades),trades_per_day=len(trades)/len(daily),
                 days_traded_pct=float((daily.trades>0).mean()*100),win_rate_pct=len(positive)/len(trades)*100 if len(trades) else None,
                 profit_factor=total_profit/total_loss if total_loss>0 else None,average_gain=mean_gain,average_loss=mean_loss,
                 gain_loss_ratio=mean_gain/-mean_loss if mean_gain is not None and mean_loss is not None else None,
                 mean_trade_bps=float(trades.net_bps.mean()) if len(trades) else None,longest_loss_streak=longest,
                 max_drawdown_usd=result.summary['max_drawdown_usd'],max_drawdown_pct=result.summary['max_drawdown_pct']*100,
                 target_leverage_mean=float(daily.loc[daily.quantity>0,'target_leverage'].mean()),
                 target_leverage_max=float(daily.target_leverage.max()),
                 entry_leverage_mean=float(trades.entry_leverage.mean()) if len(trades) else None,
                 entry_leverage_max=float(trades.entry_leverage.max()) if len(trades) else None,
                 commission=float(trades.commission.sum()),borrow_fee=float(trades.borrow_fee.sum()),
                 eligible_sessions=int((daily.eligibility=='eligible').sum()),
                 flat_data_or_warmup_sessions=int((daily.eligibility!='eligible').sum()))
    for name,values in [('instrument',b),('SPY',np.asarray(spy_benchmark))]:
        variance=np.var(values,ddof=1)
        stats[f'beta_vs_{name}']=float(np.cov(r,values,ddof=1)[0,1]/variance) if variance>0 else None
        stats[f'correlation_vs_{name}']=float(np.corrcoef(r,values)[0,1]) if variance>0 and r.std()>0 else None
    net=stats['net_pnl'];best=daily.nlargest(10,'net_pnl')
    stats['top10_days_pnl']=float(best.net_pnl.sum())
    stats['top10_days_share_of_total_pct']=stats['top10_days_pnl']/net*100 if net else None
    stripped=r.copy();stripped[best.index.to_numpy()]=0
    stats['return_without_top10_days_pct']=float((np.prod(1+stripped)-1)*100)
    return stats
