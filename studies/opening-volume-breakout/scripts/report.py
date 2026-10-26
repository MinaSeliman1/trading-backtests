"""Derive French research report and standalone scientific figures from exports."""
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
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=ROOT/'results/2026-10-24-v1');out=p.parse_args().out
    assert json.loads((out/'RUN_COMPLETE.json').read_text())['executions']==72
    c=pd.read_csv(out/'comparison_all.csv');principal=c[c.variant=='reference'];annual=[];monthly=[];directions=[];concentration=[];coverage=[]
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
    for name,rows in [('annual',annual),('monthly',monthly),('directions',directions),('concentration',concentration),('quality_reasons',coverage)]:pd.DataFrame(rows).to_csv(out/f'{name}.csv',index=False)
    plt.rcParams.update({'font.size':10,'axes.grid':True,'grid.alpha':.2,'axes.spines.top':False,'axes.spines.right':False});colors={'SPY':'#2563eb','QQQ':'#d97813'};figures=out/'figures';figures.mkdir(exist_ok=True)
    fig,axes=plt.subplots(2,1,figsize=(11,7),sharex=True)
    for r in principal[principal.period=='ALL'].itertuples():
        d=pd.read_csv(out/r.label/'daily.csv');dates=pd.to_datetime(d.date);equity=d.equity.mask(d.conditionally_excluded);dd=((d.equity/np.maximum.accumulate(np.r_[100000,d.equity])[1:]-1)*100).mask(d.conditionally_excluded)
        axes[0].plot(dates,equity,label=r.symbol,color=colors[r.symbol]);axes[1].plot(dates,dd,label=r.symbol,color=colors[r.symbol])
    axes[0].axhline(100000,color='#555',lw=.8);axes[0].set(title='ORB confirmé + RVOL : référence après frais',ylabel='Capital conditionnel USD');axes[1].set(ylabel='Drawdown quotidien %',xlabel='2016–16/10/2026 ; trous de couverture non interpolés')
    for ax in axes:ax.legend()
    fig.tight_layout();fig.savefig(figures/'equity_drawdown.png',dpi=160);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(11,4.5))
    for ax,s in zip(axes,['SPY','QQQ']):
        for period in ['A','B','ALL']:
            z=c[(c.symbol==s)&(c.period==period)&c.variant.isin(['reference','cost_0.02','cost_0.03','cost_0.05'])].sort_values('slippage');ax.plot(z.slippage,z.total_return_pct,marker='o',label=period)
        ax.axhline(0,color='#555',lw=.8);ax.set(title=s,xlabel='Friction USD/action/côté',ylabel='Résultat net conditionnel %');ax.legend()
    fig.suptitle('Stress de coûts : comptes redimensionnés à chaque scénario');fig.tight_layout();fig.savefig(figures/'cost_sensitivity.png',dpi=160);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(11,4.5))
    for ax,s in zip(axes,['SPY','QQQ']):
        labels=['no_volume','reference','volume_1.5','volume_2'];z=c[(c.symbol==s)&(c.period=='ALL')].set_index('variant').loc[labels]
        ax.bar(np.arange(4),z.total_return_pct,color=colors[s]);ax.set_xticks(np.arange(4),['OFF','≥1','≥1,5','≥2']);ax.axhline(0,color='#555',lw=.8);ax.set(title=s,xlabel='Seuil RVOL (sensibilités fixées)',ylabel='Net ALL conditionnel %')
    fig.suptitle('Effet du filtre de volume, avec confirmation identique');fig.tight_layout();fig.savefig(figures/'volume_filter.png',dpi=160);plt.close(fig)
    fig,ax=plt.subplots(figsize=(11,4.5));z=pd.DataFrame(annual);z[z.period=='ALL'].pivot(index='bucket',columns='symbol',values='return_pct')[['SPY','QQQ']].plot.bar(ax=ax,color=[colors['SPY'],colors['QQQ']]);ax.axhline(0,color='#555',lw=.8);ax.set(title='Référence par année ; 2016/2026 partielles',ylabel='Net conditionnel %',xlabel='Année');fig.tight_layout();fig.savefig(figures/'annual_returns.png',dpi=160);plt.close(fig)
    old=pd.read_csv(ROOT.parent/'opening-range-5m/results/2026-10-20/comparison_all.csv')
    old=old[(old['mode']=='both')&(old.quality=='complete_days')&(old.priority=='stop_first')&np.isclose(old.slippage,.01)]
    compare=[]
    for r in principal.itertuples():
        a=old[(old.symbol==r.symbol)&(old.period==r.period)].iloc[0];b=c[(c.symbol==r.symbol)&(c.period==r.period)&(c.variant=='no_volume')].iloc[0]
        compare.append([r.symbol,r.period,f'{a.total_return_pct:.2f} / {int(a.trades)}',f'{b.total_return_pct:.2f} / {int(b.trades)}',f'{r.total_return_pct:.2f} / {int(r.trades)}'])
    good=all(principal.total_return_pct>0)
    decision='Référence positive dans les deux périodes sur les deux ETF ; résultat exploratoire à confirmer prospectivement, aucun nouveau bot activé.' if good else 'La référence ne reste pas positive dans toutes les périodes et sur les deux ETF. Pas de nouveau bot justifié par cette étude ; conserver les règles et ne pas promouvoir une variante choisie après résultats.'
    text=['# ORB confirmé + volume relatif — rapport final SPY / QQQ','',decision,'',
        'Recherche publique puis72 scénarios figés avant PnL. Capital100000USD par scénario ; ALL4janvier2016–16octobre2026, A jusqu’au30avril2024, B du1mai2024 au16octobre2026. B a déjà été explorée : aucun nouvel OOS aveugle. Résultats conditionnels à la résolution des données.','',
        '## Pourquoi cette piste','',
        'La [recherche comparative](../../RESEARCH.md) examine publications, forums et GitHub : volume d’ouverture, VWAP tendance, Dual Thrust, volume profile et paire SPY/QQQ. Le choix est une priorité de recherche documentée, pas une garantie de meilleure stratégie. Le cadre Stocks in Play motive l’hypothèse volume/cassure ; ses rendements de portefeuille d’actions ne sont jamais importés dans les ETF. Les forums contiennent des réplications divergentes et les dépôts peuvent mélanger versions ou essais multiples.','',
        '## Formalisation testée','',
        'Première plage5minutes RTH, direction de son corps. RVOL = volume de cette plage / moyenne des14plages correspondantes précédentes, seuil≥1. Attendre une clôture minute strictement hors range dans le même sens, puis entrer à l’open suivant avant11:30NY. Une entrée maximum par séance. Taille entière décidée au signal : risque cible1%, plafond1x. Stop extrême opposé, TP10R depuis open exécuté de référence, stop prioritaire si touches simultanées ; gap stop au prix défavorable, gap TP au niveau cible. Flat à l’open15:59 ou12:59.','',
        'Extension de notre ORB ; pas réplication du papier actions : absence du classement top20, stop range au lieu d’ATR, confirmation au close et cible10R. Le benchmark ancien ORB entre09:35 sans confirmation de cassure ni RVOL. [Protocole exact](../../PROTOCOL_EXECUTION.md). Aucun changement des simulations existantes.','',
        '## Résultats principaux nets','',table(['ETF','Période','Trades','Net %','CAGR %','PF','WR %','DD marks %','Sans top3jours %'],[[r.symbol,r.period,int(r.trades),f'{r.total_return_pct:.2f}',f'{r.cagr_pct:.2f}',f'{r.profit_factor:.3f}',f'{r.win_rate_pct:.2f}',f'{r.observed_close_drawdown_pct:.2f}',f'{r.return_without_top3_days_pct:.2f}'] for r in principal.itertuples()]),'',
        'Le CAGR porte sur toute la période nominale, chauffe incluse. Le DD marks comprend événements de fill et closes1min entièrement détenus ; il ne borne pas chaque tick. Les deux ETF sont corrélés. Aucun dépassement du rendement passif à exposition équivalente n’est revendiqué. Cash témoin0%, sans rémunération ni inflation.','',
        '## Apport des deux changements','',table(['ETF','Période','Ancien ORB : net% / trades','Confirmation seule : net% / trades','Confirmation + RVOL : net% / trades'],compare),'',
        'Chaque compte est recalculé séparément avec son capital composé. Ce tableau mesure une association historique, pas l’effet causal garanti du filtre. Le RVOL et la confirmation retirent des jours/trades ; ils ne créent pas un échantillon indépendant. Le protocole n’a pas essayé RVOL sans confirmation.','',
        '## Coûts identiques et attribution','',
        'Commission0,0035USD/action/côté, minimum0,35 ; friction défavorable0,01USD/action/côté ; empruntSHORT1%annuel/360, minimum un jour. Friction déjà incorporée aux prix et soustraite une seule fois dans l’attribution. Coûts de recherche, pas tarif broker garanti. Pas de bid/ask ni file d’attente observés.','',
        table(['ETF','Période','Prix USD','Friction USD','Commission USD','Emprunt USD','Net USD','Exposition RTH bornehaute %'],[[r.symbol,r.period,*[f'{getattr(r,k):.2f}' for k in ['price_move_pnl','friction_cost','commission','borrow_fee','net_pnl','regular_time_exposure_upper_pct']]] for r in principal.itertuples()]),'',
        'Le risque1% est calculé avant open et hors frais. Les gaps peuvent dépasser les plafonds effectifs de risque/levier ; leurs comptes sont exportés. Les valeurs de stop/target ne sont pas recalibrées après un gap.','',
        '## Sensibilités fixées à l’avance','',table(['Variante ALL : trades / net% / PF','SPY','QQQ'],[[v]+[f'{int(r.trades)} / {r.total_return_pct:.2f} / {r.profit_factor:.3f}' for s in ['SPY','QQQ'] for r in [c[(c.symbol==s)&(c.period=='ALL')&(c.variant==v)].iloc[0]]] for v in c.variant.drop_duplicates()]),'',
        '12 variantes ×2ETF ×3périodes ; aucune optimisation pour retenir le meilleur résultat. Volume OFF/1,5/2, range15min, cutoff10:30, LONG/SHORT, prefix et stress0,02/0,03/0,05. Les comptes recouvrants ne sont pas72preuves indépendantes. [Tous les scénarios](comparison_all.csv).','',
        '## Couverture, chauffe et incertitude','',
        'Source SIP déjà acquise, prix minute non ajustés, calendrier NYSE et SHA des archives/préparations vérifiés avant calcul.2714séances préparées dont un padding2015-12-31,2713évaluées ; SPY2705/QQQ2707complètes dans la préparation. Les premières14séances calendaires et tout trou de fenêtre antérieure limitent RVOL. Ne jamais remplacer une date inconnue. Pas d’usage du volume de fin de journée. [Sources et empreintes](DATA_SOURCE_PROFILE.json).','',
        'Principal complete_days applique un filtre futur de qualité sur les jours pouvant générer une entrée. Prefix retire ce filtre : trou avant décision=>signal inconnu, trou actif=>trade entier non résolu et frais d’entrée connus exportés. Aucune interpolation. Le zéro de chaînage comptable d’un jour exclu n’est pas un cash observé. Les fenêtres historiques inconnues sont marquées en couverture ; une chauffe connue ne génère aucun ordre.','',
        table(['ETF','Période','Exclues principal','Trades principal','Net principal %','Trades prefix','Non résolues','Net prefix %'],[[r.symbol,r.period,int(r.data_excluded_sessions),int(r.trades),f'{r.total_return_pct:.2f}',int(p.trades),int(p.unresolved_sessions),f'{p.total_return_pct:.2f}'] for r in principal.itertuples() for p in [c[(c.symbol==r.symbol)&(c.period==r.period)&(c.variant=='resolved_prefix')].iloc[0]]]),'',
        'Les fichiers uncertainty contiennent3000bootstrap circulaires en blocs5/20séances et clusters annuels (seed20261024). Intervalles descriptifs conditionnels, sans correction des opportunités inconnues ou essais multiples. L’égalité éventuelle principal/prefix ne démontre pas la qualité d’exécution sur les lacunes.','',
        table(['ETF','Période','Sans top3 %','Sans2020 %','Pertes consécutives max'],[[r['symbol'],r['period'],f"{r['without_top3_pct']:.2f}",f"{r['without2020_pct']:.2f}",r['longest_loss_streak']] for r in concentration]),'',
        'Ablations = mettre à zéro les rendements sélectionnés du compte original, sans redimensionner un nouveau portefeuille. Années, mois, directions, raisons de non-entrée et features sont exportés pour inspection.','',
        '## Figures','',*['!['+name+'](figures/'+file+'.png)\n' for name,file in [('Capital et drawdown','equity_drawdown'),('Coûts','cost_sensitivity'),('Filtre de volume','volume_filter'),('Années','annual_returns')]],
        '## Validation et décision','',
        '[Preuves de tests, revue et audit](../../VALIDATION.md). Snapshots et protocole pré-performance sont archivés. L’audit séparé contrôle les décisions, ordres, tailles, coûts et comptes sur les mêmes données préparées ; ce n’est pas une seconde source de marché. Les tests synthétiques ne sont pas des performances historiques.','',
        'Limites : minute de trade consolidé plutôt que quotes broker, fills approximés, crise2020 incomplète, accès aux shorts non garanti, frais variables non reconstruits, données déjà explorées et sélection de famille parmi plusieurs essais. Le volume anormal d’un ETF n’équivaut pas à une nouvelle spécifique d’entreprise.','',decision+' Aucune variante promue après PnL, aucun nouveau bot ni ordre réel.']
    (out/'RAPPORT_FINAL.md').write_text('\n'.join(text)+'\n',encoding='utf-8');print('Report, 4 standalone figures, descriptive tables generated.')

if __name__=='__main__':main()
