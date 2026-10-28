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
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=ROOT/'results/2026-10-28-v1');out=p.parse_args().out.resolve()
    assert json.loads((out/'RUN_COMPLETE.json').read_text(encoding='utf-8'))['executions']==72
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
        u=json.loads((out/f'{r.symbol}_{r.period}_uncertainty.json').read_text(encoding='utf-8'))
        intervals.append([r.symbol,r.period,*[f"[{v[0]*100:.4f} ; {v[1]*100:.4f}]" for b in ['5','20'] for v in [u['blocks'][b]['conditional_daily_mean_ci95']]],str(u['annual_cluster']['mean_trade_bps_ci95'])])
    for name,rows in [('annual',annual),('monthly',monthly),('directions',directions),('concentration',concentration),('quality_reasons',coverage)]:pd.DataFrame(rows).to_csv(out/f'{name}.csv',index=False)
    plt.rcParams.update({'font.size':10,'axes.grid':True,'grid.alpha':.2,'axes.spines.top':False,'axes.spines.right':False});colors={'SPY':'#2563eb','QQQ':'#d97813'};figures=out/'figures';figures.mkdir(exist_ok=True)
    fig,axes=plt.subplots(2,1,figsize=(11,7),sharex=True)
    for r in principal[principal.period=='ALL'].itertuples():
        d=pd.read_csv(out/r.label/'daily.csv');dates=pd.to_datetime(d.date);equity=d.equity.mask(d.conditionally_excluded);dd=((d.equity/np.maximum.accumulate(np.r_[100000,d.equity])[1:]-1)*100).mask(d.conditionally_excluded)
        axes[0].plot(dates,equity,label=r.symbol,color=colors[r.symbol]);axes[1].plot(dates,dd,label=r.symbol,color=colors[r.symbol])
    axes[0].axhline(100000,color='#555',lw=.8);axes[0].set(title='Opening range puis premier retest : référence après frais',ylabel='Capital conditionnel USD');axes[1].set(ylabel='Drawdown quotidien %',xlabel='2016–16/10/2026 ; lacunes de couverture non interpolées')
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
        labels=['wait3','reference','wait12','no_retest'];z=c[(c.symbol==s)&(c.period=='ALL')].set_index('variant').loc[labels]
        ax.bar(np.arange(4),z.total_return_pct,color=colors[s]);ax.set_xticks(np.arange(4),['Attente 3','Attente 6','Attente 12','Sans retest']);ax.axhline(0,color='#555',lw=.8);ax.set(title=s,ylabel='Net ALL conditionnel %')
    fig.suptitle('Sensibilités fixées avant performance ; aucune variante promue');fig.tight_layout();fig.savefig(figures/'rule_sensitivity.png',dpi=160);plt.close(fig)
    fig,ax=plt.subplots(figsize=(11,4.5));z=pd.DataFrame(annual);z[z.period=='ALL'].pivot(index='bucket',columns='symbol',values='return_pct')[['SPY','QQQ']].plot.bar(ax=ax,color=[colors['SPY'],colors['QQQ']]);ax.axhline(0,color='#555',lw=.8);ax.set(title='Référence par année ; 2026 arrêtée au16octobre',ylabel='Net conditionnel %',xlabel='Année');fig.tight_layout();fig.savefig(figures/'annual_returns.png',dpi=160);plt.close(fig)
    allrows=principal[principal.period=='ALL']
    criteria=dict(min100trades_ALL=bool((allrows.trades>=100).all()),six_references_positive=bool((principal.total_return_pct>0).all()),
        sans_top3_ALL_positive=bool((allrows.return_without_top3_days_pct>0).all()),
        doubled_friction_A_positive=bool((c[(c.period=='A')&(c.variant=='cost_0.02')].total_return_pct>0).all()),
        block20_ALL_lower_positive=all(json.loads((out/f'{s}_ALL_uncertainty.json').read_text(encoding='utf-8'))['blocks']['20']['conditional_daily_mean_ci95'][0]>0 for s in ['SPY','QQQ']))
    good=all(criteria.values())
    (out/'CANDIDACY.json').write_text(json.dumps(dict(criteria=criteria,passed=good),indent=2)+'\n',encoding='utf-8')
    decision='Les critères historiques prédéfinis passent : présélection à vérifier prospectivement, aucune activation de bot.' if good else 'Les critères historiques prédéfinis ne passent pas. Cette formalisation ne justifie pas un nouveau bot.'
    text=['# Opening range puis premier retest confirmé — SPY / QQQ','',decision,'',
        'Capital100000USD indépendant par scénario. ALL4janvier2016–16octobre2026 ; A jusqu’au30avril2024 ; B1mai2024–16octobre2026. B et ces ETF déjà explorés : aucun nouveau OOS aveugle.','',
        '## Recherche élargie et limites des sources','',
        'Recherche universitaire, dépôts primaires, blogs quantitatifs et forums comparés. Le travail descriptif Research-QQQ motive une hypothèse de retest, sans démonstration de rentabilité ni reproduction de ses règles. Les statistiques de continuation ou d’extrêmes ne sont pas des fills. Les filtres propriétaires non publiés ne sont pas inventés. [Sources et limites de lecture](../../RESEARCH.md).','',
        '## Règles figées avant PnL','',
        'Range RTH09:30–09:44NY. Première clôture5minutes au-dessus du haut ou sous le bas. Exclure la bougie de cassure ; attendre au plus6bougies5minutes. Sur le premier toucher seulement, exiger clôture encore extérieure au niveau et corps dans le sens de la cassure. Premier toucher raté : fin de journée, sans chercher ensuite une réussite. Tolérance arithmétique1e−10USD, pas une tolérance économique.','',
        'Entrée open minute suivante, dès09:55 et au plus tard11:30 incluse sur séances normales et demi-séances. Stop sous le low du seul retest moins0,01USD LONG, inverse SHORT, centime vers extérieur. Quantité au close du signal : risque cible1%, plafond1x, frais exclus. Gap futur peut dépasser ces plafonds ; aucune annulation rétroactive. TP2R depuis open d’entrée observé, arrondi vers entrée. Stop prioritaire si SL/TP ensemble ; gap stop au mauvais open, gap TP sans amélioration. EOD dernier open15:59/12:59 avant sa mèche. Aucun overnight ou gestion intermédiaire. [Protocole complet](../../PROTOCOL_EXECUTION.md).','',
        '## Référence après les mêmes frais','',
        table(['ETF','Période','Trades','Net cumulé %','CAGR %','PF','WR %','DD marks %','Sans top3 %'],[[r.symbol,r.period,int(r.trades),f'{r.total_return_pct:.2f}',f'{r.cagr_pct:.2f}',f'{r.profit_factor:.3f}',f'{r.win_rate_pct:.2f}',f'{r.observed_close_drawdown_pct:.2f}',f'{r.return_without_top3_days_pct:.2f}'] for r in principal.itertuples()]),'',
        'Comptes conditionnels aux données résolues ; CAGR sur période nominale. DD aux frais d’entrée, closes1minute entièrement détenus et sortie nette, sans borne de tous les ticks. DD quotidien graphique moins fin. ETF corrélés, pas deux preuves indépendantes ; aucun avantage sur le passif à exposition comparable revendiqué, cash0%.','',
        '## Frais et attribution','',
        'Commission0,0035USD/action/côté minimum0,35 ; friction adverse0,01USD/action/côté ; empruntSHORT1%annuel/360 minimum1jour pour les ventes à découvert. Friction comprise dans les fills puis attribuée une seule fois. Modèle commun, pas tarif broker garanti ; spreads lors des mouvements rapides et frais variables non observés.','',
        table(['ETF','Période','Prix USD','Friction USD','Commission USD','Emprunt USD','Net USD','Exposition RTH bornehaute %'],[[r.symbol,r.period,*[f'{getattr(r,k):.2f}' for k in ['price_move_pnl','friction_cost','commission','borrow_fee','net_pnl','regular_time_exposure_upper_pct']]] for r in principal.itertuples()]),'',
        '## Sensibilités fixées et contrôles','',
        table(['Variante ALL : trades/net%/PF','SPY','QQQ'],[[v]+[f'{int(r.trades)} / {r.total_return_pct:.2f} / {r.profit_factor:.3f}' for s in ['SPY','QQQ'] for r in [c[(c.symbol==s)&(c.period=='ALL')&(c.variant==v)].iloc[0]]] for v in c.variant.drop_duplicates()]),'',
        '12variantes ×2ETF ×3périodes=72comptes recouvrants. Coûts0,02/0,03/0,05, TP1R/3R, attente3/12barres, LONGseul/SHORTseul, sans retest et prefix. La direction est filtrée sur la première cassure commune, sans recherche ultérieure. Sans retest entre dès09:50 suivant la première cassure avec stop de cette bougie ; change aussi stop/sizing/exposition, pas contrôle causal pur du délai. Comptes composés séparément. [Tous les scénarios](comparison_all.csv), aucune variante promue après PnL.','',
        '## Critères de présélection déclarés','',
        table(['Critère avant PnL','Passe'],[[k,'oui' if v else 'non'] for k,v in criteria.items()]),'',
        'Exiger ≥100trades ALL/ETF, six références positives, ALL sans top3 positif, A à friction doublée positive et bornes basses IC95 blocs20 ALL>0 sur les deux ETF. Un passage resterait une présélection historique, pas preuve prospective ni activation automatique.','',
        '## Couverture et provenance','',
        'Mêmes archives SIP/préparations vérifiées SHA, calendrier NYSE et rapprochement corporate actions.2714séances préparées dont padding2015-12-31,2713évaluées. SPY2705/QQQ2707complètes dans le cache total. Trous, notamment en2020 ; pas de deuxième flux ni interpolation. [Profil source](DATA_SOURCE_PROFILE.json).','',
        'Niveaux et décisions entièrement intraday : aucun niveau de la veille ou historique de prix ajusté, aucun dividende crédité au compte flat overnight. Les minutes nécessaires au range, à la recherche de cassure et au premier retest doivent être présentes. Les données après échec/expiration/cutoff connus ne sont pas nécessaires.','',
        'complete_days applique après coup la qualité OHLCV de toute la journée après premier signal, biais potentiel. Prefix retire ce filtre mais reste conditionnel : barre nécessaire inconnue avant signal=>journée inconnue ; trou actif=>trade entier non résolu, frais d’entrée connus exportés. Zéro de chaînage n’est pas cash observé. Données inutiles après signal ou sortie ne l’annulent pas.','',
        table(['ETF','Période','Exclues principal','Trades principal','Net principal %','Trades prefix','Non résolues','Net prefix %'],[[r.symbol,r.period,int(r.data_excluded_sessions),int(r.trades),f'{r.total_return_pct:.2f}',int(p.trades),int(p.unresolved_sessions),f'{p.total_return_pct:.2f}'] for r in principal.itertuples() for p in [c[(c.symbol==r.symbol)&(c.period==r.period)&(c.variant=='resolved_prefix')].iloc[0]]]),'',
        '## Incertitude et concentration','',
        'Bootstrap descriptif3000tirages seed20261026, blocs circulaires5/20séances et clusters annuels. Exclusions au zéro de chaînage, données non reconstruites, peu de clusters et essais multiples non corrigés.','',
        table(['ETF','Période','IC95 moyenne quotidienne %, blocs5','Blocs20','IC95 bps/trade, années'],intervals),'',
        table(['ETF','Période','Sans top3 %','Sans2020 %','Pertes consécutives max'],[[r['symbol'],r['period'],f"{r['without_top3_pct']:.2f}",f"{r['without2020_pct']:.2f}",r['longest_loss_streak']] for r in concentration]),'',
        'Ablations : rendements concernés mis à zéro dans le compte original, sans nouveau sizing. Années/mois/directions, qualité, premières décisions par variante et chaque trade exportés.','',
        '## Figures','',*['!['+name+'](figures/'+file+'.png)\n' for name,file in [('Capital et drawdown','equity_drawdown'),('Coûts','cost_sensitivity'),('Délais et contrôle sans retest','rule_sensitivity'),('Années','annual_returns')]],
        '## Validation et limites','',
        '[Tests, revue et replay](../../VALIDATION.md). Code/tests/rapport/audit/dépendances gelés avant PnL. Agrégation séparée minute par minute, puis automate et replay scalaire de chaque décision, fill et compte sans appeler le moteur. Même chargeur/source : pas de réplication sur un deuxième fournisseur.','',
        'Limites : adaptation ORB/retest distincte des études descriptives, quotes/carnet absents, ticks non ordonnés dans la minute, spreads variables non reconstruits, coûts fixes/shorts non garantis, couverture incomplète et choix d’hypothèse sur des marchés déjà explorés. Aucun nouveau holdout aveugle, aucune famille de risque indépendante de l’ORB.','',decision+' Les deux bots QQQ existants restent inchangés, aucun nouveau bot ou ordre réel.']
    (out/'RAPPORT_FINAL.md').write_text('\n'.join(text)+'\n',encoding='utf-8');print('Report,4figures and descriptive tables generated.')

if __name__=='__main__':main()
