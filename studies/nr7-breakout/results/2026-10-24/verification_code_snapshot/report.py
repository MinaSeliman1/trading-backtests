"""All reported values come from stored executions; no parameter selection."""
from pathlib import Path
import sys,json,argparse
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from nr7.data import source


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=ROOT/'results/2026-10-24');out=p.parse_args().out
    c=pd.read_csv(out/'comparison_all.csv');principal=c[(c['mode']=='both')&(c.slippage==.01)&(c.quality=='complete_days')&c.require_nr7]
    figures=out/'figures';figures.mkdir(exist_ok=True)
    primary=principal[principal.period=='ALL'];annual=[];monthly=[];directions=[];ablation=[]
    fig,axes=plt.subplots(2,1,figsize=(11,7),sharex=True)
    for row in primary.itertuples():
        d=pd.read_csv(out/row.label/'daily.csv');t=pd.read_csv(out/row.label/'trades.csv');dates=pd.to_datetime(d.date)
        axes[0].plot(dates,d.equity,label=row.symbol);axes[1].plot(dates,(d.equity/d.equity.cummax()-1)*100,label=row.symbol)
    axes[0].axhline(100000,color='gray',lw=.8);axes[0].set_ylabel('USD — compte conditionnel');axes[0].set_title('NR7 : BOTH, friction 0,01 USD/action/côté')
    axes[1].set_ylabel('Drawdown closes quotidiens (%)');axes[0].legend();axes[1].legend()
    for ax in axes:ax.grid(alpha=.2)
    fig.tight_layout();fig.savefig(figures/'equity_drawdown.png',dpi=150);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(11,4))
    for ax,symbol in zip(axes,('SPY','QQQ')):
        for period in ('A','B','ALL'):
            z=c[(c.symbol==symbol)&(c.period==period)&(c['mode']=='both')&(c.quality=='complete_days')&c.require_nr7].sort_values('slippage')
            ax.plot(z.slippage,z.total_return_pct,marker='o',label=period)
        ax.axhline(0,color='gray',lw=.8);ax.set_title(symbol);ax.set_xlabel('Friction USD/action/côté');ax.set_ylabel('Rendement net conditionnel (%)');ax.legend();ax.grid(alpha=.2)
    fig.tight_layout();fig.savefig(figures/'friction_stress.png',dpi=150);plt.close(fig)
    for row in principal.itertuples():
        d=pd.read_csv(out/row.label/'daily.csv');t=pd.read_csv(out/row.label/'trades.csv');dates=pd.to_datetime(d.date)
        for unit,container in [('Y',annual),('M',monthly)]:
            for key,g in d.groupby(dates.dt.to_period(unit)):
                container.append(dict(symbol=row.symbol,period=row.period,bucket=str(key),return_pct=(np.prod(1+g.return_net)-1)*100,net_pnl=g.net_pnl.sum(),trades=g.trades.sum(),excluded=g.conditionally_excluded.sum()))
        for key,g in t.groupby('direction'):directions.append(dict(symbol=row.symbol,period=row.period,direction=key,trades=len(g),net_pnl=g.net_pnl.sum(),commission=g.commission.sum(),borrow=g.borrow_fee.sum(),friction=g.friction_cost.sum()))
        mask=dates.dt.year!=2020;ablation.append(dict(symbol=row.symbol,period=row.period,return_without_top3_pct=row.return_without_top3_days_pct,
            return_without_2020_pct=(np.prod(1+d.loc[mask,'return_net'])-1)*100,method='Set selected daily returns to zero; keep original return sequence elsewhere, not a re-sized account.'))
    for name,rows in [('annual',annual),('monthly',monthly),('directions',directions),('ablations',ablation)]:pd.DataFrame(rows).to_csv(out/f'{name}.csv',index=False)
    fig,ax=plt.subplots(figsize=(11,4));y=pd.DataFrame(annual);z=y[y.period=='ALL'].pivot(index='bucket',columns='symbol',values='return_pct')[['SPY','QQQ']];z.plot.bar(ax=ax,color=['#1f77b4','#ff7f0e']);ax.axhline(0,color='gray',lw=.8);ax.set_xlabel('Année');ax.legend(title='Instrument');ax.set_ylabel('Rendement annuel conditionnel (%)');ax.set_title('Années partielles aux bornes ; mêmes paramètres');fig.tight_layout();fig.savefig(figures/'annual_returns.png',dpi=150);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(11,4))
    for ax,row in zip(axes,primary.itertuples()):
        t=pd.read_csv(out/row.label/'trades.csv');ax.hist(t.net_bps,bins=40,color='#3c78a8');ax.axvline(0,color='black',lw=.8);ax.set_title(row.symbol);ax.set_xlabel('PnL net / notionnel entrée (bps)');ax.set_ylabel('Transactions')
    fig.tight_layout();fig.savefig(figures/'trade_distribution.png',dpi=150);plt.close(fig)
    lines=['# NR7 SPY/QQQ — rapport final du 24 octobre 2026','',
        '48 scénarios figés avant les calculs ; dates2016–16/10/2026. A2016–30/04/2024 ; B01/05/2024–16/10/2026, période déjà explorée et réutilisée : aucun nouvel OOS aveugle. Capital100000USD indépendant par scénario.','',
        '## Résultats principaux, frais inclus','',
        '| Instrument | Période | Net % | CAGR % | DD marks observés % | Trades | PF | Sans top3 jours % | Coûts USD : friction / commissions / emprunt |',
        '|---|---|---:|---:|---:|---:|---:|---:|---|']
    for r in principal.itertuples():lines.append(f'| {r.symbol} | {r.period} | {r.total_return_pct:.2f} | {r.cagr_pct:.2f} | {r.observed_close_drawdown_pct:.2f} | {r.trades} | {r.profit_factor:.3f} | {r.return_without_top3_days_pct:.2f} | {r.friction_cost:.2f} / {r.commission:.2f} / {r.borrow_fee:.2f} |')
    lines+=['','## Interprétation et sensibilité','',
        'Les variantes sont toutes publiées dans comparison_all.csv, sans retenir après coup la meilleure. Les LONG/SHORT seuls filtrent le premier signal. Le témoin sans filtre NR7 utilise son propre capital et ses quantités : comparaison descriptive, pas effet causal à exposition égale. Cash vaut0% avant inflation. Les trois meilleurs jours sont classés par PnL net positif en USD ; leurs rendements sont ensuite annulés sans recalculer les quantités.','']
    for symbol in ('SPY','QQQ'):
        r=principal[(principal.symbol==symbol)&(principal.period=='B')].iloc[0];allr=principal[(principal.symbol==symbol)&(principal.period=='ALL')].iloc[0]
        stress=c[(c.symbol==symbol)&(c.period=='ALL')&(c['mode']=='both')&(c.quality=='complete_days')&c.require_nr7].sort_values('slippage')
        u=json.loads((out/f'{symbol}_B_uncertainty.json').read_text());ab=pd.DataFrame(ablation);az=ab[(ab.symbol==symbol)&(ab.period=='ALL')].iloc[0]
        lines +=[f'{symbol} : ALL {allr.total_return_pct:.2f}% net, B {r.total_return_pct:.2f}% sur {r.trades} transactions. ALL sans rendements2020 : {az.return_without_2020_pct:.2f}%. Stress ALL de0,01 à0,05USD : '+', '.join(f'{x.slippage:g}→{x.total_return_pct:.2f}%' for x in stress.itertuples())+'.',
            f'B : IC95 descriptif moyenne trade bps, clusters annuels {u["annual_cluster"]["mean_trade_bps_ci95"]} ; blocs5/20 pour moyenne quotidienne : {u["blocks"]}. Peu de clusters annuels, dépendance et absence de correction des comparaisons multiples limitent ces intervalles.','']
    lines+=['## Validation, couverture et exécution','',
        'Les sources sont les mêmes archives Alpaca SIP que les études précédentes. Six fichiers préparés et six acquisitions OHLCV brutes sont revérifiés par SHA256 ; calendrier XNYS continu, horodatages et demi-séances contrôlés. DATA_SOURCE_PROFILE.json contient la provenance et les nombres de séances complètes/incomplètes. PRE_EXECUTION_PROTOCOL.json fige règles,48spécifications, empreintes et versions avant la boucle financière.','',
        'Le principal reste conditionnel au filtre complete_days connu après coup. Pour une absence NR7 ou un historique invalide connue avant la séance, le cash est causal. Pour des données inconnues avant signal ou en position, observed_return est manquant et le zero du compte conditionnel ne représente pas une performance observée. resolved_prefix, intentions non résolues et frais connus sont exportés. Il ne faut pas interpréter ces exclusions comme un portefeuille continu réalisable.','',
        'Cas matériel : QQQ le2020-03-09 est une séance NR7 éligible incomplète. Le principal l’exclut ; resolved_prefix retrouve une entrée SHORT59actions à193,265USD, puis un open actif manquant au slot5. Le trade entier reste omis, avec commission d’entrée connue0,35USD et friction d’entrée0,59USD exportées. L’égalité des résultats principal/prefix ne démontre donc pas une robustesse à cette séance : ils omettent tous deux le même trade non résolu. SPY n’a pas de séance NR7 courante éligible incomplète dans ces archives.','',
        'Le stop et les fills utilisent les prix OHLC minute : spread, liquidité, ordre exact des ticks, disponibilité SHORT et latence réelle ne sont pas prouvés. Le sizing est causal au close du signal ; les gaps peuvent dépasser le risque1% ou le plafond1x effectifs. Friction0,01/côté, commission0,0035minimum0,35 et emprunt1%/360 sont des hypothèses comparables, pas une cotation de frais garantie. Les frais réglementaires variables ne sont pas séparés.','',
        'AUDIT_INDEPENDENT.json décrit la reconstruction indépendante Decimal des features, signaux, trades, coûts, comptes et marks sur48scénarios ; AUDIT_SCENARIOS.csv compare comptes finaux, nombres de trades et drawdowns. Le JSON liste les agrégats effectivement recalculés, dont CAGR, Sharpe, PF et coûts. Les lignes de périodes A/B/ALL se recouvrent : leur nombre ne mesure pas des trades uniques. Les tableaux annual/monthly/directions/ablations et les figures complètent le rapport.','',
        '## Décision','',
        'BOTH principal perd en B sur SPY et QQQ : cette version NR7 n’est pas retenue pour un nouveau bot. Les petits gains historiques ALL sont sensibles aux frais et ne compensent pas la faiblesse récente ni les limites de couverture. Les variantes LONG/SHORT et le témoin restent exploratoires, sans sélectionner après coup un sous-ensemble positif. Aucun paramètre n’est retouché à partir de ces résultats. La simulation ORB reste une expérience distincte avec son propre journal.','',
        '## Figures','',*[f'![{name}](figures/{name}.png)' for name in ('equity_drawdown','friction_stress','annual_returns','trade_distribution')]]
    (out/'RAPPORT_FINAL.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    source.write_json(out/'DELIVERY_MANIFEST.json',dict(files={p.relative_to(out).as_posix():source.sha(p) for p in out.rglob('*') if p.is_file() and p.name!='DELIVERY_MANIFEST.json'}))
    print('Report, four figures and delivery manifest written.')


if __name__=='__main__':main()
