"""Post-run presentation; does not change financial scenarios."""
from pathlib import Path
from datetime import datetime,timezone
import sys,json,math
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/2026-10-31-v1';sys.path.insert(0,str(ROOT))
from variation.data import source
def table(rows,cols):
 def fmt(x):
  if x is None or isinstance(x,(float,np.floating)) and not math.isfinite(x):return '—'
  return f'{x:.2f}' if isinstance(x,(float,np.floating)) else str(x)
 return '| '+' | '.join(v for k,v in cols)+' |\\n|'+'|'.join('---' for _ in cols)+'|\\n'+'\\n'.join('| '+' | '.join(fmt(r.get(k)) for k,v in cols)+' |' for r in rows)
def main():
 m=pd.read_csv(OUT/'comparison_all.csv');ref=m[m.variant=='reference'];allref=ref[ref.period=='ALL']
 checks={};ci=[]
 for symbol in ('SPY','QQQ'):
  r=ref[ref.symbol==symbol].set_index('period')
  u=json.loads((OUT/f'{symbol}_ALL_uncertainty.json').read_text());lo=u['blocks']['20']['conditional_daily_mean_ci95'][0]
  checks[symbol]=dict(trades_all_ge100=bool(r.loc['ALL','trades']>=100),reference_A_B_ALL_positive=bool((r.total_return_pct>0).all()),
    all_without_top3_positive=bool(r.loc['ALL','return_without_top3_days_pct']>0),
    A_double_friction_positive=bool(m[(m.symbol==symbol)&(m.period=='A')&(m.variant=='cost_0.02')].total_return_pct.iloc[0]>0),
    all_block20_ci_lower_positive=bool(lo>0))
  for period in ('ALL','A','B'):
   u=json.loads((OUT/f'{symbol}_{period}_uncertainty.json').read_text())
   ci.append(dict(symbol=symbol,period=period,lo=u['blocks']['20']['conditional_daily_mean_ci95'][0]*10000,hi=u['blocks']['20']['conditional_daily_mean_ci95'][1]*10000))
 passed=all(all(x.values()) for x in checks.values())
 decision='Candidat historique seulement ; aucun nouveau bot automatique.' if passed else 'Piste écartée pour un nouveau bot : au moins un critère fixé avant les résultats échoue.'
 source.write_json(OUT/'SCREENING.json',dict(predeclared=True,checks=checks,all_passed=passed,decision=decision))
 figdir=OUT/'figures';figdir.mkdir(exist_ok=True);plt.rcParams.update({'font.size':10,'axes.grid':True,'grid.alpha':.2})
 colors={'SPY':'#2375b5','QQQ':'#e38a22'}
 fig,axes=plt.subplots(2,1,figsize=(11,7),sharex=True)
 for symbol in ('SPY','QQQ'):
  d=pd.read_csv(OUT/f'{symbol}_ALL_reference/daily.csv');dates=pd.to_datetime(d.date)
  axes[0].plot(dates,(d.equity/100000-1)*100,label=symbol,color=colors[symbol])
  eq=np.r_[100000.,d.equity];dd=100*(eq/np.maximum.accumulate(eq)-1)
  axes[1].plot(dates,dd[1:],label=symbol,color=colors[symbol])
 axes[0].set(title='Référence : comptes historiques conditionnels séparés',ylabel='Gain net cumulé (%)');axes[0].legend()
 axes[1].set(ylabel='Drawdown aux clôtures (%)',xlabel='Date');fig.tight_layout();fig.savefig(figdir/'equity_drawdown.png',dpi=150);plt.close(fig)
 fig,axes=plt.subplots(1,2,figsize=(12,6),sharey=True)
 names=m.variant.drop_duplicates().tolist()
 for ax,symbol in zip(axes,('SPY','QQQ')):
  z=m[(m.symbol==symbol)&(m.period=='ALL')].set_index('variant').loc[names]
  ax.barh(np.arange(len(names)),z.total_return_pct,color=colors[symbol]);ax.axvline(0,color='black',lw=.7)
  ax.set(yticks=np.arange(len(names)),yticklabels=names,title=symbol,xlabel='Rendement net ALL (%)');ax.invert_yaxis()
 fig.suptitle('14 variantes fixées avant calcul — exposition différente des témoins');fig.tight_layout();fig.savefig(figdir/'sensitivity.png',dpi=150);plt.close(fig)
 fig,axes=plt.subplots(2,1,figsize=(11,7),sharex=True)
 for ax,symbol in zip(axes,('SPY','QQQ')):
  y=pd.read_csv(OUT/f'{symbol}_ALL_reference/by_year.csv');ax.bar(y.year,y.return_pct,color=colors[symbol]);ax.axhline(0,color='black',lw=.7);ax.set(title=symbol,ylabel='Rendement annuel net (%)')
 axes[1].set(xlabel='Année (2026 arrêtée au 16 octobre)',xticks=y.year);fig.suptitle('Référence : années calendaires, capital recomposé');fig.tight_layout();fig.savefig(figdir/'annual.png',dpi=150);plt.close(fig)
 fig,axes=plt.subplots(2,1,figsize=(11,7),sharex=True)
 for ax,symbol in zip(axes,('SPY','QQQ')):
  f=pd.read_csv(OUT/f'{symbol}_reference_features.csv');f=f[f.date>='2024-01-01'];dates=pd.to_datetime(f.date)
  ax.plot(dates,f.score,color=colors[symbol],lw=.7,label='Score matinal')
  ax.plot(dates,f.threshold,color='black',lw=1,label='Seuil passé q90');ax.set(title=symbol,ylabel='L / racine des carrés');ax.legend(loc='lower left')
 fig.suptitle('Diagnostic du signal — seuil sans la séance courante');fig.tight_layout();fig.savefig(figdir/'signal.png',dpi=150);plt.close(fig)
 audit=json.loads((ROOT/'audit/AUDIT_RESULTS.json').read_text());additional=json.loads((ROOT/'audit/ADDITIONAL_CHECKS.json').read_text());tests=json.loads((OUT/'TESTS.json').read_text())
 sections=['# Momentum matinal normalisé par la variation — résultats SPY/QQQ','Calcul du31octobre2026, historique2016-01-04–2026-10-16. Deux comptes indépendants100000USD, LONG seulement, plafond causal1x hors frais. '+decision,
 '## Règle et recherche',
 'Le score de première heure est L/V : log(close10:29/open09:30), divisé par la racine de la somme des retours logarithmiques2minutes au carré. Achat si score au-dessus du quantile90% des matinées antérieures admissibles, minimum252. Signal10:30NewYork, quantité floor(capital/close10:29), fill10:31open, sortie15:59open, aucune nuit ni stop. Le ratio n’est ni Sharpe ni prévision en sigmas. Tous les OHLCV du matin sont exigés ; seuls les créneaux échantillonnés entrent dans V.',
 '[SharpeTwo, source primaire](https://sharpetwo.com/research/spys-quiet-rally-what-happens-after-a-big-move-with-little-volatility) propose cette famille sur quote-midpoints et panier large. Notre adaptation ne réplique ni ce panier ni les performances gross publiées. Différences matérielles : tradebarsSIP, SPY/QQQ séparés, quantile expanding précisément défini ici et sortie15:59open. [Recherche Web lisible, alternatives et statut des accès](../../RESEARCH_READABLE.md).',
 '## Frais et risque',
 'Commission0.0035USD/action/côté, minimum0.35, plus friction adverse0.01USD/action/côté ; doublement et stress0.03/0.05 testés. Friction incluse aux fills une seule fois ; LONG donc emprunt0. Cash sans intérêt. Hypothèses communes aux études antérieures, pas un tarif broker certifié.',
 'Le notionnel est1x avant frais, sans stop ni cible de perte1%. Un gap au fill peut dépasser1x ; pas de redimensionnement rétrospectif. Les risques et l’exposition diffèrent des bots Noise Area4x/ORB1x avec stops. Ne pas classer ces stratégies sur le seul rendement brut.',
 '## Référence : comptes séparés A, B et ALL',
 table(ref.to_dict('records'),[('symbol','ETF'),('period','Période'),('trades','Trades'),('total_return_pct','Net %'),('cagr_pct','CAGR %'),('profit_factor','PF'),('win_rate_pct','Gagnants %'),('observed_close_drawdown_pct','DD minute observé %'),('max_daily_close_drawdown_pct','DD clôture %')]),
 'A va jusqu’au30avril2024 ; B du1mai2024 au16octobre2026. Chaque compte repart de100000. B et A ont déjà servi aux recherches précédentes : aucune nouvelle période OOS aveugle. Le warmup initial explique de la non-exposition en2016 ; aucune donnée antérieure inventée.',
 '![Courbes et drawdowns](figures/equity_drawdown.png)',
 '## Décomposition des coûts, pertes et concentration',
 table(allref.to_dict('records'),[('symbol','ETF'),('price_move_pnl','Mouvement de prix USD'),('friction_cost','Friction USD'),('commission','Commission USD'),('borrow_fee','Emprunt USD'),('net_pnl','Net USD'),('return_without_top3_days_pct','Sans top3 %'),('top3_positive_profit_share_pct','Top3/gains %'),('worst_trade_usd','Pire trade USD'),('worst_observed_mae_usd','Pire MAE prix USD'),('regular_time_exposure_pct','Exposition RTH %')]),
 'Sans top3 signifie mise à zéro de ces retours sur la trajectoire initiale, sans recalcul des quantités ultérieures. MAE/MFE de prix utilisent les fills après friction et les extrêmes entièrement détenus, hors commissions. DD aux marks d’entrée, closes minute détenus et sortie nette ; ni pire tick ni garantie de perte maximale.',
 '![Années](figures/annual.png)',
 '## Sensibilités et témoins',
 table(m[m.period=='ALL'].to_dict('records'),[('symbol','ETF'),('variant','Variante'),('trades','Trades'),('total_return_pct','Net %'),('profit_factor','PF'),('observed_close_drawdown_pct','DD minute %')]),
 'Les84comptes sont publiés, pas une sélection des gagnants. raw_momentum remplace le ratio par L sur le même panel ; always_long garde le warmup/panel et achète sans seuil. Fréquences et capitalisations différentes : aucune attribution causale isolée au filtre. noon observe jusqu’à11:59 et entre12:01. exit_close utilise un proxy SIP final, pas un fill officiel d’enchère vérifié.',
 '![Sensibilités](figures/sensitivity.png)',
 '## Incertitude et présélection',
 table(ci,[('symbol','ETF'),('period','Période'),('lo','IC95 bas moyenne quotidienne bps'),('hi','IC95 haut bps')]),
 'Bootstrap descriptif3000tirages seed20261031, blocs circulaires5/20séances, clusters annuels. Exclusions au zéro de chaînage, pas des rendements cash observés. Pas de correction des multiples essais ; les ETF corrélés ne sont pas deux validations indépendantes.',
 table([dict(symbol=s,**{k:'passe' if v else 'échoue' for k,v in check.items()}) for s,check in checks.items()],[('symbol','ETF'),('trades_all_ge100','>=100 ALL'),('reference_A_B_ALL_positive','A/B/ALL positifs'),('all_without_top3_positive','Sans top3 positif'),('A_double_friction_positive','A frais doublés positif'),('all_block20_ci_lower_positive','IC95 blocs20 bas>0')]),
 '## Données, exclusions et validation',
 table(ref.to_dict('records'),[('symbol','ETF'),('period','Période'),('data_excluded_sessions','Séances inconnues/exclues'),('unresolved_sessions','Trades non résolus'),('sessions','Séances calendaires')]),
 'Principal complete_days filtre la journée entière après un signal, donc utilise une condition de couverture connue après coup. resolved_prefix retire ce filtre mais exige matin et trajet détenu observables. Un trou actif/fill inconnu omet tout le trade et archive les coûts connus ; cela ne constitue pas un portefeuille continuellement observé. Les motifs quotidiens et gaps sont exportés. Demi-séances : inactivité connue. Une lacune après-midi historique n’efface pas un matin valide de calibration.',
 f'{tests["passed"]}tests passent. Oracle scalaire séparé :{audit["checks"]}contrôles,{audit["executions"]}comptes,{audit["trade_rows"]}lignes de trades,{audit["daily_rows"]}lignes quotidiennes qui se chevauchent entre variantes/périodes. Il recalcule grilles, quantiles, signaux, fills, frais, ledger et marks. {additional["numeric_checks"]}contrôles agrégés supplémentaires et6comptes bootstrap vérifiés.',
 'Même fournisseur/cache/chargeur : pas une seconde source indépendante. Hashes des acquisitions et calendrier XNYS vérifiés, aucune clé/API. Sans quotes, liquidité, fills partiels, rejets broker ou latence réelle ; barres révisables, gross1x sans fraisfinancement/impôts/abonnement. Les comparaisons avec buy-and-hold de long terme ne sont pas couvertes par ces témoins intraday.',
 '![Signal](figures/signal.png)',
 '## Décision et reproduction',decision+' Les deux simulations QQQ existantes restent inchangées ; aucun nouveau bot ni passage au réel.',
 '[Comparaison84comptes](comparison_all.csv) · [Gel avant PnL](PRE_EXECUTION_PROTOCOL.json) · [Critères](SCREENING.json) · [Source](DATA_SOURCE_PROFILE.json) · [Tests](TESTS.json) · [Audit](../../audit/AUDIT_RESULTS.json) · [Contrôles supplémentaires](../../audit/ADDITIONAL_CHECKS.json) · [Protocole](../../PROTOCOL_EXECUTION.md). Chaque compte : trades/daily/unresolved/by_year/summary ; features et gaps par ETF ; snapshots financiers/dépendances et manifest final. Données brutes et secrets exclus de Git.']
 text='\\n\\n'.join(sections).replace('\\n','\n')+'\n'
 replacements={
 'Calcul du31octobre2026':'Calcul du 31 octobre 2026','indépendants100000USD':'indépendants de 100 000 USD','causal1x':'causal de 1×',
 'logarithmiques2minutes':'logarithmiques sur 2 minutes','quantile90%':'quantile 90 %','minimum252':'minimum 252',
 'Signal10:30NewYork':'Signal à 10:30 New York','fill10:31open':'entrée à l’open de 10:31','sortie15:59open':'sortie à l’open de 15:59',
 'Commission0.0035USD':'Commission 0,0035 USD','minimum0.35':'minimum 0,35 USD','adverse0.01USD':'adverse 0,01 USD',
 'stress0.03/0.05':'stress 0,03/0,05 USD','emprunt0':'emprunt 0','est1x':'est de 1×','perte1%':'perte 1 %','dépasser1x':'dépasser 1×',
 'Area4x/ORB1x':'Area 4×/ORB 1×','jusqu’au30avril2024':'jusqu’au 30 avril 2024','du1mai2024 au16octobre2026':'du 1er mai 2024 au 16 octobre 2026',
 'de100000':'de 100 000 USD','Les84comptes':'Les 84 comptes','jusqu’à11:59':'jusqu’à 11:59','entre12:01':'entre à 12:01',
 'descriptif3000tirages seed20261031':'descriptif : 3 000 tirages, seed 20261031','circulaires5/20séances':'circulaires de 5/20 séances',
 'gross1x sans fraisfinancement':'notionnel 1× sans frais de financement','Comparaison84comptes':'Comparaison des 84 comptes',
 '42tests passent':'42 tests passent','5437956contrôles,84comptes,23612lignes de trades,151928lignes quotidiennes':'5 437 956 contrôles, 84 comptes, 23 612 lignes de trades, 151 928 lignes quotidiennes',
 '864contrôles agrégés supplémentaires et6comptes':'864 contrôles agrégés supplémentaires et 6 comptes'}
 for old,new in replacements.items():text=text.replace(old,new)
 (OUT/'RAPPORT_FINAL.md').write_text(text,encoding='utf-8',newline='\n')
 print(decision)
if __name__=='__main__':main()
