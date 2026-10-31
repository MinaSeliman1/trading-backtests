"""Render factual report, fixed screening and static figures from reviewed exports."""
from pathlib import Path
import sys,json,argparse,math
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def table(rows,columns):
    def cell(x):
        if x is None or isinstance(x,(float,np.floating)) and not math.isfinite(x):return '—'
        return f'{x:.2f}' if isinstance(x,(float,np.floating)) else str(x)
    return '| '+' | '.join(label for _,label in columns)+' |\n|'+ '|'.join('---' for _ in columns)+'|\n'+'\n'.join('| '+' | '.join(cell(row.get(k)) for k,_ in columns)+' |' for row in rows)

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=ROOT/'results/2026-10-31-v1');out=p.parse_args().out.resolve()
    df=pd.read_csv(out/'comparison_all.csv');ref=df[df.variant=='reference'];audit=json.loads((ROOT/'audit/AUDIT_RESULTS.json').read_text());assert audit['status']=='passed'
    def row(s,period='ALL',v='reference'):return df[(df.symbol==s)&(df.period==period)&(df.variant==v)].iloc[0].to_dict()
    checks={}
    for s in ['SPY','QQQ']:
        u=json.loads((out/f'{s}_ALL_uncertainty.json').read_text())
        checks[s]={'trades_all_ge100':row(s)['trades']>=100,'reference_A_B_ALL_positive':all(row(s,p)['net_pnl']>0 for p in ['A','B','ALL']),
          'all_without_top3_positive':row(s)['return_without_top3_days_pct']>0,'A_double_friction_positive':row(s,'A','cost_0.02')['net_pnl']>0,
          'all_block20_ci_lower_positive':u['blocks']['20']['conditional_daily_mean_ci95'][0]>0}
    passed=all(all(x.values()) for x in checks.values());decision='Candidat historique à discuter, aucun nouveau bot automatique.' if passed else 'Adaptation intraday écartée pour un nouveau bot : critères prédéfinis non satisfaits.'
    screening={'criteria':checks,'all_passed':passed,'decision':decision,'multiple_testing_adjusted':False,'blind_oos':False}
    (out/'SCREENING.json').write_text(json.dumps(screening,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    colors={'SPY':'#215ca0','QQQ':'#b64f13'};figs=out/'figures';figs.mkdir(exist_ok=True)
    fig,ax=plt.subplots(figsize=(10,5))
    for s in ['SPY','QQQ']:
        d=pd.read_csv(out/f'{s}_ALL_reference/daily.csv');ax.plot(pd.to_datetime(d.date),(d.equity/100000-1)*100,label=s,color=colors[s])
    ax.axhline(0,color='black',lw=.7);ax.set(ylabel='Rendement net cumulé (%)',title='Turnaround Tuesday intraday — comptes historiques conditionnels');ax.legend();ax.grid(alpha=.2);fig.tight_layout();fig.savefig(figs/'equity.png',dpi=150);plt.close(fig)
    fig,ax=plt.subplots(figsize=(10,4.5));years=sorted(pd.DatetimeIndex(pd.read_csv(out/'SPY_ALL_reference/daily.csv').date).year.unique());pos=np.arange(len(years))
    for j,s in enumerate(['SPY','QQQ']):
        d=pd.read_csv(out/f'{s}_ALL_reference/daily.csv');y=d.assign(year=pd.to_datetime(d.date).dt.year).groupby('year').return_net.apply(lambda r:((1+r).prod()-1)*100)
        ax.bar(pos+(j-.5)*.36,[y.get(k,0) for k in years],.36,label=s,color=colors[s])
    ax.set_xticks(pos,years,rotation=45);ax.axhline(0,color='black',lw=.7);ax.set(ylabel='Rendement annuel net (%)',title='Années civiles — 2026 partielle au 16 octobre');ax.legend();fig.tight_layout();fig.savefig(figs/'years.png',dpi=150);plt.close(fig)
    fig,ax=plt.subplots(figsize=(9,4.5));costs=[.01,.02,.03,.05]
    for j,s in enumerate(['SPY','QQQ']):ax.bar(np.arange(4)+(j-.5)*.36,[row(s,'ALL','reference' if c==.01 else f'cost_{c:g}')['total_return_pct'] for c in costs],.36,label=s,color=colors[s])
    ax.set_xticks(range(4),[f'{c:.2f}' for c in costs]);ax.axhline(0,color='black',lw=.7);ax.set(xlabel='Friction USD/action/côté, commissions en plus',ylabel='Rendement net ALL (%)',title='Stress de coûts fixé avant résultats');ax.legend();fig.tight_layout();fig.savefig(figs/'costs.png',dpi=150);plt.close(fig)
    fig,ax=plt.subplots(figsize=(10,4.5));variants=['reference','all_tuesdays','all_down_days'];labels=['Mardi après lundi down','Tous les mardis','Tous les jours après baisse']
    for j,s in enumerate(['SPY','QQQ']):ax.bar(np.arange(3)+(j-.5)*.36,[row(s,'ALL',v)['total_return_pct'] for v in variants],.36,label=s,color=colors[s])
    ax.set_xticks(range(3),labels);ax.axhline(0,color='black',lw=.7);ax.set(ylabel='Rendement net ALL (%)',title='Témoins descriptifs : fréquence et capitalisation différentes');ax.legend();fig.tight_layout();fig.savefig(figs/'controls.png',dpi=150);plt.close(fig)
    sections=['# Turnaround Tuesday intraday — rapport final',
      '**'+decision+'** Les deux bots Noise Area et ORB continuent leur simulation distincte ; aucun nouveau moteur installé.',
      'Étude calculée le31octobre2026, archives SIP1minute du4janvier2016 au16octobre2026, SPY/QQQ. Deux comptes séparés100000USD, risque cible1%, plafond causal1x. Résultats historiques conditionnels à la couverture. A et B ont déjà été examinées par de nombreuses études ; B n’est pas un nouvel hors-échantillon aveugle.',
      '## Hypothèse et règles',
      'Acheter le mardi si la dernière séance est un lundi dont le close RTH brut est inférieur au close de la séance précédente ; lundi férié exclu. Après le close09:30, quantité calculée puis achat à l’open09:31. Stop fixe ADR14, sortie au dernier open RTH15:59/12:59. Aucune nuit, aucun TP ou filtre RSI/IBS. Les stratégies externes détiennent souvent la nuit : cette adaptation ne reproduit pas leur performance et retire potentiellement leur principal moteur de profit.',
      'Friction adverse0.01USD/action/côté ; commission0.0035USD/action/côté, minimum0.35. Risque cible hors frais ; quantités entières décidées avant le fill. Les gaps peuvent dépasser ce risque. LONG seulement : emprunt nul et aucun dividende encaissé overnight.',
      '## Résultats des références',
      table(ref.to_dict('records'),[('symbol','ETF'),('period','Période'),('trades','Trades'),('total_return_pct','Net %'),('cagr_pct','CAGR %'),('win_rate_pct','Gagnants %'),('profit_factor','PF'),('observed_close_drawdown_pct','DD observé %'),('return_without_top3_days_pct','Sans top3 %')]),
      'A :2016-01-04–2024-04-30 ; B :2024-05-01–2026-10-16. Chaque compte de période repart de100000USD. Le DD observe les frais d’entrée, closes minute détenus et sorties ; il ne reconstruit pas tous les ticks.',
      '![Comptes conditionnels](figures/equity.png)',
      '## Coûts et risque',
      table([row(s) for s in ['SPY','QQQ']],[('symbol','ETF'),('price_move_pnl','Mouvement brut USD'),('friction_cost','Friction USD'),('commission','Commissions USD'),('borrow_fee','Emprunt USD'),('net_pnl','Net USD'),('max_actual_entry_leverage','Levier réf max'),('max_entry_fill_leverage','Levier fill max'),('max_entry_risk_pct','Risque brut max %'),('max_modeled_stop_net_risk_pct','Risque stop net modélisé max %')]),
      'Le risque net modélisé suppose une sortie au stop ou l’open d’entrée si le stop est déjà dépassé, avec deux frictions et commissions. Ce n’est pas une borne de perte : un nouveau gap ou des frais différents peut l’aggraver. MAE/MFE de prix excluent les commissions et utilisent les fills et seules minutes entièrement détenues.',
      '![Stress des coûts](figures/costs.png)',
      '## Témoins et sensibilités',
      table(df[df.variant.isin(['reference','all_tuesdays','all_down_days'])].to_dict('records'),[('symbol','ETF'),('period','Période'),('variant','Variante'),('trades','Trades'),('total_return_pct','Net %'),('profit_factor','PF')]),
      'Ces témoins modifient la fréquence, les dates d’exposition et la capitalisation ; leurs écarts ne prouvent pas un effet causal du mardi. Les autres jours, seuils0.5%/1%, entrée09:35 et retrait du filtre de couverture sont tous conservés dans la matrice84scénarios. Aucun meilleur seuil n’est promu après observation.',
      '![Témoins](figures/controls.png)',
      '## Années et concentration',
      '![Années civiles](figures/years.png)',
      table([row(s,p) for s in ['SPY','QQQ'] for p in ['ALL','A','B']],[('symbol','ETF'),('period','Période'),('return_without_top3_days_pct','Sans3meilleurs jours %'),('top3_positive_profit_share_pct','Top3/gains positifs %'),('worst_trade_usd','Pire trade USD'),('regular_time_exposure_upper_pct','Exposition RTH max %')]),
      'Le retrait des trois meilleurs jours est un diagnostic de concentration avec quantités de la trajectoire originale, pas un nouveau portefeuille recalculé. Les années2026 ne couvrent que la période arrêtée au16octobre.',
      '## Incertitude et critères avant résultats']
    ci=[]
    for s in ['SPY','QQQ']:
      for p in ['ALL','A','B']:
        u=json.loads((out/f'{s}_{p}_uncertainty.json').read_text());ci.append(dict(symbol=s,period=p,lo=u['blocks']['20']['conditional_daily_mean_ci95'][0]*10000,hi=u['blocks']['20']['conditional_daily_mean_ci95'][1]*10000))
    sections += [table(ci,[('symbol','ETF'),('period','Période'),('lo','IC95 moyen quotidien bas, bps'),('hi','IC95 haut, bps')]),
      'Bootstrap descriptif3000tirages, blocs circulaires5/20séances et clusters annuels, seed20261031. Les exclusions sont à zéro dans le chaînage mais pas des observations de cash. IC conditionnels, peu de clusters et absence de correction pour les nombreux essais antérieurs : ni preuve de significativité exploitable ni OOS aveugle.',
      table([dict(symbol=s,**{k:'passe' if v else 'échoue' for k,v in c.items()}) for s,c in checks.items()],[('symbol','ETF'),('trades_all_ge100','>=100trades ALL'),('reference_A_B_ALL_positive','A/B/ALL positifs'),('all_without_top3_positive','ALL sans top3 positif'),('A_double_friction_positive','A coûts doublés positif'),('all_block20_ci_lower_positive','IC95 blocs20 bas>0')]),
      '## Couverture et validation',
      table(ref.to_dict('records'),[('symbol','ETF'),('period','Période'),('data_excluded_sessions','Jours exclus'),('unresolved_sessions','Non résolus'),('half_session_trades','Trades demi-séance')]),
      f'Audit scalaire séparé :{audit["checks"]}contrôles,{audit["scenario_count"]}scénarios,{audit["trade_rows"]}lignes de trades et{audit["daily_rows"]}lignes quotidiennes qui se chevauchent entre scénarios. Il recalcule les calendriers/signaux, ADR, stops, quantités, fills, coûts et comptes sans appeler le moteur de stratégie. Même source et chargeur vérifié : pas un deuxième fournisseur de prix.',
      'Le principal exige une journée complète, filtre connu après coup. resolved_prefix le retire mais conserve toute donnée nécessaire au signal et aux fills ; un trou actif rend le trade non résolu et omet son PnL entier, avec coûts connus archivés. Les données historiques peuvent être révisées ; absence de quotes, liquidité, fills partiels ou latence broker dans le modèle.',
      'Les prix bruts close/close peuvent prendre un détachement de dividende pour une baisse. Aucun split renvoyé dans la requête archivée, complétude fournisseur non certifiée. Ces réserves s’ajoutent aux limites de sélection et d’exécution, elles ne sont pas effacées par un grand nombre de trades.',
      '## Décision',decision,
      'Les critères ont été figés avant le premier PnL. Aucune variante isolée positive ne remplace la référence. Les simulations Noise Area et ORB restent inchangées ; aucun passage automatique en réel.',
      '## Fichiers et reproduction',
      '[84scénarios](comparison_all.csv) · [Critères](SCREENING.json) · [Gel avant calcul](PRE_EXECUTION_PROTOCOL.json) · [Profil des données](DATA_SOURCE_PROFILE.json) · [Tests](TESTS.json) · [Audit](../../audit/AUDIT_RESULTS.json) · [Sources et différences](../../RESEARCH.md) · [Protocole](../../PROTOCOL_EXECUTION.md). Chaque dossier de scénario conserve trades, daily, unresolved, by_year et summary. Archives de marché et clés exclues de Git.']
    (out/'RAPPORT_FINAL.md').write_text('\n\n'.join(sections)+'\n',encoding='utf-8')
    print(json.dumps(screening,ensure_ascii=True))
if __name__=='__main__':main()
