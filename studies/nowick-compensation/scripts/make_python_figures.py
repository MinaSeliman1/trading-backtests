"""Standalone research figures from executed CSVs; no synthetic performance."""
import argparse
from pathlib import Path
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
PAIRS=['GBPUSD','USDJPY','AUDUSD']
COLORS={'GBPUSD':'#2563eb','USDJPY':'#e58013','AUDUSD':'#14806a'}

def main():
    p=argparse.ArgumentParser(); p.add_argument('--run-id',default='2026-10-24-python-v1'); args=p.parse_args()
    run=ROOT/'results'/args.run_id
    comparison=pd.read_csv(run/'comparison_all.csv')
    out=run/'figures'; out.mkdir(exist_ok=True)
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.facecolor':'white','axes.grid':True,'grid.alpha':.18})
    def save(fig,name):
        fig.savefig(out/(name+'.png'),dpi=160,bbox_inches='tight')
        fig.savefig(out/(name+'.svg'),bbox_inches='tight')
        plt.close(fig)
    fig,ax=plt.subplots(figsize=(11,5.5))
    for pair in PAIRS:
        df=pd.read_csv(run/pair/'ALL/reference/daily_equity.csv')
        dates=pd.to_datetime(df.date)
        # Break curves across long source outages instead of drawing continuity.
        x=[]; y=[]
        for i,(date,equity) in enumerate(zip(dates,df.equity)):
            if i and (date-dates.iloc[i-1]).days>4:
                x.append(dates.iloc[i-1]+pd.Timedelta(days=1)); y.append(np.nan)
            x.append(date); y.append(equity/1000)
        ax.plot(x,y,label=pair,color=COLORS[pair],lw=1.4)
    ax.axhline(100,color='#555',lw=.8)
    ax.set(title='Nowick : capital simulé après coûts — référence',ylabel='Indice de capital, départ 100',xlabel='2015–2024 ; trous de données visibles comme interruptions')
    ax.legend(ncol=3,loc='upper right')
    fig.text(.08,-.01,'Modèle Bid à 1 minute ; coût synthétique 1 pip A/R ; sorties sur trou pénalisées. Aucun résultat TradingView.',fontsize=9)
    save(fig,'equity_reference')
    fig,ax=plt.subplots(figsize=(10,4.8))
    base=comparison[comparison.variant=='reference']
    xpos=np.arange(3); width=.24
    for i,period in enumerate(['A','B','ALL']):
        values=[base[(base.pair==p)&(base.period==period)].iloc[0].expectancy_r for p in PAIRS]
        ax.bar(xpos+(i-1)*width,values,width,label=period,color=['#9aa9bb','#476485','#132e50'][i])
    ax.axhline(0,color='black',lw=.8)
    ax.set_xticks(xpos,PAIRS)
    ax.set(title='Espérance nette : deux moitiés chronologiques',ylabel='R par trade fermé, pénalités incluses')
    ax.legend(title='A 2015–19 / B 2020–24',ncol=3)
    save(fig,'chronological_expectancy')
    fig,ax=plt.subplots(figsize=(10,4.8))
    for pair in PAIRS:
        rows=comparison[(comparison.pair==pair)&(comparison.period=='ALL')].set_index('variant')
        ax.plot([1,2,3],[rows.loc[k,'return_pct'] for k in ['reference','cost_2pips','cost_3pips']],marker='o',label=pair,color=COLORS[pair])
    ax.axhline(0,color='black',lw=.8)
    ax.set(title='Sensibilité au coût total aller-retour',xlabel='Coût en pips ; portefeuille recalculé à chaque niveau',ylabel='Variation du capital (%)',xticks=[1,2,3])
    ax.legend(ncol=3)
    save(fig,'cost_sensitivity')
    fig,axes=plt.subplots(3,1,figsize=(12,7),sharex=True)
    for ax,pair in zip(axes,PAIRS):
        d=pd.read_csv(run/f'{pair}_daily_coverage.csv')
        d['month']=pd.to_datetime(d.date).dt.to_period('M').astype(str)
        monthly=d.groupby('month').agg(present=('sum','sum'),expected=('count','sum'))
        missing=100*(1-monthly.present/monthly.expected)
        ax.bar(np.arange(len(monthly)),missing,color=COLORS[pair],width=.9)
        ax.set_ylabel(pair+'\n% absentes')
        ax.set_ylim(0,max(5,float(missing.max())*1.15))
    axes[0].set_title('Couverture : minutes absentes dans la fenêtre 02–08 New York des jours ouvrés')
    axes[-1].set_xticks(np.arange(0,len(monthly),12),monthly.index[::12],rotation=30)
    fig.text(.08,.01,'Enveloppe de semaine incluant les jours fériés ; ces pourcentages ne certifient pas les heures réellement négociables.',fontsize=9)
    fig.tight_layout(rect=(0,.04,1,1))
    save(fig,'coverage_monthly')
    fig,ax=plt.subplots(figsize=(11,5))
    variants=['reference','swing_on','sr_on','double_on','filters_all']
    x=np.arange(len(variants)); w=.24
    for j,pair in enumerate(PAIRS):
        rows=comparison[(comparison.pair==pair)&(comparison.period=='ALL')].set_index('variant')
        ax.bar(x+(j-1)*w,[rows.loc[k,'expectancy_r'] for k in variants],w,label=pair,color=COLORS[pair])
    ax.axhline(0,color='black',lw=.8)
    ax.set_xticks(x,['Référence','Swing ON','S/R ON','Double ON','Les trois ON'])
    ax.set(title='Filtres fixés avant résultats — période ALL',ylabel='Espérance nette R/trade')
    ax.legend(ncol=3)
    save(fig,'filter_comparison')
    print('5 figures PNG/SVG generated from executed outputs.')

if __name__=='__main__':main()
