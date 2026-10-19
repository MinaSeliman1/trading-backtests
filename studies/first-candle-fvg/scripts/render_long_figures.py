"""Figures de synthèse IS/OOS, lues exclusivement dans les résultats calculés."""
from pathlib import Path
import argparse
import hashlib
import json
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


def date_axis(ax,first,last):
    start,end=pd.Timestamp(first),pd.Timestamp(last)
    months=(end.year-start.year)*12+end.month-start.month+1
    required=max(1,int(np.ceil(months/7)))
    interval=next((n for n in [1,2,3,6,12] if n>=required),required)
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=interval))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.tick_params(axis='x',rotation=25)


def refresh_diagnostics(folder):
    """Les dates mensuelles sont espacées pour rester lisibles sur trois années."""
    summary=json.loads((folder/'summary.json').read_text())
    equity=pd.read_csv(folder/'equity_intraday.csv')
    monthly=pd.read_csv(folder/'monthly.csv'); trades=pd.read_csv(folder/'trades.csv')
    fig,axes=plt.subplots(2,2,figsize=(13,8),layout='constrained')
    fig.suptitle(summary['label']+' — données réelles')
    if len(equity):
        y=np.r_[100000.,equity.equity.to_numpy()]
        t=pd.to_datetime(equity.timestamp,utc=True)
        x=[pd.Timestamp(summary['first_session'],tz='America/New_York')+pd.Timedelta(hours=9,minutes=30),*t]
        axes[0,0].plot(x,y,lw=1.2)
        axes[0,1].fill_between(x,100*(y/np.maximum.accumulate(y)-1),0,color='#c44e52',alpha=.6)
        for ax in axes[0]:
            date_axis(ax,summary['first_session'],summary['last_session'])
    axes[0,0].set(title='Capital (USD)',ylabel='USD')
    axes[0,1].set(title='Drawdown aux marques 1 minute / exécutions',ylabel='%')
    values=monthly.net_pnl.to_numpy(); axes[1,0].bar(np.arange(len(values)),values,color='#4c72b0')
    step=max(1,int(np.ceil(len(values)/10))); ticks=np.arange(0,len(values),step)
    axes[1,0].set_xticks(ticks,monthly.month.iloc[ticks],rotation=45,ha='right')
    axes[1,0].set(title='P&L mensuel net',ylabel='USD')
    if len(trades): axes[1,1].hist(trades.result_r,bins=min(25,max(3,len(trades))),color='#4c72b0',edgecolor='white')
    axes[1,1].set(title='Résultats nets par trade',xlabel='R',ylabel='Nombre')
    for ax in axes.flat: ax.grid(alpha=.2)
    fig.savefig(folder/'diagnostics.png',dpi=150); plt.close(fig)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results',type=Path,default=Path('results/alpaca_sip_long'))
    args=parser.parse_args()
    for segment in ['IS','OOS']:
        fig,axes=plt.subplots(2,2,figsize=(13,9),layout='constrained',sharex=True)
        for i,symbol in enumerate(['SPY','QQQ']):
            for variant,color in [('A','#176eaa'),('B','#cf571c')]:
                folder=args.results/symbol/f'{symbol}_{segment}_{variant}_slip1_principal'
                frame=pd.read_csv(folder/'daily.csv')
                dates=pd.to_datetime(frame.date)
                x=[dates.iloc[0]-pd.Timedelta(days=1),*dates]
                y=np.r_[100000.,frame.equity.to_numpy()]
                axes[i,0].plot(x,y,label=f'Stop {variant}',color=color,lw=1.5)
                intraday=pd.read_csv(folder/'equity_intraday.csv')
                # Drawdown uses all recorded minute-close/execution marks, not daily closes alone.
                t=pd.to_datetime(intraday.timestamp,utc=True)
                values=np.r_[100000.,intraday.equity.to_numpy()]
                dd=100*(values/np.maximum.accumulate(values)-1)
                axes[i,1].plot([x[0],*t],dd,label=f'Stop {variant}',color=color,lw=1.)
            axes[i,0].set_title(f'{symbol} — capital aux clôtures de séance')
            axes[i,1].set_title(f'{symbol} — drawdown aux marques 1 minute / exécutions')
            axes[i,0].set_ylabel('USD'); axes[i,1].set_ylabel('%')
        for ax in axes.flat:
            ax.grid(alpha=.2); ax.legend(frameon=False)
            date_axis(ax,frame.date.iloc[0],frame.date.iloc[-1])
        fig.suptitle(f'{segment} — paramètres principaux, slippage 1 tick par exécution\n100 000 USD indépendants par instrument et stop ; commissions et spread inclus')
        fig.savefig(args.results/f'{segment}_capital_drawdown.png',dpi=160)
        plt.close(fig)
        fig,axes=plt.subplots(2,2,figsize=(14,9),layout='constrained')
        for i,symbol in enumerate(['SPY','QQQ']):
            for j,variant in enumerate(['A','B']):
                folder=args.results/symbol/f'{symbol}_{segment}_{variant}_slip1_principal'
                monthly=pd.read_csv(folder/'monthly.csv'); trades=pd.read_csv(folder/'trades.csv')
                ax=axes[i,j]; values=monthly.net_pnl.to_numpy()
                ax.bar(np.arange(len(values)),values,color=np.where(values>=0,'#176eaa','#cf571c'))
                step=max(1,int(np.ceil(len(values)/12)))
                ticks=np.arange(0,len(values),step)
                ax.set_xticks(ticks,monthly.month.iloc[ticks],rotation=45,ha='right')
                ax.axhline(0,color='black',lw=.6); ax.set_title(f'{symbol} — stop {variant}')
                ax.set_ylabel('P&L net (USD)'); ax.grid(axis='y',alpha=.2)
        fig.suptitle(f'{segment} — résultats mensuels, scénario principal 1 tick')
        fig.savefig(args.results/f'{segment}_monthly.png',dpi=160); plt.close(fig)
        fig,axes=plt.subplots(2,2,figsize=(12,8),layout='constrained',sharex=True)
        all_r=[]
        for symbol in ['SPY','QQQ']:
            for variant in ['A','B']:
                t=pd.read_csv(args.results/symbol/f'{symbol}_{segment}_{variant}_slip1_principal'/'trades.csv')
                all_r.extend(t.result_r)
        bins=np.linspace(min(all_r),max(all_r),26) if all_r else np.linspace(-2,4,26)
        for i,symbol in enumerate(['SPY','QQQ']):
            for j,variant in enumerate(['A','B']):
                t=pd.read_csv(args.results/symbol/f'{symbol}_{segment}_{variant}_slip1_principal'/'trades.csv')
                ax=axes[i,j]; ax.hist(t.result_r,bins=bins,color='#176eaa',edgecolor='white')
                ax.set(title=f'{symbol} — stop {variant} ({len(t)} trades)',xlabel='Résultat net / risque initial hors frais (R)',ylabel='Trades')
                ax.axvline(0,color='black',lw=.8); ax.grid(axis='y',alpha=.2)
        fig.suptitle(f'{segment} — distribution des résultats, scénario principal 1 tick')
        fig.savefig(args.results/f'{segment}_distribution_r.png',dpi=160); plt.close(fig)
    folders=sorted(p.parent for p in args.results.glob('*/*/summary.json'))
    for folder in folders: refresh_diagnostics(folder)
    receipt=dict(script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                 refreshed_diagnostics=len(folders),summary_figures=6,
                 operation='Rendering only; results CSV and statistics unchanged',
                 figures={str(p.relative_to(args.results)):hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in args.results.rglob('*.png')})
    (args.results/'FIGURES_PROVENANCE.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    print(f'Six figures IS/OOS et {len(folders)} diagnostics exportés depuis les CSV ; aucune nouvelle simulation.')


if __name__=='__main__': main()
