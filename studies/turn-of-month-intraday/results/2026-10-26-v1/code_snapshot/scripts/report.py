"""Report and standalone plots derived solely from the frozen execution exports."""
from pathlib import Path
import argparse,json,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tom.statistics import monthly_contrast
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
    contrasts=[]
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
        control=pd.read_csv(out/f'{r.symbol}_{r.period}_all_days/trades.csv')
        contrast=monthly_contrast(control);contrasts.append(dict(symbol=r.symbol,period=r.period,**contrast))
        (out/f'{r.symbol}_{r.period}_calendar_contrast.json').write_text(json.dumps(contrast,indent=2)+'\n',encoding='utf-8')
        pd.DataFrame(contrast['monthly_rows']).to_csv(out/f'{r.symbol}_{r.period}_calendar_months.csv',index=False)
        u=json.loads((out/f'{r.symbol}_{r.period}_uncertainty.json').read_text())
        intervals.append([r.symbol,r.period,*[f"[{v[0]*100:.4f} ; {v[1]*100:.4f}]" for b in ['5','20'] for v in [u['blocks'][b]['conditional_daily_mean_ci95']]],str(u['annual_cluster']['mean_trade_bps_ci95'])])
    for name,rows in [('annual',annual),('monthly',monthly),('directions',directions),('concentration',concentration),('quality_reasons',coverage)]:pd.DataFrame(rows).to_csv(out/f'{name}.csv',index=False)
    plt.rcParams.update({'font.size':10,'axes.grid':True,'grid.alpha':.2,'axes.spines.top':False,'axes.spines.right':False});colors={'SPY':'#2563eb','QQQ':'#d97813'};figures=out/'figures';figures.mkdir(exist_ok=True)
    fig,axes=plt.subplots(2,1,figsize=(11,7),sharex=True)
    for r in principal[principal.period=='ALL'].itertuples():
        d=pd.read_csv(out/r.label/'daily.csv');dates=pd.to_datetime(d.date);equity=d.equity.mask(d.conditionally_excluded);dd=((d.equity/np.maximum.accumulate(np.r_[100000,d.equity])[1:]-1)*100).mask(d.conditionally_excluded)
        axes[0].plot(dates,equity,label=r.symbol,color=colors[r.symbol]);axes[1].plot(dates,dd,label=r.symbol,color=colors[r.symbol])
    axes[0].axhline(100000,color='#555',lw=.8);axes[0].set(title='Calendrier fin/début de mois : référence après frais',ylabel='Capital conditionnel USD');axes[1].set(ylabel='Drawdown quotidien %',xlabel='2016–16/10/2026 ; lacunes de couverture non interpolées')
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
        labels=['first1','last1','reference','first5_last1'];z=c[(c.symbol==s)&(c.period=='ALL')].set_index('variant').loc[labels]
        ax.bar(np.arange(4),z.total_return_pct,color=colors[s]);ax.set_xticks(np.arange(4),['Premier','Dernier','Dernier +3','Dernier +5']);ax.axhline(0,color='#555',lw=.8);ax.set(title=s,ylabel='Net ALL conditionnel %')
    fig.suptitle('Sensibilités fixées avant performance ; aucune variante promue');fig.tight_layout();fig.savefig(figures/'rule_sensitivity.png',dpi=160);plt.close(fig)
    fig,ax=plt.subplots(figsize=(11,4.5));z=pd.DataFrame(annual);z[z.period=='ALL'].pivot(index='bucket',columns='symbol',values='return_pct')[['SPY','QQQ']].plot.bar(ax=ax,color=[colors['SPY'],colors['QQQ']]);ax.axhline(0,color='#555',lw=.8);ax.set(title='Référence par année ; 2026 arrêtée au16octobre',ylabel='Net conditionnel %',xlabel='Année');fig.tight_layout();fig.savefig(figures/'annual_returns.png',dpi=160);plt.close(fig)
    good=all(principal.total_return_pct>0) and all(x['ci95_bps'] is not None and x['ci95_bps'][0]>0 for x in contrasts if x['period']=='ALL')
    decision='Les critères historiques prédéfinis passent, mais ne prouvent pas une rentabilité prospective et n’activent aucun bot.' if good else 'Les critères historiques prédéfinis ne passent pas. Cette formalisation ne justifie pas un nouveau bot.'
    text=['# Fin/début de mois en intraday — rapport SPY / QQQ','',decision,'',
        'Capital initial100000USD indépendant par scénario. ALL4janvier2016–16octobre2026 ; A jusqu’au30avril2024 ; B1mai2024–16octobre2026. B et ces ETF ont déjà été étudiés : aucun nouvel échantillon aveugle.','',
        '## Hypothèse et sources','',
        'Le calendrier peut concentrer certains rendements autour du changement de mois. Forums, GitHub et exemple QuantConnect décrivent des fenêtres et maintiens différents ; certains comprennent plusieurs nuits. [Recherche et limites des sources](../../RESEARCH.md). Notre question porte sur les seules heures régulières ; aucun gain overnight ou rendement tiers n’est importé. Aucune cause de flux institutionnel n’est démontrée par ce test.','',
        '## Règles fixées avant résultats','',
        'LONG dernier jour de bourse du mois et3premières séances. Calendrier XNYS sur mois complets, au-delà des coupures de données/A/B ; demi-séances incluses. Le dernier enregistrement source n’est jamais considéré artificiellement comme fin de mois. Calendrier historique reconstruit, pas archive point-in-time des fermetures annoncées.','',
        'Sizing au close09:34 (slot4), entrée open09:35 (slot5). Stop closeSignal×0,99 arrondi centime vers le bas. Quantité entière : risque cible1%, plafond1x, décidée avant open futur. Aucun TP. Gap stop au mauvais open, sinon low≤stop. Sortie dernier open15:59/12:59 avant sa mèche. Une entrée/jour, aucun short, trailing, indicateur ou overnight. no_stop conserve la quantité issue du stop virtuel et supprime seulement son exécution : la distance1% ne borne alors plus les pertes. [Protocole complet](../../PROTOCOL_EXECUTION.md).','',
        '## Référence après les mêmes frais','',table(['ETF','Période','Trades','Net cumulé %','CAGR %','PF','WR %','DD marks %','Sans top3jours %'],[[r.symbol,r.period,int(r.trades),f'{r.total_return_pct:.2f}',f'{r.cagr_pct:.2f}',f'{r.profit_factor:.3f}',f'{r.win_rate_pct:.2f}',f'{r.observed_close_drawdown_pct:.2f}',f'{r.return_without_top3_days_pct:.2f}'] for r in principal.itertuples()]),'',
        'Performances conditionnelles aux données résolues, pas compte observé continu. CAGR sur toute la période nominale. DD marks aux coûts d’entrée, closes entièrement détenus et sortie nette : ne borne pas tous les ticks. Le graphique DD quotidien est moins fin. Les deux ETF sont corrélés. Cash0%, sans rémunération. Aucun avantage par rapport au passif à exposition comparable n’est revendiqué.','',
        '## Coûts et attribution','',
        'Commission0,0035USD/action/côté minimum0,35 ; friction adverse0,01USD/action/côté. Modèle SHORT1%annuel/360 minimum1jour inchangé, mais emprunt nul ici car LONG seulement. Friction déjà dans les fills, soustraite une seule fois dans l’attribution. Modèle commun de recherche, pas tarif broker garanti ; frais variables et bid/ask non reconstruits. Gaps susceptibles de dépasser les plafonds effectifs1x/1%, frais exclus du risque cible.','',
        table(['ETF','Période','Prix USD','Friction USD','Commission USD','Emprunt USD','Net USD','Exposition RTH bornehaute %'],[[r.symbol,r.period,*[f'{getattr(r,k):.2f}' for k in ['price_move_pnl','friction_cost','commission','borrow_fee','net_pnl','regular_time_exposure_upper_pct']]] for r in principal.itertuples()]),'',
        '## Contrôles : gagner ne suffit pas à prouver un effet de calendrier','',
        table(['ETF','Période','TOM trades / net% / bps par trade','Autres jours','Tous les jours'],[[r.symbol,r.period]+[f'{int(x.trades)} / {x.total_return_pct:.2f} / {x.mean_trade_bps:.3f}' for variant in ['reference','other_days','all_days'] for x in [c[(c.symbol==r.symbol)&(c.period==r.period)&(c.variant==variant)].iloc[0]]] for r in principal.itertuples()]),'',
        'Contrôles : même achat09:35, stop1%, sizing et frais ; changer seulement les séances autorisées. Chaque compte est composé séparément. Des expositions différentes empêchent de lire le seul net cumulé comme un effet causal. Les bps par trade sont rapportés au notionnel d’entrée exécuté, pas au capital total.','',
        table(['ETF','Période','Mois avec2groupes','Mois sans2groupes','Partiels/incomplets inclus','Écart moyen TOM−autres bps','IC95 par mois bps'],[[x['symbol'],x['period'],x['qualifying_months'],x['months_without_both_groups'],x['partial_or_incomplete_months'],f"{x['mean_difference_bps']:.3f}" if x['mean_difference_bps'] is not None else 'NA',str(x['ci95_bps'])] for x in contrasts]),'',
        'Diagnostic fixé : depuis le compte all_days, calculer dans chaque mois la moyenne nette des trades TOM et autres, puis moyenner leurs écarts en donnant le même poids à chaque mois. IC95 par rééchantillonnage3000fois des mois, seed20261026. Mois partiels/incomplets conservés et signalés ; exclure seulement les mois sans les deux groupes. CSV calendar_months et JSON calendar_contrast exposent chaque calcul. Intervalles descriptifs conditionnels, peu de mois en B, dépendances de régime et essais multiples non corrigés.','',
        'Critères de candidature fixés avant PnL : référence positive sur chaque ETF/période ET borne basse du contraste mensuel ALL>0 sur les deux ETF. Un passage éventuel resterait une présélection historique, sans autorisation automatique de bot ou réel.','',
        '## Toutes les sensibilités prévues','',table(['Variante ALL : trades / net% / PF','SPY','QQQ'],[[v]+[f'{int(r.trades)} / {r.total_return_pct:.2f} / {r.profit_factor:.3f}' for s in ['SPY','QQQ'] for r in [c[(c.symbol==s)&(c.period=='ALL')&(c.variant==v)].iloc[0]]] for v in c.variant.drop_duplicates()]),'',
        '12variantes ×2ETF ×3périodes=72comptes recouvrants : coûts0,02/0,03/0,05, premier1, dernier1, premiers3, premier5+dernier1, autres/tous jours, sans stop et prefix. Pas de sélection de fenêtre gagnante après PnL. [Tous les scénarios](comparison_all.csv).','',
        '## Couverture et provenance','',
        'SIP minute déjà acquis. Archives/préparations SHA, calendrier NYSE et rapprochement des corporate actions vérifiés avant PnL.2714séances préparées dont padding2015-12-31,2713évaluées ; SPY2705/QQQ2707complètes dans le cache total. Quelques minutes manquent, notamment en2020. [Profil](DATA_SOURCE_PROFILE.json), [calendrier complet figé](XNYS_CALENDAR.csv).','',
        'Signal sans historique de prix ; aucun ajustement cash nécessaire : flat overnight et achat après l’ouverture à l’ex-date. Aucun dividende inventé ni crédité. Pas de volume dans le signal, mais complete_days applique après coup la qualité OHLCV du jour pouvant générer une entrée : biais potentiel. Prefix retire ce filtre mais reste conditionnel : sizing inconnu ou trade actif non résolu omis, frais d’entrée connus exportés. Pas d’interpolation ; zéro comptable d’exclusion n’est pas cash observé. Les minutes avant09:34 et après une sortie résolue ne sont pas nécessaires en prefix.','',
        table(['ETF','Période','Exclues principal','Trades principal','Net principal %','Trades prefix','Non résolues','Net prefix %'],[[r.symbol,r.period,int(r.data_excluded_sessions),int(r.trades),f'{r.total_return_pct:.2f}',int(p.trades),int(p.unresolved_sessions),f'{p.total_return_pct:.2f}'] for r in principal.itertuples() for p in [c[(c.symbol==r.symbol)&(c.period==r.period)&(c.variant=='resolved_prefix')].iloc[0]]]),'',
        '## Incertitude, concentration et années','',
        'Bootstrap descriptif3000tirages seed20261026 : blocs circulaires5/20séances pour moyenne quotidienne et clusters annuels pour bps/trade. Exclusions au zéro de chaînage, pas couverture reconstruite ; aucun ajustement des essais multiples.','',table(['ETF','Période','IC95 moyenne quotidienne %, blocs5','Blocs20','IC95 bps/trade, années'],intervals),'',
        table(['ETF','Période','Sans top3 %','Sans2020 %','Pertes consécutives max'],[[r['symbol'],r['period'],f"{r['without_top3_pct']:.2f}",f"{r['without2020_pct']:.2f}",r['longest_loss_streak']] for r in concentration]),'',
        'Ablations : mettre à zéro les rendements sélectionnés du compte original, sans nouveau sizing. Années/mois/directions, qualité, calendrier et chaque transaction sont exportés.','',
        '## Figures','',*['!['+name+'](figures/'+file+'.png)\n' for name,file in [('Capital et drawdown','equity_drawdown'),('Coûts','cost_sensitivity'),('Fenêtres calendaires','rule_sensitivity'),('Années','annual_returns')]],
        '## Vérifications, limites et décision','',
        '[Tests/revue/audit](../../VALIDATION.md). Calendrier/code/dépendances gelés avant PnL. Replay scalaire séparé du calendrier mois par mois et de chaque ordre/compte ; il n’appelle pas le moteur. Source commune : pas deuxième flux de marché.','',
        'Limites : adaptation intraday d’une littérature souvent daily/overnight, prix de trades sans carnet, coûts fixes, données/fermetures historiques non point-in-time, couverture de crise incomplète, choix d’hypothèse et dates déjà explorées, exposition limitée et corrélation des ETF.','',decision+' Les deux bots QQQ existants restent inchangés, aucun nouveau bot ni ordre réel.']
    (out/'RAPPORT_FINAL.md').write_text('\n'.join(text)+'\n',encoding='utf-8');print('Report,4figures,calendar contrasts and descriptive tables generated.')

if __name__=='__main__':main()
