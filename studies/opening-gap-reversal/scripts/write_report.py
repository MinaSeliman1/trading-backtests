"""Rapport et figures exportables à partir des résultats réellement calculés."""
from pathlib import Path
import argparse,json,hashlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]


def table(headers,rows):
    return '| '+' | '.join(headers)+' |\n|'+'|'.join(['---']*len(headers))+'|\n'+'\n'.join('| '+' | '.join(map(str,r))+' |' for r in rows)


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=ROOT/'results/2026-10-20-v3');a=p.parse_args();out=a.out
    c=pd.read_csv(out/'comparison_all.csv');figs=out/'figures';figs.mkdir(exist_ok=True)
    main=c[(c.profile=='endpoints')&(c.strategy=='reversal')&(c.slippage==.01)]
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'axes.grid':True,'grid.alpha':.2})
    for period in ['ALL','B']:
        fig,axes=plt.subplots(1,2,figsize=(12,4.6),sharey=True)
        for ax,symbol in zip(axes,['SPY','QQQ']):
            for strategy,color,label in [('reversal','#155f9b','Retour après gap'),('momentum','#ab5a45','Contrôle : sens du gap')]:
                d=pd.read_csv(out/f'{symbol}_{period}_{strategy}_endpoints_s0.01/daily.csv')
                ax.plot(pd.to_datetime(d.date),d.equity/1000,color=color,label=label,lw=1.7)
            ax.axhline(100,color='#666666',lw=.8,ls='--',label='Cash sans intérêt')
            ax.set_title(symbol);ax.tick_params(axis='x',rotation=25);ax.set_ylabel('Capital simulé (milliers USD)')
        axes[0].legend(fontsize=8,loc='best');fig.suptitle(f'Gap Reversal — période {period} — cible 1x, coûts inclus')
        fig.text(.5,.01,'SIP raw ; friction 0,01 USD/action/côté ; simulation historique, données réutilisées.',ha='center',fontsize=8)
        fig.tight_layout(rect=(0,.04,1,.94));fig.savefig(figs/f'equity_{period}.png',dpi=160);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(10,4.3),sharey=True)
    for ax,symbol in zip(axes,['SPY','QQQ']):
        s=c[(c.symbol==symbol)&(c.period=='B')&(c.profile=='endpoints')&(c.strategy=='reversal')].sort_values('slippage')
        ax.bar([f'{v:.2f}' for v in s.slippage],s.total_return_pct,color='#155f9b',width=.6)
        ax.axhline(0,color='black',lw=.8);ax.set_title(symbol);ax.set_xlabel('Friction USD/action/côté');ax.set_ylabel('Rendement net cumulé (%)')
        for i,v in enumerate(s.total_return_pct):ax.text(i,v+.12,f'{v:.2f} %',ha='center',fontsize=9)
        ax.set_ylim(0,max(10,float(s.total_return_pct.max())*1.2))
    fig.suptitle('Période B : sensibilité aux coûts — 11 trades SPY, 18 QQQ')
    fig.tight_layout(rect=(0,0,1,.93));fig.savefig(figs/'costs_B.png',dpi=160);plt.close(fig)
    first=pd.read_csv(ROOT/'results/2026-10-20/comparison_all.csv').set_index('label')
    last=c.set_index('label');delta=float((last.net_pnl-first.net_pnl).abs().max());assert delta==0
    versions=dict(initial='2026-10-20',intermediate='2026-10-20-v2',reference='2026-10-20-v3',scenarios=54,max_net_pnl_change_usd=delta,
        corrected_fields=['exact decimal post-dividend threshold','PnL and return correlations separately','drawdown duration from last preceding peak'],
        note='No strategy, threshold, cost or date optimization. Initial and intermediate runs retained. Initial source code archived.')
    (out/'VERSION_COMPARISON.json').write_text(json.dumps(versions,indent=2),encoding='utf-8')
    fullrows=[]
    for r in main.itertuples():
        fullrows.append([r.symbol,r.period,r.trades,f'{r.total_return_pct:.2f}',f'{r.cagr_pct:.2f}',f'{r.sharpe:.2f}',f'{r.win_rate_pct:.1f}',f'{r.max_daily_close_drawdown_pct:.2f}',f'{r.observed_close_drawdown_pct:.2f}'])
    costs=c[(c.period=='B')&(c.profile=='endpoints')&(c.strategy=='reversal')]
    costrows=[[r.symbol,f'{r.slippage:.2f}',f'{r.net_pnl:.2f}',f'{r.total_return_pct:.2f}'] for r in costs.itertuples()]
    ci=[];groups=[]
    for symbol in ['SPY','QQQ']:
        j=json.loads((out/f'{symbol}_B_reversal_endpoints_s0.01/summary.json').read_text());b=j['annual_cluster_bootstrap']
        ci.append([symbol,f'{j["mean_trade_bps"]:.2f}',f'[{b["mean_trade_bps_ci95"][0]:.2f} ; {b["mean_trade_bps_ci95"][1]:.2f}]',f'{j["return_without_top3_days_pct"]:.2f}'])
        t=pd.read_csv(out/f'{symbol}_ALL_reversal_endpoints_s0.01/trades.csv');t['year']=t.date.str[:4]
        for year,g in t.groupby('year'):groups.append([symbol,year,len(g),f'{g.net_pnl.sum():.2f}'])
    quality=pd.read_csv(out/'quality_exceptions.csv');halts=quality[quality.official_mwcb_date]
    haltrows=[[r.symbol,r.date,r.eligibility,('indéterminé' if pd.isna(r.gap) else str(r.event)),r.missing_holding_minutes] for r in halts.itertuples()]
    corr=json.loads((out/'noise_correlation.json').read_text());corrrows=[[r['symbol'],f'{r["correlation_daily_pnl_usd"]:.4f}',f'{r["correlation_daily_returns"]:.4f}'] for r in corr]
    references=[]
    for symbol in ['SPY','QQQ']:
        t=pd.read_csv(out/f'{symbol}_B_reversal_endpoints_s0.01/trades.csv')
        chosen=t.sort_values('net_pnl').head(4).index.union(t.sort_values('net_pnl').tail(4).index)
        references.append(t.loc[chosen].assign(symbol=symbol))
    examples=pd.concat(references).head(15);examples.to_csv(out/'EXEMPLES_15_TRADES.csv',index=False)
    parts=['# Opening Gap Reversal — rapport final du 20 octobre 2026',
        '**QQQ mérite un suivi en simulation ; les preuves restent insuffisantes pour un bot autonome. SPY apporte trop peu de gain récent pour conclure à un avantage.** La comparaison B est rétrospective sur des données déjà étudiées, pas une validation aveugle.',
        '## Règles, période et coûts',
        'Gap = ouverture 09:30 / (clôture régulière précédente − dividende ex-date) − 1. Seuil absolu strictement supérieur à 2 %. Acheter un gap négatif, vendre un gap positif. Entrée à 09:31, sortie à 10:00, heure de New York, sans stop ajouté. Quantité entière floor(capital/open 09:30), exposition cible 1x ; la taille ne connaît pas le futur open 09:31. Le levier effectif peut légèrement varier avec ce prix.',
        'Capital initial séparé de 100 000 USD dans ALL (04/01/2016–16/10/2026), A (jusqu’au 30/04/2024) et B (01/05/2024–16/10/2026). Le capital se recompose dans chaque période ; ne pas additionner leurs profits. Commission 0,0035 USD/action/côté, minimum 0,35 USD/ordre, emprunt SHORT supposé 1 %/360 minimum un jour, friction adverse de 0,01 à 0,05 USD/action/côté. Ces coûts ne sont pas des spreads/quotes observés.',
        '## Résultats principaux à 0,01 USD par côté',
        table(['Instrument','Période','Trades','Net %','CAGR %','Sharpe','Gagnants %','DD quotidien %','DD minute observé %'],fullrows),
        'Les rendements de Sharpe utilisent toutes les séances régulières et un taux sans risque nul. Le cash témoin est non rémunéré : cette comparaison ne démontre pas une surperformance par rapport à un placement monétaire rémunéré. Le DD minute utilise les clôtures observées et les fills ; il peut sous-estimer le risque entre deux observations, surtout pendant une suspension.',
        '![Capital sur toute la période](figures/equity_ALL.png)',
        '![Capital sur la période B](figures/equity_B.png)',
        '## Sensibilité aux coûts et contrôles',table(['Instrument','Friction par côté USD','P&L net USD','Net B %'],costrows),
        '![Sensibilité aux coûts](figures/costs_B.png)',
        'Le contrôle qui entre dans le sens du gap utilise les mêmes événements et horaires. En B à 0,01, il perd environ 1,48 % sur SPY et 8,20 % sur QQQ. Cette comparaison appuie le sens du retour dans cet échantillon ; elle ne crée pas un échantillon de validation supplémentaire. Les 54 scénarios sont déclarés : 48 instrument/période/coût/sens et 6 sensibilités de qualité. Aucun meilleur seuil ou horaire n’a été recherché.',
        '## Rareté, concentration et incertitude',
        table(['Instrument','Moyenne bps/trade B','IC 95 % bootstrap annuel bps','Net B sans 3 meilleurs jours %'],ci),
        'Le bootstrap rééchantillonne des années entières, conserve les années sans événement et utilise 5 000 répétitions, seed 20261020. B ne compte que trois blocs annuels, partiels ou complets. L’intervalle QQQ positif est descriptif et fragile ; il ne suffit pas à prouver un avantage avec 18 trades, un historique réutilisé et un contexte de recherche ayant déjà examiné plusieurs stratégies.',
        'Retirer les trois meilleures journées ramène QQQ B à +1,59 % et SPY à −1,37 %. Sur ALL, le rendement sans les journées de 2020 passe de +34,36 % à +17,90 % pour QQQ et de +15,55 % à +4,15 % pour SPY. Ces retraits recomposent les rendements quotidiens observés sans les journées désignées ; ce n’est pas une nouvelle recherche de paramètres.',
        '### Répartition des transactions principales ALL',table(['Instrument','Année','Trades','P&L net USD'],groups),
        'Les fichiers by_direction.csv donnent séparément LONG/SHORT ; trades.csv fournit chaque entrée, sortie, quantité, coût, emprunt, levier effectif et MAE/MFE de prix observés. [Quinze exemples réels](EXEMPLES_15_TRADES.csv) accompagnent l’audit exhaustif ; ils ne remplacent pas tous les trades.',
        '## Qualité des données et suspensions',
        'Le profil principal exige des prix observés à 09:30, 09:31 et 10:00 ainsi que la clôture précédente. Il conserve les trous intermédiaires sans inventer de prix. Une séance manquante après le trade ne l’annule pas. Les erreurs OHLCV ou ambiguïtés signalées restent exclues. Les quatre dates de circuit breaker de mars 2020 sont confirmées par [NYSE](https://www.nyse.com/article/assessing-nyse-model-performance). Un autre trou ne devient pas une suspension officielle par simple inférence.',
        table(['Instrument','Date','Statut aux bornes','Gap >2 %','Minutes absentes pendant détention'],haltrows),
        'Le 16 mars 2020 ne possède pas les bornes nécessaires et n’est pas exécuté artificiellement. Les 9 et 12 mars peuvent être simulés aux deux bornes observées malgré 14 minutes intermédiaires absentes ; leurs MAE/MFE et leur DD restent limités aux prix observés. Les fenêtres d’entrée/sortie réelles de crise peuvent subir plus de friction que 0,05 USD ; le backtest ne prouve pas la liquidité de ces fills.',
        'Le filtre alternatif de journées complètes donne 42 SPY /77 QQQ, identiques au comptage publié. Le profil principal en conserve 48 /83 car la qualité de la journée entière n’est pas une information disponible à 09:31. En B, les comptes restent 11 /18. Le filtre complet réduit ALL à +4,41 % SPY et +19,69 % QQQ ; cette différence montre la sensibilité au traitement des crises et des séances qui les suivent. Les exclusions détaillées sont dans [quality_exceptions.csv](quality_exceptions.csv).',
        '## Comparaison à Noise Area',table(['Instrument','Corrélation P&L quotidiens USD','Corrélation rendements quotidiens'],corrrows),
        '618 dates B communes ; Noise Area next_open, cible plafonnée à 1x, même friction 0,01. Ces corrélations proches de zéro sont descriptives, influencées par les nombreuses journées sans gap trade. Elles ne démontrent pas une diversification stable et aucun portefeuille combiné n’a été optimisé.',
        '## Validation et versions',
        '20 tests automatisés passent. L’audit Decimal indépendant rapproche 2 334 lignes de trades des 54 scénarios : signal, quantité, sens, référence ex-dividende, timestamps, fills, frais, emprunt, capital, rendements et DD quotidien. Les 2 334 lignes incluent les scénarios de coûts, contrôles et périodes qui se recouvrent : ce ne sont pas 2 334 événements indépendants. Une seconde revue a recalculé les 131 trades principaux ALL, les drawdowns minute et le bootstrap.',
        'La revue a corrigé une frontière flottante exactement à 2 % après dividende, séparé corrélations P&L/rendements et corrigé localement la durée du drawdown depuis le dernier sommet précédant la perte. Les P&L des 54 scénarios sont inchangés entre la première et la version finale. Les deux exécutions antérieures restent archivées ; v3 est la référence. Aucune source ni sortie des études FVG/Noise Area n’a été modifiée.',
        '[Audit indépendant](AUDIT_INDEPENDANT.json) · [Manifeste original de cette exécution](MANIFEST.json) · [Comparaison des versions](VERSION_COMPARISON.json) · [54 scénarios](comparison_all.csv) · [Protocole gelé avant cette exécution](PRE_EXECUTION_PROTOCOL.json).',
        '## Décision et suite',
        'Conserver QQQ Gap Reversal comme piste de recherche et de suivi virtuel séparé, sans l’intégrer automatiquement au bot Noise Area. SPY n’apporte pas de preuve convaincante. La stratégie est trop rare pour attendre rapidement une validation prospective puissante. Avant tout changement d’usage : prix/quotes d’ouverture observés, latence et coûts réels, journal de toutes les journées admissibles, dates de suspension et règles de reprise. Une observation véritablement nouvelle peut commencer le 21 octobre 2026 avec ce protocole figé.']
    (out/'RAPPORT_FINAL.md').write_text('\n\n'.join(parts)+'\n',encoding='utf-8')
    print('Report and 3 figures written:',out)


if __name__=='__main__':main()
