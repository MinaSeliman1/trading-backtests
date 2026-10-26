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
    axes[0].axhline(100000,color='#555',lw=.8);axes[0].set(title='Repli EMA9/20 : référence après frais',ylabel='Capital conditionnel USD');axes[1].set(ylabel='Drawdown quotidien %',xlabel='2016–16/10/2026 ; lacunes de couverture non interpolées')
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
        labels=['rr1','reference','rr3','deep_pullback'];z=c[(c.symbol==s)&(c.period=='ALL')].set_index('variant').loc[labels]
        ax.bar(np.arange(4),z.total_return_pct,color=colors[s]);ax.set_xticks(np.arange(4),['1R / 5m','2R / 5m','3R / 5m','Mèche libre']);ax.axhline(0,color='#555',lw=.8);ax.set(title=s,ylabel='Net ALL conditionnel %')
    fig.suptitle('Sensibilités fixées avant performance ; aucune variante promue');fig.tight_layout();fig.savefig(figures/'rule_sensitivity.png',dpi=160);plt.close(fig)
    fig,ax=plt.subplots(figsize=(11,4.5));z=pd.DataFrame(annual);z[z.period=='ALL'].pivot(index='bucket',columns='symbol',values='return_pct')[['SPY','QQQ']].plot.bar(ax=ax,color=[colors['SPY'],colors['QQQ']]);ax.axhline(0,color='#555',lw=.8);ax.set(title='Référence par année ; 2026 arrêtée au16octobre',ylabel='Net conditionnel %',xlabel='Année');fig.tight_layout();fig.savefig(figures/'annual_returns.png',dpi=160);plt.close(fig)
    good=all(principal.total_return_pct>0)
    decision='La référence reste positive sur les deux ETF et les deux périodes : piste historique à vérifier prospectivement, aucune activation de bot.' if good else 'La référence ne reste pas positive sur les deux ETF et les deux périodes. Cette formalisation ne justifie pas un nouveau bot.'
    text=['# Repli EMA9/20 puis reprise — rapport final SPY / QQQ','',decision,'',
        'Capital initial 100000 USD indépendant par scénario. ALL : 4 janvier 2016–16 octobre 2026 ; A : jusqu’au 30 avril 2024 ; B : 1 mai 2024–16 octobre 2026. Ces marchés et B ont déjà été étudiés : découpage chronologique exploratoire, aucun nouvel échantillon aveugle.','',
        '## Recherche et choix','',
        'Recherche sur Reddit et GitHub : replis9/20, projets QQQ multi-échelles, validation de journaux discrétionnaires et comparaison QQQ5min. Les opinions divergent et plusieurs exemples omettent les coûts ou utilisent des prix trop favorables. Nous ne reprenons aucun rendement tiers. [Sources et différences de règles](../../RESEARCH.md).','',
        'Hypothèse : une tendance peut reprendre après un repli contrôlé dans la zone des moyennes. Elle ne dépend ni des extrêmes de veille, ni d’un RSI, ni d’une bande Noise Area. Aucune affirmation sur une pression institutionnelle ou un carnet observé.','',
        '## Définition mécanique figée','',
        'Bougies5min RTH. EMA9/20 des closes, seed premier close, alpha2/(période+1), continuité entre séances et cash ex-date soustrait aux états passés. Exiger60bougies valides consécutives. Trou OHLC=>reset et nouvelle chauffe ; aucune interpolation. Les prix overnight ne sont pas inventés.','',
        'Avant la bougie LONG : EMA9>EMA20, deux pentes sur3barres positives, close précédent>EMA9. Pendant la bougie : low entre EMA20 et EMA9, close>EMA9 et>open, clôture dans les30%hauts du range. SHORT inverse. Toutes les EMA du signal sont celles de la bougie précédente, avec tolérance arithmétique1e-10USD.','',
        'Premier signal seulement, entrée open suivant entre09:45incluse et14:00exclue NY. Une entrée/jour. Stop mèche±0,01USD arrondi au centime vers l’extérieur ; quantité fixée au close du signal, risque cible1%, plafond1x. TP2R depuis open d’entrée, arrondi défavorable. Stop prioritaire si SL/TP touchés ensemble ; gap stop au mauvais open, gap TP sans amélioration. Flat au dernier open15:59/12:59 avant sa mèche. Aucun trailing, break-even, ADX ou maintien overnight. [Protocole exhaustif](../../PROTOCOL_EXECUTION.md).','',
        '## Référence après frais','',table(['ETF','Période','Trades','Net cumulé %','CAGR %','PF','WR %','DD marks %','Sans top3jours %'],[[r.symbol,r.period,int(r.trades),f'{r.total_return_pct:.2f}',f'{r.cagr_pct:.2f}',f'{r.profit_factor:.3f}',f'{r.win_rate_pct:.2f}',f'{r.observed_close_drawdown_pct:.2f}',f'{r.return_without_top3_days_pct:.2f}'] for r in principal.itertuples()]),'',
        'Compte historique conditionnel aux données résolues. CAGR sur la période nominale, chauffe comprise. DD marks aux coûts d’entrée, closes1min entièrement détenus et sortie nette : il ne borne pas tous les ticks. Le graphique de DD quotidien est une mesure moins fine. ETF corrélés, pas deux preuves indépendantes. Aucun dépassement du passif à exposition équivalente revendiqué ; cash témoin0%, non rémunéré.','',
        '## Mêmes coûts et attribution','',
        'Commission0,0035USD/action/côté minimum0,35 ; friction adverse0,01USD/action/côté ; empruntSHORT1%annuel/360 minimum un jour. Friction déjà comprise dans les fills et soustraite une seule fois dans l’attribution. Modèle commun de recherche, pas tarif broker garanti. Sizing avant open : les gaps peuvent dépasser les plafonds effectifs1x/1%, frais exclus du risque cible.','',
        table(['ETF','Période','Prix USD','Friction USD','Commission USD','Emprunt USD','Net USD','Exposition RTH bornehaute %'],[[r.symbol,r.period,*[f'{getattr(r,k):.2f}' for k in ['price_move_pnl','friction_cost','commission','borrow_fee','net_pnl','regular_time_exposure_upper_pct']]] for r in principal.itertuples()]),'',
        '## Sensibilités prévues avant performance','',table(['Variante ALL : trades / net% / PF','SPY','QQQ'],[[v]+[f'{int(r.trades)} / {r.total_return_pct:.2f} / {r.profit_factor:.3f}' for s in ['SPY','QQQ'] for r in [c[(c.symbol==s)&(c.period=='ALL')&(c.variant==v)].iloc[0]]] for v in c.variant.drop_duplicates()]),'',
        '12variantes ×2ETF ×3périodes=72comptes recouvrants. Coûts0,02/0,03/0,05, LONG/SHORT, TP1R/3R, sans pente, sans force de clôture, mèche au-delà de l’EMA lente autorisée et resolved_prefix. Tous les résultats A/B/ALL figurent dans [comparison_all.csv](comparison_all.csv). Aucune variante sélectionnée après PnL.','',
        '## Couverture et corporate actions','',
        'Archives Alpaca SIP minute déjà acquises, SHA des données/préparations, calendrier NYSE et rapprochement des corporate actions vérifiés avant PnL.2714séances préparées dont padding2015-12-31,2713évaluées. SPY2705/QQQ2707séances complètes dans le cache total. Quelques minutes manquantes, notamment en2020 ; pas de deuxième flux ni d’interpolation. [Sources et empreintes](DATA_SOURCE_PROFILE.json).','',
        'Le signal/les EMA utilisent les OHLC, pas le volume. Soustraire le cash connu au changement d’ex-date conserve toutes les pentes dans la même échelle ; aucune correction future. L’intégrité/rapprochement de la table ne prouve pas l’exhaustivité absolue des corporate actions. Une lacune peut affecter plusieurs séances à cause des60barres de rechauffe.','',
        'complete_days applique après coup la qualité OHLCV du jour courant s’il produirait une entrée : filtre futur pouvant favoriser le résultat. resolved_prefix retire ce filtre mais reste conditionnel : historique nécessaire inconnu avant signal=>séance inconnue ; lacune active=>trade entier non résolu, frais d’entrée connus exportés. Zéro de chaînage d’une exclusion ne signifie pas cash observé. La chauffe initiale est une absence connue d’ordre, pas un rendement inconnu.','',
        table(['ETF','Période','Exclues principal','Trades principal','Net principal %','Trades prefix','Non résolues','Net prefix %'],[[r.symbol,r.period,int(r.data_excluded_sessions),int(r.trades),f'{r.total_return_pct:.2f}',int(p.trades),int(p.unresolved_sessions),f'{p.total_return_pct:.2f}'] for r in principal.itertuples() for p in [c[(c.symbol==r.symbol)&(c.period==r.period)&(c.variant=='resolved_prefix')].iloc[0]]]),'',
        '## Incertitude, concentration et régimes','',
        'Bootstrap descriptif3000tirages seed20261026 : blocs circulaires5/20séances pour moyenne quotidienne, clusters annuels pour bps/trade. Intervalles conditionnels, exclusions au zéro comptable, peu de clusters et aucune correction des essais multiples. Ils ne prouvent pas une performance future.','',
        table(['ETF','Période','IC95 moyenne quotidienne %, blocs5','Blocs20','IC95 bps/trade, années'],intervals),'',
        table(['ETF','Période','Sans top3 %','Sans2020 %','Pertes consécutives max'],[[r['symbol'],r['period'],f"{r['without_top3_pct']:.2f}",f"{r['without2020_pct']:.2f}",r['longest_loss_streak']] for r in concentration]),'',
        'Ablations : rendements concernés mis à zéro dans le compte original, sans nouveau sizing. Les CSV annual/monthly/directions/quality_reasons et features détaillent la concentration, le sens, les coûts et les motifs de non-entrée.','',
        '## Figures','',*['!['+name+'](figures/'+file+'.png)\n' for name,file in [('Capital et drawdown','equity_drawdown'),('Coûts','cost_sensitivity'),('Sensibilités','rule_sensitivity'),('Années','annual_returns')]],
        '## Contrôles, limites et décision','',
        '[Tests, revue et replay indépendant](../../VALIDATION.md). Protocole, code, audit, rapport et dépendances figés avant PnL. L’audit utilise des segments pandas EWM sur closes+cash cumulatif passé, distincts de la récurrence du moteur, puis vérifie décisions, fills, sizing, frais et comptes sans appeler la stratégie. Source commune : ce n’est pas une validation sur un autre fournisseur.','',
        'Limites : prix de trades consolidés plutôt que bid/ask/carnet, ordre des ticks inconnu, coûts fixes/shorts non garantis, crise incomplète, formalisation propre différente des recettes discrétionnaires, famille et paramètres examinés sur des données déjà explorées.','',decision+' Les deux bots QQQ existants ne sont pas modifiés ; aucun nouveau bot ni ordre réel.']
    (out/'RAPPORT_FINAL.md').write_text('\n'.join(text)+'\n',encoding='utf-8');print('Report,4standalone figures and descriptive tables generated.')

if __name__=='__main__':main()
