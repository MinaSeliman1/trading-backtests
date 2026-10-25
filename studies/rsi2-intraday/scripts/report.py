"""French report and standalone figures derived from complete frozen exports."""
from pathlib import Path
import argparse
import json
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+['| '+' | '.join(map(str,row))+' |' for row in rows])


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,default=ROOT/'results/2026-10-24-v1');out=parser.parse_args().out
    assert json.loads((out/'RUN_COMPLETE.json').read_text())['executions']==72
    c=pd.read_csv(out/'comparison_all.csv');primary=c[c.variant=='reference'];allrows=primary[primary.period=='ALL']
    annual=[];monthly=[];directions=[];ablations=[];quality=[]
    figures=out/'figures';figures.mkdir(exist_ok=True)
    plt.rcParams.update({'font.size':10,'axes.grid':True,'grid.alpha':.2,'axes.spines.top':False,'axes.spines.right':False})
    colors={'SPY':'#2563eb','QQQ':'#d97813'}
    fig,axes=plt.subplots(2,1,figsize=(11,7),sharex=True)
    for row in allrows.itertuples():
        d=pd.read_csv(out/row.label/'daily.csv');dates=pd.to_datetime(d.date)
        # Exclusions are not plotted as observed cash or interpolated prices.
        equity=d.equity.copy();equity[d.conditionally_excluded]=np.nan
        axes[0].plot(dates,equity,label=row.symbol,color=colors[row.symbol])
        dd=(d.equity/np.maximum.accumulate(np.r_[100000,d.equity])[1:]-1)*100;dd[d.conditionally_excluded]=np.nan
        axes[1].plot(dates,dd,label=row.symbol,color=colors[row.symbol])
    axes[0].axhline(100000,color='#555',lw=.8);axes[0].set(title='RSI(2) : référence LONG après frais',ylabel='Capital conditionnel (USD)')
    axes[1].set(ylabel='Drawdown des closes quotidiens (%)',xlabel='2016–16/10/2026 ; chauffe et contraintes de couverture conservées')
    for ax in axes:ax.legend()
    fig.tight_layout();fig.savefig(figures/'equity_drawdown.png',dpi=160);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(11,4.5))
    for ax,symbol in zip(axes,['SPY','QQQ']):
        for period in ['A','B','ALL']:
            z=c[(c.symbol==symbol)&(c.period==period)&c.variant.isin(['reference','cost_0.02','cost_0.03','cost_0.05'])].sort_values('slippage')
            ax.plot(z.slippage,z.total_return_pct,marker='o',label=period)
        ax.axhline(0,color='#555',lw=.8);ax.set(title=symbol,xlabel='Friction USD/action/côté',ylabel='Résultat net conditionnel (%)');ax.legend()
    fig.suptitle('Sensibilité aux frais ; capital recalculé à chaque coût');fig.tight_layout();fig.savefig(figures/'cost_sensitivity.png',dpi=160);plt.close(fig)
    fig,ax=plt.subplots(figsize=(10,4.5))
    for j,symbol in enumerate(['SPY','QQQ']):
        rows=primary[primary.symbol==symbol].set_index('period')
        ax.bar(np.arange(3)+(j-.5)*.35,[rows.loc[k,'total_return_pct'] for k in ['A','B','ALL']],.35,label=symbol,color=colors[symbol])
    ax.axhline(0,color='#555',lw=.8);ax.set_xticks(np.arange(3),['A 2016–04/2024','B 05/2024–10/2026','ALL']);ax.set(title='Même référence dans chaque période',ylabel='Résultat net conditionnel (%)');ax.legend();fig.tight_layout();fig.savefig(figures/'chronological.png',dpi=160);plt.close(fig)
    for row in primary.itertuples():
        d=pd.read_csv(out/row.label/'daily.csv');t=pd.read_csv(out/row.label/'trades.csv');dates=pd.to_datetime(d.date)
        for unit,container in [('Y',annual),('M',monthly)]:
            for key,g in d.groupby(dates.dt.to_period(unit)):
                container.append(dict(symbol=row.symbol,period=row.period,bucket=str(key),return_pct=(np.prod(1+g.return_net)-1)*100,net_pnl=g.net_pnl.sum(),trades=int(g.trades.sum()),excluded=int(g.conditionally_excluded.sum())))
        for direction,g in t.groupby('direction'):
            directions.append(dict(symbol=row.symbol,period=row.period,direction=direction,trades=len(g),net_pnl=g.net_pnl.sum(),commission=g.commission.sum(),borrow=g.borrow_fee.sum(),friction=g.friction_cost.sum()))
        losses=longest=0
        for value in t.net_pnl:
            losses=losses+1 if value<0 else 0;longest=max(longest,losses)
        ablations.append(dict(symbol=row.symbol,period=row.period,return_without_top3_pct=row.return_without_top3_days_pct,
            return_without_2020_pct=(np.prod(1+d.loc[dates.dt.year!=2020,'return_net'])-1)*100,longest_loss_streak=longest,
            method='Set selected original daily returns to zero, not a portfolio re-sized without selected trades.'))
        reasons=d.eligibility.value_counts().to_dict();quality.append(dict(symbol=row.symbol,period=row.period,**reasons))
    for name,rows in [('annual',annual),('monthly',monthly),('directions',directions),('ablations',ablations),('quality_reasons',quality)]:
        pd.DataFrame(rows).to_csv(out/f'{name}.csv',index=False)
    fig,ax=plt.subplots(figsize=(11,4.5));a=pd.DataFrame(annual);z=a[a.period=='ALL'].pivot(index='bucket',columns='symbol',values='return_pct')[['SPY','QQQ']]
    z.plot.bar(ax=ax,color=[colors['SPY'],colors['QQQ']]);ax.axhline(0,color='#555',lw=.8);ax.set(title='Années de la référence ; 2016/2026 partielles',ylabel='Résultat annuel conditionnel (%)',xlabel='Année');fig.tight_layout();fig.savefig(figures/'annual_returns.png',dpi=160);plt.close(fig)
    negative=all(allrows.total_return_pct<0)
    conclusion='La référence est négative sur les deux ETF après frais ; cette formalisation ne justifie pas un nouveau bot.' if negative else 'Les résultats sont exploratoires : la stabilité par période et les coûts doivent décider de la suite, sans sélectionner un gagnant après observation.'
    lines=['# RSI(2) intraday SPY / QQQ — rapport final','',conclusion,'',
        '72 exécutions fixées avant performances. Entrées 4 janvier 2016–16 octobre 2026 ; A jusqu’au30/04/2024, B du01/05/2024 au16/10/2026. B a déjà servi aux autres recherches : aucun nouvel OOS aveugle. Capital100000USD indépendant par scénario. La chauffe200séances, les absences de closes antérieurs et les journées incomplètes limitent les observations réellement négociées.','',
        '## Hypothèse et règles','',
        'Adaptation exploratoire intraday du retour à la moyenne RSI(2), distincte des stratégies journalières décrites par Connors. RSI Wilder2 sur closes5min RTH, réinitialisé chaque séance ; LONG quand régime haussier et RSI<5, première occurrence après chauffe ATR14. Régime = close minute RTH précédent contre moyenne des200closes antérieurs, corrigés par dividendes cash cumulés connus. Les200séances sont consécutives : un close manquant ne se remplace pas par une séance plus ancienne. Ce proxy cash-additif n’est pas un rendement total composé.','',
        'Entrée au prochain open1min, entre10:00 et15:00 New York ; chauffe ATR14 => première entrée possible10:40 sur séance normale. Une transaction maximum par séance. Stop2ATR14 figé au signal, arrondi adverse au centime. Sortie sur close5m RSI>70 à l’open suivant, stop prioritaire, liquidation à l’open de la dernière minute RTH15:59/12:59. Pas de TP, pyramide, break-even ou maintien overnight. Quantité décidée au signal : risque cible1%, plafond1x, unités entières ; les gaps peuvent dépasser ces plafonds réalisés. [Protocole exact](../../PROTOCOL_EXECUTION.md).','',
        '## Résultats principaux après frais','',
        table(['ETF','Période','Trades','Net %','CAGR %','PF','Win rate %','DD marks %','Sans top3 jours %'],[[r.symbol,r.period,r.trades,f'{r.total_return_pct:.2f}',f'{r.cagr_pct:.2f}',f'{r.profit_factor:.3f}',f'{r.win_rate_pct:.2f}',f'{r.observed_close_drawdown_pct:.2f}',f'{r.return_without_top3_days_pct:.2f}'] for r in primary.itertuples()]),'',
        'Le CAGR utilise la période nominale, y compris la chauffe/séances sans ordre. Les drawdowns « marks » utilisent les closes1min entièrement tenus et les événements de fill, pas chaque tick. Les courbes sont conditionnelles à la résolution des données ; elles ne prouvent pas une exécution continue durant les absences. Cash témoin0% avant inflation. Aucun dépassement d’un placement passif n’est revendiqué.','',
        '## Coûts et exposition','',
        'Mêmes hypothèses que les études ETF précédentes : commission0,0035USD/action/côté, minimum0,35/côté ; friction adverse0,01USD/action/côté ; empruntSHORT1%annuel/360, minimum un jour. Aucun double comptage : friction incorporée aux prix, puis commissions et emprunt soustraits une fois. Ces hypothèses ne sont pas un tarif garanti d’Alpaca. Frais réglementaires variables, file d’attente et bid/ask non reconstitués.','',
        table(['ETF','Période','Mouvement prix USD','Friction USD','Commissions USD','Emprunt USD','Net USD','Part du temps RTH (borne haute) %'],[[r.symbol,r.period,*[f'{getattr(r,k):.2f}' for k in ['price_move_pnl','friction_cost','commission','borrow_fee','net_pnl','regular_time_exposure_upper_pct']]] for r in primary.itertuples()]),'',
        'Les variantes SHORT utilisent l’emprunt minimum d’une journée même sans overnight. Le risque de1% est un plafond de prix au signal, pas une garantie de perte nette ; le plafond1x limite généralement la taille avant ce risque cible. Les mesures de levier et de risque effectifs à l’entrée sont exportées, avec leurs éventuels dépassements par gap.','',
        '## Configurations et coûts fixés avant résultats','',
        table(['Variante ALL : trades / net % / PF','SPY','QQQ'],[[v]+[f'{int(r.trades)} / {r.total_return_pct:.2f}% / {r.profit_factor:.3f}' for s in ['SPY','QQQ'] for r in [c[(c.symbol==s)&(c.period=='ALL')&(c.variant==v)].iloc[0]]] for v in c.variant.drop_duplicates()]),'',
        'Les72comptes sont recouvrants, pas72preuves indépendantes. BOTH ajoute les SHORT en régime baissier (RSI>95 puis sortie<30). Le filtre de tendance OFF, le seuil10, les stops1/3ATR et la sortie80 sont des sensibilités fixées à l’avance ; aucune n’est retenue après coup comme nouveau résultat principal. Toutes les périodes et coûts figurent dans [comparison_all.csv](comparison_all.csv).','',
        'La variante entrée RSI<10 est positive en B (+2,47% SPY, +3,55% QQQ), mais reste négative en A et sur ALL pour les deux ETF. Elle ne remplace pas la référence et ne justifie pas une sélection après observation.','',
        '## Couverture et causalité','',
        'Sources : archives Alpaca SIP brutes déjà acquises, préparations et corporate actions vérifiées par SHA avant exécution. 2714séances calendaires dans la préparation, dont une première date2015-12-31 sans données suffisantes ; période évaluée2713séances2016–2026. SPY2705séances complètes dans la préparation, QQQ2707. [Profil et empreintes](DATA_SOURCE_PROFILE.json). Aucune clé ni nouvelle requête API nécessaire.','',
        'Principal complete_days : exclusion après coup des séances courantes incomplètes pouvant générer une entrée. Ce filtre est connu après la séance et peut favoriser les résultats. resolved_prefix retire ce filtre futur : une lacune avant le signal rend la décision inconnue, une lacune active laisse une intention non résolue et les coûts d’entrée connus dans unresolved.csv ; le trade entier est omis du compte conditionnel. Le zéro de chaînage d’un jour exclu n’est pas du cash observé.','',
        table(['ETF','Période','Exclues principal','Trades principal','Net principal %','Trades prefix','Non résolues prefix','Net prefix %'],[[r.symbol,r.period,int(r.data_excluded_sessions),r.trades,f'{r.total_return_pct:.2f}',int(p.trades),int(p.unresolved_sessions),f'{p.total_return_pct:.2f}'] for r in primary.itertuples() for p in [c[(c.symbol==r.symbol)&(c.period==r.period)&(c.variant=='resolved_prefix')].iloc[0]]]),'',
        'Une absence de régime éligible ou une chauffe connue avant séance implique aucun ordre selon les règles. Une donnée de close antérieur manquante bloque le régime jusqu’à sa sortie des200séances : ce comportement est causal mais restreint la période réellement exploitable. Il ne certifie pas que l’historique est complet. Les raisons détaillées par date sont dans daily.csv et les features. L’égalité éventuelle de résultats prefix et principal ne résout pas les opportunités manquantes.','',
        '## Incertitude et concentration','',
        'Les fichiers *_uncertainty.json contiennent les intervalles descriptifs par blocs circulaires5/20séances et clusters annuels,3000tirages seed20261024. Ils utilisent les retours conditionnels existants et ne corrigent ni les journées inconnues, ni les recherches multiples, ni la réutilisation de B. Pas de seuil p choisi après coup.','',
        table(['ETF','Période','Sans top3 jours %','Sans2020 %','Série pertes max'],[[r['symbol'],r['period'],f"{r['return_without_top3_pct']:.2f}",f"{r['return_without_2020_pct']:.2f}",r['longest_loss_streak']] for r in ablations]),'',
        'Les ablations mettent à zéro les rendements journaliers sélectionnés ; ce ne sont pas des comptes recalculés sans ces trades. Années/mois et directions sont exportés à côté du rapport. Un haut win rate peut coexister avec des gains faibles et des stops plus grands.','',
        '## Figures','',*['!['+title+'](figures/'+name+'.png)\n' for title,name in [('Capital et drawdown','equity_drawdown'),('Deux périodes','chronological'),('Coûts','cost_sensitivity'),('Années','annual_returns')]],
        '## Validation et limites','',
        '[Tests, revue et audit indépendant](../../VALIDATION.md). Snapshots de code et dépendances figés avant la boucle dans PRE_EXECUTION_PROTOCOL.json. Les tests contrôlés ne sont pas des performances de marché. Les vérifications indépendantes relisent prix/signaux/comptes sans utiliser les fonctions du moteur pour confirmer leur arithmétique ; leur portée exacte figure dans les preuves d’audit.','',
        'Hypothèse encore non vérifiée en direct : rebond d’un excès intraday mesuré par RSI. Quotes de trades consolidées, résolution1min, gaps inconnus et coûts fixes peuvent différer des fills d’un courtier. Les données excluent plusieurs minutes de crise2020 et la complétude du retour des corporate actions n’est pas garantie. SPY/QQQ partagent leur exposition actions américaines, donc les deux résultats ne sont pas indépendants.','',
        '## Décision','',conclusion+' Aucune variante choisie après résultats, aucune modification de Noise Area/ORB, aucun ordre envoyé.','',
        'Sources de l’idée : [Connors, sorties dynamiques RSI](https://tradingmarkets.com/recent/dynamic_exits_how_to_properly_exit_a_trade-641067), [TradingMarkets, replis et régime200jours](https://tradingmarkets.com/recent/buying_weakness_and_selling_strength-684961), [TradeStation, formule Wilder](https://help.tradestation.com/10_00/eng/tsdevhelp/elword/function/rsi_function_.htm). Ces textes motivent l’hypothèse ; leurs résultats ne sont pas importés dans nos comptes.']
    (out/'RAPPORT_FINAL.md').write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
    print('French report, 4 figures and descriptive tables generated.')


if __name__=='__main__':main()
