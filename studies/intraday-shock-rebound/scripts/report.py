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
    axes[0].axhline(100000,color='#555',lw=.8);axes[0].set(title='Choc baissier puis rebond : référence après frais',ylabel='Capital conditionnel USD');axes[1].set(ylabel='Drawdown quotidien %',xlabel='2016–16/10/2026 ; lacunes de couverture non interpolées')
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
        labels=['z1.5','reference','z2.5','no_z_filter'];z=c[(c.symbol==s)&(c.period=='ALL')].set_index('variant').loc[labels]
        ax.bar(np.arange(4),z.total_return_pct,color=colors[s]);ax.set_xticks(np.arange(4),['1,5sigma','2sigma','2,5sigma','Sans seuil z']);ax.axhline(0,color='#555',lw=.8);ax.set(title=s,ylabel='Net ALL conditionnel %')
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
    text=['# Rebond après choc intraday — rapport SPY / QQQ','',decision,'',
        'Capital100000USD indépendant par scénario. ALL4janvier2016–16octobre2026 ; A jusqu’au30avril2024 ; B1mai2024–16octobre2026. B et ces ETF déjà explorés : aucun nouveau OOS aveugle.','',
        '## Recherche élargie et limites des sources','',
        'Publications arXiv/articles académiques, recherches quantitatives, forums et GitHub comparés. Retenir une adaptation de réversion après choc, sans reprendre de rendement tiers. Les travaux SPY NBBO/event-time ou sur actions ne démontrent pas la rentabilité de notre règle clock-time sur deux ETF. Paires/lead-lag : stabilité/vitesse/coûts ; améliorations ORB à règles payantes : pas de fausse réplication ; IBS overnight : hors day trading. [Recherche détaillée](../../RESEARCH.md).','',
        '## Règles figées avant PnL','',
        'LONG seulement. Tous les5minutes dès09:59, rendement log(close/open) des30minutes écoulées. Moyenne et sigma ddof1 sur20séances précédentes à même heure. Ignorer uniquement une fermeture structurelle, jamais une donnée manquante. Les30minutes OHLC de chaque rendement doivent être cohérentes. Moins de20séances=>chauffe connue ; historique nécessaire troué=>inconnu ; sigma≤1e-12=>pas de choc exploitable. Aucun paramètre estimé avec le futur.','',
        'Rendement négatif et z≤−2 (tolérance1e-10), puis confirmation5minutes immédiatement suivante, close>open et>closeChoc. Premier couple admissible seulement ; une fenêtre inconnue antérieure ne devient pas arbitrairement un non-signal. Confirmation lue seulement après un choc admissible.','',
        'Entrée open minute suivante, dès10:05, au plus tard60minutes avant clôture incluse (15:00/12:00). Stop min(choc,confirmation)−0,01USD arrondi vers le bas. Quantité au close du signal : risque cible1%, plafond1x, frais exclus. Gap futur peut dépasser ces plafonds ; aucune annulation rétroactive. TP2R depuis open d’entrée observé, arrondi vers l’entrée. Stop prioritaire si SL/TP ensemble ; gap stop au mauvais open, gap TP sans amélioration. EOD dernier open15:59/12:59 avant sa mèche. Aucun overnight, trailing, RSI, VWAP ou EMA. [Protocole complet](../../PROTOCOL_EXECUTION.md).','',
        '## Référence après les mêmes frais','',
        table(['ETF','Période','Trades','Net cumulé %','CAGR %','PF','WR %','DD marks %','Sans top3 %'],[[r.symbol,r.period,int(r.trades),f'{r.total_return_pct:.2f}',f'{r.cagr_pct:.2f}',f'{r.profit_factor:.3f}',f'{r.win_rate_pct:.2f}',f'{r.observed_close_drawdown_pct:.2f}',f'{r.return_without_top3_days_pct:.2f}'] for r in principal.itertuples()]),'',
        'Comptes conditionnels aux données résolues ; CAGR sur période nominale chauffe comprise. DD aux frais d’entrée, closes1minute entièrement détenus et sortie nette, sans borne de tous les ticks. DD quotidien graphique moins fin. ETF corrélés, pas deux preuves indépendantes ; aucun avantage sur le passif à exposition comparable revendiqué, cash0%.','',
        '## Frais et attribution','',
        'Commission0,0035USD/action/côté minimum0,35 ; friction adverse0,01USD/action/côté ; empruntSHORT1%annuel/360 minimum1jour seulement miroir SHORT. Friction comprise dans les fills puis attribuée une seule fois. Modèle commun, pas tarif broker garanti ; spreads lors des chocs et frais variables non observés.','',
        table(['ETF','Période','Prix USD','Friction USD','Commission USD','Emprunt USD','Net USD','Exposition RTH bornehaute %'],[[r.symbol,r.period,*[f'{getattr(r,k):.2f}' for k in ['price_move_pnl','friction_cost','commission','borrow_fee','net_pnl','regular_time_exposure_upper_pct']]] for r in principal.itertuples()]),'',
        '## Sensibilités fixées et contrôles','',
        table(['Variante ALL : trades/net%/PF','SPY','QQQ'],[[v]+[f'{int(r.trades)} / {r.total_return_pct:.2f} / {r.profit_factor:.3f}' for s in ['SPY','QQQ'] for r in [c[(c.symbol==s)&(c.period=='ALL')&(c.variant==v)].iloc[0]]] for v in c.variant.drop_duplicates()]),'',
        '12variantes ×2ETF ×3périodes=72comptes recouvrants. Coûts0,02/0,03/0,05, seuil1,5/2,5sigma, TP1R/3R, sans confirmation, sans filtre z, miroir SHORT et prefix. Sans z conserve r<0, confirmation et disponibilité de baseline ; ce n’est pas un contrôle causal à exposition identique. Sans confirmation entre dès10:00 avec stop30minutes seul. SHORT miroir : r>0,z≥+2, confirmation baissière et stop high+0,01. Comptes composés séparément. [Tous les scénarios](comparison_all.csv), aucune variante promue après PnL.','',
        '## Critères de présélection déclarés','',
        table(['Critère avant PnL','Passe'],[[k,'oui' if v else 'non'] for k,v in criteria.items()]),'',
        'Exiger ≥100trades ALL/ETF, six références positives, ALL sans top3 positif, A à friction doublée positive et bornes basses IC95 blocs20 ALL>0 sur les deux ETF. Un passage resterait une présélection historique, pas preuve prospective ni activation automatique.','',
        '## Couverture et provenance','',
        'Mêmes archives SIP/préparations vérifiées SHA, calendrier NYSE et rapprochement corporate actions.2714séances préparées dont padding2015-12-31,2713évaluées. SPY2705/QQQ2707complètes dans le cache total. Trous, notamment en2020 ; pas de deuxième flux ni interpolation. [Profil source](DATA_SOURCE_PROFILE.json).','',
        'Rendements entièrement intraday, invariants à l’échelle de chaque séance : aucun raccord entre ancien prix non ajusté et niveau courant, aucun dividende crédité au compte flat overnight. Les20séances passées sont choisies par horaire ouvert, sans filtre futur de qualité de journée entière. Une lacune historique peut donc empêcher des décisions durant20séances suivantes à cette heure.','',
        'complete_days applique après coup la qualité OHLCV courante après premier signal, biais potentiel. Prefix la retire mais reste conditionnel : fenêtre/historique/confirmation nécessaire inconnu avant signal=>journée inconnue ; trou actif=>trade entier non résolu, frais d’entrée connus exportés. Zéro de chaînage n’est pas cash observé. Chauffe initiale/sigma nul sont connus sans ordre. Données inutiles après signal ou sortie ne l’annulent pas.','',
        table(['ETF','Période','Exclues principal','Trades principal','Net principal %','Trades prefix','Non résolues','Net prefix %'],[[r.symbol,r.period,int(r.data_excluded_sessions),int(r.trades),f'{r.total_return_pct:.2f}',int(p.trades),int(p.unresolved_sessions),f'{p.total_return_pct:.2f}'] for r in principal.itertuples() for p in [c[(c.symbol==r.symbol)&(c.period==r.period)&(c.variant=='resolved_prefix')].iloc[0]]]),'',
        '## Incertitude et concentration','',
        'Bootstrap descriptif3000tirages seed20261026, blocs circulaires5/20séances et clusters annuels. Exclusions au zéro de chaînage, données non reconstruites, peu de clusters et essais multiples non corrigés.','',
        table(['ETF','Période','IC95 moyenne quotidienne %, blocs5','Blocs20','IC95 bps/trade, années'],intervals),'',
        table(['ETF','Période','Sans top3 %','Sans2020 %','Pertes consécutives max'],[[r['symbol'],r['period'],f"{r['without_top3_pct']:.2f}",f"{r['without2020_pct']:.2f}",r['longest_loss_streak']] for r in concentration]),'',
        'Ablations : rendements concernés mis à zéro dans le compte original, sans nouveau sizing. Années/mois/directions, qualité, premières décisions par variante et chaque trade exportés.','',
        '## Figures','',*['!['+name+'](figures/'+file+'.png)\n' for name,file in [('Capital et drawdown','equity_drawdown'),('Coûts','cost_sensitivity'),('Seuils','rule_sensitivity'),('Années','annual_returns')]],
        '## Validation et limites','',
        '[Tests, revue et replay](../../VALIDATION.md). Code/tests/rapport/audit/dépendances gelés avant PnL. Moteur : rolling pandas décalé ; audit : deque des20séances ouvertes et NumPy, puis replay scalaire de chaque décision, fill et compte sans appeler le moteur. Même chargeur/source : pas de réplication sur un deuxième fournisseur.','',
        'Limites : adaptation clock-time de travaux NBBO/event-time/actions ; quotes/carnet absents, ticks non ordonnés dans la minute, élargissement de spread lors du choc non reconstruit, coûts fixes/shorts non garantis, couverture incomplète et choix d’hypothèse sur des marchés déjà explorés. Aucun nouveau holdout aveugle.','',decision+' Les deux bots QQQ existants restent inchangés, aucun nouveau bot ou ordre réel.']
    (out/'RAPPORT_FINAL.md').write_text('\n'.join(text)+'\n',encoding='utf-8');print('Report,4figures and descriptive tables generated.')

if __name__=='__main__':main()
