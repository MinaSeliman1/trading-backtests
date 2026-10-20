"""Figures de tous les scénarios principaux ; aucune performance recalculée."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import argparse
import hashlib
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter


BLUE='#2466a2';ORANGE='#c35a28';GRAY='#66717a'


def monthly_matrix(daily):
    data=daily.copy();date=pd.to_datetime(data.date)
    data['year']=date.dt.year;data['month']=date.dt.month
    grouped=data.groupby(['year','month']).return_net.apply(lambda r:(np.prod(1+r)-1)*100)
    return grouped.unstack('month').reindex(columns=range(1,13))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--results',type=Path,default=Path('results/2026-10-19'))
    args=parser.parse_args();out=args.results
    comparison=pd.read_csv(out/'comparison_all.csv')
    primary=comparison[(comparison.kind=='principal')&(comparison.slippage==.001)]
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.facecolor':'white','axes.titleweight':'bold'})
    figure_files=[]
    def save(fig,path):
        fig.savefig(path,dpi=130,facecolor='white');plt.close(fig);figure_files.append(path)
    for row in primary.itertuples():
        folder=out/row.instrument/row.label
        daily=pd.read_csv(folder/'daily.csv');trades=pd.read_csv(folder/'trades.csv')
        summary=json.loads((folder/'summary.json').read_text(encoding='utf-8'))
        dates=pd.to_datetime(daily.date)
        buyhold=100000*np.cumprod(1+daily.buyhold_return)
        title=f'{row.instrument} · {row.period} · {row.execution} · plafond cible {row.leverage_cap:g}x'
        subtitle=f'{daily.date.iloc[0]} au {daily.date.iloc[-1]} | {len(trades)} trades fermés | slippage 0,001 USD/action/côté'
        fig,axes=plt.subplots(2,1,figsize=(12,8),sharex=True,gridspec_kw={'height_ratios':[2,1]},layout='constrained')
        axes[0].plot(dates,daily.equity,color=BLUE,label='Noise Area net')
        axes[0].plot(dates,buyhold,color=GRAY,label=f'{row.instrument} buy & hold, dividendes réinvestis')
        if row.instrument=='QQQ':
            axes[0].plot(dates,100000*np.cumprod(1+daily.SPY_buyhold_return),color='#997b32',ls=':',label='SPY buy & hold, dividendes réinvestis')
        axes[0].set_yscale('log');axes[0].yaxis.set_major_formatter(FuncFormatter(lambda x,_:f'{x/1000:,.0f} k$'))
        axes[0].set_ylabel('Capital USD · logarithmique');axes[0].legend(loc='upper left');axes[0].grid(alpha=.15)
        daily_curve=np.r_[100000,daily.equity.to_numpy()]
        dd=(daily_curve[1:]/np.maximum.accumulate(daily_curve)[1:]-1)*100
        axes[1].fill_between(dates,dd,0,color=ORANGE,alpha=.45,label='DD aux clôtures quotidiennes')
        axes[1].axhline(-summary['max_drawdown_pct'],color=ORANGE,ls='--',lw=1,label=f'Pire DD minute : {summary["max_drawdown_pct"]:.2f} %')
        axes[1].set_ylabel('Drawdown (%)');axes[1].legend(loc='lower left');axes[1].grid(alpha=.15)
        fig.suptitle(title+'\n'+subtitle,fontsize=13)
        fig.supxlabel('Données Alpaca SIP raw ; frais 0,0035/action (min. 0,35/ordre), emprunt SHORT 1 %/an. Capital initial 100 000 USD.',fontsize=9)
        save(fig,folder/'capital_drawdown.png')
        fig,axes=plt.subplots(2,2,figsize=(13,9),layout='constrained')
        years=dates.dt.year
        annual=daily.groupby(years).return_net.apply(lambda r:(np.prod(1+r)-1)*100)
        bh=daily.groupby(years).buyhold_return.apply(lambda r:(np.prod(1+r)-1)*100)
        x=np.arange(len(annual))
        axes[0,0].bar(x-.2,annual,width=.4,color=BLUE,label='Stratégie nette')
        axes[0,0].bar(x+.2,bh,width=.4,color=GRAY,label='Buy & hold TR')
        axes[0,0].set_xticks(x,annual.index.astype(str));axes[0,0].axhline(0,color=GRAY,lw=.8)
        axes[0,0].set_title('Rendements annuels · années de bord partielles');axes[0,0].set_ylabel('%');axes[0,0].legend(fontsize=8)
        matrix=monthly_matrix(daily);limit=max(1,float(np.nanmax(np.abs(matrix))))
        heat=axes[0,1].imshow(matrix,aspect='auto',cmap='RdBu',vmin=-limit,vmax=limit)
        axes[0,1].set_xticks(range(12),['J','F','M','A','M','J','J','A','S','O','N','D'])
        axes[0,1].set_yticks(range(len(matrix)),matrix.index.astype(str));axes[0,1].set_title('Rendements mensuels nets (%)')
        for i in range(matrix.shape[0]):
            for j in range(12):
                value=matrix.iloc[i,j]
                if np.isfinite(value):axes[0,1].text(j,i,f'{value:.1f}',ha='center',va='center',fontsize=7,color='white' if abs(value)>.55*limit else '#222222')
        fig.colorbar(heat,ax=axes[0,1],fraction=.035)
        axes[1,0].hist(trades.net_bps,bins=45,color=BLUE,alpha=.8)
        axes[1,0].axvline(0,color=ORANGE,lw=1);axes[1,0].set_title('Distribution des trades fermés')
        axes[1,0].set_xlabel('P&L net / nominal d’entrée (bps)');axes[1,0].set_ylabel('Nombre de trades')
        grouped=trades.groupby('direction').net_pnl.sum().reindex(['LONG','SHORT'],fill_value=0)
        axes[1,1].bar(grouped.index,grouped/1000,color=[BLUE,ORANGE]);axes[1,1].axhline(0,color=GRAY,lw=.8)
        axes[1,1].set_ylabel('P&L net (milliers USD)');axes[1,1].set_title('Contribution LONG / SHORT')
        fig.suptitle(title+'\n'+subtitle,fontsize=13)
        fig.supxlabel('Années et mois de bord partiels. Comptes et périodes autonomes ; ne pas additionner les variantes.',fontsize=9)
        save(fig,folder/'behavior.png')
        if row.period=='B':
            controls=json.loads((folder/'controls.json').read_text(encoding='utf-8'))
            fig,axes=plt.subplots(1,2,figsize=(12,4),layout='constrained')
            for ax,values,observed,xlabel,p in [
                (axes[0],(np.asarray(controls['random_final_equity'])/100000-1)*100,summary['total_return_pct'],'Rendement total net (%)',controls['p_random_final_equity_ge_strategy']),
                (axes[1],controls['random_sharpe'],summary['sharpe'],'Sharpe annualisé, taux sans risque 0',controls['p_random_sharpe_ge_strategy'])]:
                ax.hist(values,bins=40,color=GRAY,alpha=.65,label='1 000 directions aléatoires')
                ax.axvline(observed,color=BLUE,lw=2,label='Noise Area observée');ax.set_xlabel(xlabel);ax.set_ylabel('Simulations')
                ax.set_title(f'p empirique unilatéral = {p:.3f}');ax.legend(fontsize=8)
            fig.suptitle(title+' · contrôles aux mêmes horaires',fontsize=13)
            fig.supxlabel('Heures conditionnées aux trades de la stratégie, quantités recomposées ; p non corrigées pour comparaisons multiples.',fontsize=9)
            save(fig,folder/'random_controls.png')
    fig,axes=plt.subplots(2,2,figsize=(13,9),layout='constrained')
    for i,symbol in enumerate(['SPY','QQQ']):
        for j,cap in enumerate([1,4]):
            ax=axes[i,j]
            for execution,style in [('close','--'),('next_open','-')]:
                label=f'B_{execution}_L{cap}_s0.001_principal';daily=pd.read_csv(out/symbol/label/'daily.csv')
                dates=pd.to_datetime(daily.date)
                ax.plot(dates,daily.equity,ls=style,color=BLUE if execution=='next_open' else ORANGE,label=execution)
            ax.plot(dates,100000*np.cumprod(1+daily.buyhold_return),color=GRAY,label=f'{symbol} buy & hold TR')
            ax.set_yscale('log');ax.set_title(f'{symbol} · plafond cible {cap}x');ax.yaxis.set_major_formatter(FuncFormatter(lambda x,_:f'{x/1000:.0f} k$'))
            ax.legend(fontsize=8);ax.grid(alpha=.15)
            ax.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    fig.suptitle('Noise Area · période B demandée : 1er mai 2024 – 16 octobre 2026\nComptes séparés de 100 000 USD, frais et emprunt inclus, slippage 0,001 USD/côté',fontsize=14)
    save(fig,out/'B_OVERVIEW.png')
    receipts={p.relative_to(out).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in figure_files}
    (out/'FIGURES_PROVENANCE.json').write_text(json.dumps(dict(figures=len(receipts),sha256=receipts,script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()),indent=2),encoding='utf-8')
    print(f'PASS: {len(receipts)} figures produites depuis les exports, sans modifier les performances.')


if __name__=='__main__':main()
