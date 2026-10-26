"""Report and standalone plots derived solely from the frozen execution exports."""
from pathlib import Path
import argparse,json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]

def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+['| '+' | '.join(map(str,row))+' |' for row in rows])

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=ROOT/'results/2026-10-26-v1');out=p.parse_args().out.resolve()
    assert json.loads((out/'RUN_COMPLETE.json').read_text())['executions']==72
    c=pd.read_csv(out/'comparison_all.csv');principal=c[c.variant=='reference'];annual=[];monthly=[];directions=[];concentration=[];coverage=[];intervals=[]
    for r in principal.itertuples():
        d=pd.read_csv(out/r.label/'daily.csv');t=pd.read_csv(out/r.label/'trades.csv');dates=pd.to_datetime(d.date)
        for unit,rows in [('Y',annual),('M',monthly)]:
            for key,g in d.groupby(dates.dt.to_period(unit)):
                rows.append(dict(symbol=r.symbol,period=r.period,bucket=str(key),return_pct=(np.prod(1+g.return_net)-1)*100,net_pnl=g.net_pnl.sum(),trades=int(g.trades.sum()),excluded=int(g.conditionally_excluded.sum())))
        for direction,g in t.groupby('direction'):
            directions.append(dict(symbol=r.symbol,period=r.period,direction=direction,trades=len(g),net_pnl=g.net_pnl.sum(),commission=g.commission.sum(),friction=g.friction_cost.sum(),borrow=g.borrow_fee.sum()))
        streak=longest=0
        for x in t.net_pnl:streak=streak+1 if x<0 else 0;longest=max(streak,longest)
        concentration.append(dict(symbol=r.symbol,period=r.period,without_top3_pct=r.return_without_top3_days_pct,without2020_pct=(np.prod(1+d.loc[dates.dt.year!=2020,'return_net'])-1)*100,longest_loss_streak=longest))
        coverage.append(dict(symbol=r.symbol,period=r.period,**d.eligibility.value_counts().to_dict()))
        u=json.loads((out/f'{r.symbol}_{r.period}_uncertainty.json').read_text())
        intervals.append([r.symbol,r.period,*[f"[{v[0]*100:.4f} ; {v[1]*100:.4f}]" for b in ['5','20'] for v in [u['blocks'][b]['conditional_daily_mean_ci95']]],str(u['annual_cluster']['mean_trade_bps_ci95'])])
    for name,rows in [('annual',annual),('monthly',monthly),('directions',directions),('concentration',concentration),('quality_reasons',coverage)]:pd.DataFrame(rows).to_csv(out/f'{name}.csv',index=False)
    plt.rcParams.update({'font.size':10,'axes.grid':True,'grid.alpha':.2,'axes.spines.top':False,'axes.spines.right':False});colors={'SPY':'#2563eb','QQQ':'#d97813'};figures=out/'figures';figures.mkdir(exist_ok=True)
    fig,axes=plt.subplots(2,1,figsize=(11,7),sharex=True)
    for r in principal[principal.period=='ALL'].itertuples():
        d=pd.read_csv(out/r.label/'daily.csv');dates=pd.to_datetime(d.date);equity=d.equity.mask(d.conditionally_excluded);dd=((d.equity/np.maximum.accumulate(np.r_[100000,d.equity])[1:]-1)*100).mask(d.conditionally_excluded)
        axes[0].plot(dates,equity,label=r.symbol,color=colors[r.symbol]);axes[1].plot(dates,dd,label=r.symbol,color=colors[r.symbol])
    axes[0].axhline(100000,color='#555',lw=.8);axes[0].set(title='Rejet des extrêmes de veille : référence après frais',ylabel='Capital conditionnel USD');axes[1].set(ylabel='Drawdown quotidien %',xlabel='2016–16/10/2026 ; lacunes de couverture non interpolées')
    for ax in axes:ax.legend()
    fig.tight_layout();fig.savefig(figures/'equity_drawdown.png',dpi=160);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(11,4.5))
    for ax,s in zip(axes,['SPY','QQQ']):
        for period in ['A','B','ALL']:
            z=c[(c.symbol==s)&(c.period==period)&c.variant.isin(['reference','cost_0.02','cost_0.03','cost_0.05'])].sort_values('slippage');ax.plot(z.slippage,z.total_return_pct,marker='o',label=period)
        ax.axhline(0,color='#555',lw=.8);ax.set(title=s,xlabel='Friction USD/action/côté',ylabel='Résultat net conditionnel %');ax.legend()
    fig.suptitle('Stress de coûts : capital recalculé pour chaque scénario');fig.tight_layout();fig.savefig(figures/'cost_sensitivity.png',dpi=160);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(11,4.5))
    for ax,s in zip(axes,['SPY','QQQ']):
        labels=['rr1','reference','rr3','signal15'];z=c[(c.symbol==s)&(c.period=='ALL')].set_index('variant').loc[labels]
        ax.bar(np.arange(4),z.total_return_pct,color=colors[s]);ax.set_xticks(np.arange(4),['1R / 5m','2R / 5m','3R / 5m','2R / 15m']);ax.axhline(0,color='#555',lw=.8);ax.set(title=s,ylabel='Net ALL conditionnel %')
    fig.suptitle('Sensibilités fixées avant performance ; aucune variante promue');fig.tight_layout();fig.savefig(figures/'rule_sensitivity.png',dpi=160);plt.close(fig)
    fig,ax=plt.subplots(figsize=(11,4.5));z=pd.DataFrame(annual);z[z.period=='ALL'].pivot(index='bucket',columns='symbol',values='return_pct')[['SPY','QQQ']].plot.bar(ax=ax,color=[colors['SPY'],colors['QQQ']]);ax.axhline(0,color='#555',lw=.8);ax.set(title='Référence par année ; 2016/2026 partielles',ylabel='Net conditionnel %',xlabel='Année');fig.tight_layout();fig.savefig(figures/'annual_returns.png',dpi=160);plt.close(fig)
    good=all(principal.total_return_pct>0)
    decision='La référence reste positive sur les deux ETF et les deux périodes : piste de recherche, sans preuve prospective ni activation de bot.' if good else 'La référence ne reste pas positive sur les deux ETF et les deux périodes. Cette étude ne justifie pas un nouveau bot.'
    text=['# Rejet des extrêmes de veille — rapport final SPY / QQQ','',decision,'',
        'Capital initial100000USD indépendant par scénario. ALL4janvier2016–16octobre2026 ; A jusqu’au30avril2024 ; B du1mai2024 au16octobre2026. Ces marchés et B ont déjà été étudiés : ce découpage chronologique ne constitue pas un nouvel échantillon aveugle.','',
        '## Hypothèse et recherche','',
        'Après une fausse cassure du plus haut/bas de la veille, le retour dans le range pourrait produire une réversion intraday. Les exemples publics sur l’or ont servi à définir une primitive mécanique, sans importer leur win rate. [Sources, lecture de code et limites](../../RESEARCH.md). Aucune affirmation sur un carnet ou des stops réellement observés.','',
        '## Règles figées','',
        'Range OHLC de la séance RTH immédiatement précédente, demi-séances incluses ; correction du dividende cash courant. Open09:30 strictement dedans. Bougie5min : dépassement d’au moins0,01USD de l’extrême, puis clôture strictement dedans. Premier signal seulement ; deux côtés dépassés sur la même bougie=>aucun trade. Entrée à l’open suivant,09:45≤entrée<14:00NY ; une entrée maximum par jour.','',
        'Stop0,01USD au-delà de la mèche du signal, arrondi au centime vers l’extérieur. Quantité entière au close du signal : risque cible1%, plafond1x du capital. Objectif2R depuis open d’entrée, arrondi au centime défavorable. Stop prioritaire si touches simultanées ; gap stop au prix défavorable, gap TP sans amélioration. Dernier open15:59 ou12:59 si encore en position. Aucun break-even/trailing/overnight. [Protocole exhaustif](../../PROTOCOL_EXECUTION.md).','',
        '## Référence après tous les frais','',table(['ETF','Période','Trades','Net %','CAGR %','PF','WR %','DD marks %','Sans top3jours %'],[[r.symbol,r.period,int(r.trades),f'{r.total_return_pct:.2f}',f'{r.cagr_pct:.2f}',f'{r.profit_factor:.3f}',f'{r.win_rate_pct:.2f}',f'{r.observed_close_drawdown_pct:.2f}',f'{r.return_without_top3_days_pct:.2f}'] for r in principal.itertuples()]),'',
        'Compte historique conditionnel aux données résolues. CAGR sur toute la période nominale, pas annualisation du seul temps investi. DD marks inclut coût d’entrée, closes1min entièrement détenus et sortie nette ; ne borne pas tous les ticks. Le graphique de DD quotidien est une mesure moins fine. Deux ETF corrélés, pas deux preuves indépendantes. Aucun avantage face au buy-and-hold à exposition comparable n’est revendiqué ; cash témoin0%, non rémunéré.','',
        '## Coûts identiques et attribution','',
        'Commission0,0035USD/action/côté, minimum0,35 ; friction adverse0,01USD/action/côté ; empruntSHORT1%annuel/360, minimum un jour. Friction déjà incorporée aux prix et soustraite une seule fois dans l’attribution. Modèle de recherche commun, pas tarif garanti du courtier. Gaps susceptibles de dépasser les plafonds de risque/levier, frais exclus du risque cible.','',
        table(['ETF','Période','Prix USD','Friction USD','Commission USD','Emprunt USD','Net USD','Exposition RTH bornehaute %'],[[r.symbol,r.period,*[f'{getattr(r,k):.2f}' for k in ['price_move_pnl','friction_cost','commission','borrow_fee','net_pnl','regular_time_exposure_upper_pct']]] for r in principal.itertuples()]),'',
        '## Toutes les sensibilités prévues','',table(['Variante ALL : trades / net% / PF','SPY','QQQ'],[[v]+[f'{int(r.trades)} / {r.total_return_pct:.2f} / {r.profit_factor:.3f}' for s in ['SPY','QQQ'] for r in [c[(c.symbol==s)&(c.period=='ALL')&(c.variant==v)].iloc[0]]] for v in c.variant.drop_duplicates()]),'',
        '12variantes ×2ETF ×3périodes=72comptes recouvrants. Coûts0,02/0,03/0,05 ; LONG/SHORT ; TP1R/3R ; signal15min ; ouverture hors range autorisée ; sans correction cash ; resolved_prefix. Aucune variante choisie gagnante après PnL. [Matrice intégrale A/B/ALL](comparison_all.csv).','',
        '## Qualité et couverture','',
        'Source Alpaca SIP1minute déjà acquise ; SHA des archives/préparations, calendrier NYSE et rapprochement des corporate actions vérifiés avant PnL.2714séances préparées dont padding2015-12-31,2713évaluées. SPY2705/QQQ2707complètes dans le cache total. Quelques minutes manquent notamment pendant la crise2020. Aucun téléchargement, interpolation ou flux de courtier alternatif ajouté à cette étude. [Profil et empreintes](DATA_SOURCE_PROFILE.json).','',
        'Les niveaux exigent les OHLC de la veille entière ; le volume n’intervient pas. Une veille inconnue n’est jamais remplacée par une plus ancienne. Le dividende cash est soustrait seulement à son ex-date, sans futur ajustement ; la table historique et son rapprochement ne garantissent pas un fichier corporate actions exhaustif.','',
        'complete_days applique après coup la qualité OHLCV du jour courant lorsque le signal produirait une entrée : ce filtre futur peut favoriser la performance. resolved_prefix retire ce filtre, mais reste conditionnel : lacune nécessaire avant signal=>inconnu ; lacune active=>trade entier non résolu, frais d’entrée connus exportés. Le zéro de chaînage d’une exclusion n’est pas un rendement de cash observé.','',
        table(['ETF','Période','Exclues principal','Trades principal','Net principal %','Trades prefix','Non résolues','Net prefix %'],[[r.symbol,r.period,int(r.data_excluded_sessions),int(r.trades),f'{r.total_return_pct:.2f}',int(p.trades),int(p.unresolved_sessions),f'{p.total_return_pct:.2f}'] for r in principal.itertuples() for p in [c[(c.symbol==r.symbol)&(c.period==r.period)&(c.variant=='resolved_prefix')].iloc[0]]]),'',
        '## Incertitude et concentration','',
        'Bootstrap descriptif3000tirages, seed20261026 : blocs circulaires5/20séances pour la moyenne quotidienne et clusters annuels pour les bps/trade. Comptes conditionnels, exclusions au zéro comptable, peu de clusters et aucune correction des essais multiples. Ces intervalles ne prouvent pas une performance future.','',
        table(['ETF','Période','IC95 moyenne quotidienne %, blocs5','Blocs20','IC95 bps/trade, clusters annuels'],intervals),'',
        table(['ETF','Période','Sans top3 %','Sans2020 %','Pertes consécutives max'],[[r['symbol'],r['period'],f"{r['without_top3_pct']:.2f}",f"{r['without2020_pct']:.2f}",r['longest_loss_streak']] for r in concentration]),'',
        'Ablations : rendements sélectionnés mis à zéro dans le compte original, sans nouveau redimensionnement. Exports par année/mois/direction, raisons de non-entrée, niveaux/features, données manquantes et transactions accessibles dans ce dossier.','',
        '## Figures','',*['!['+name+'](figures/'+file+'.png)\n' for name,file in [('Capital et drawdown','equity_drawdown'),('Coûts','cost_sensitivity'),('Règles','rule_sensitivity'),('Années','annual_returns')]],
        '## Vérifications et décision','',
        '[Tests, revue et audit indépendant](../../VALIDATION.md). Protocole, code et dépendances figés avant PnL. Replay scalaire séparé des signaux, tailles, fills, coûts, comptes et drawdowns sur les mêmes sources : pas une seconde source de marché. Empreintes liées à cette exécution et livraison scellée.','',
        'Limites : trade consolidé plutôt que bid/ask/carnet, ordre des ticks inconnu, coûts fixes, shorts non garantis, couverture de crise incomplète, choix de famille et sensibilités sur des données déjà explorées. Les seuils de centime représentent notre formalisation, pas une propriété universelle du marché.','',decision+' Les deux bots QQQ existants restent en simulation ; aucun nouveau bot ni ordre réel.']
    (out/'RAPPORT_FINAL.md').write_text('\n'.join(text)+'\n',encoding='utf-8');print('Report, 4 standalone figures and descriptive tables generated.')

if __name__=='__main__':main()
