"""Post-run presentation, screening and figures; no rule changes."""
from pathlib import Path
import json,sys,math
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/2026-10-31-v1';sys.path.insert(0,str(ROOT))
from atr.data import source
def table(rows,cols):
 def fmt(x,key=None):
  if x is None or isinstance(x,(float,np.floating)) and not math.isfinite(x):return '—'
  if key=='max_entry_fill_leverage' and isinstance(x,(float,np.floating)):return f'{x:.4f}'
  return f'{x:.2f}' if isinstance(x,(float,np.floating)) else str(x)
 return '| '+' | '.join(label for key,label in cols)+' |\\n|'+'|'.join('---' for x in cols)+'|\\n'+'\\n'.join('| '+' | '.join(fmt(r.get(k),k) for k,label in cols)+' |' for r in rows)
def main():
 m=pd.read_csv(OUT/'comparison_all.csv');ref=m[m.variant=='reference'];allref=ref[ref.period=='ALL'];checks={};ci=[]
 for s in ('SPY','QQQ'):
  z=ref[ref.symbol==s].set_index('period');u=json.loads((OUT/f'{s}_ALL_uncertainty.json').read_text(encoding='utf-8'))
  checks[s]=dict(trades_all_ge100=bool(z.loc['ALL','trades']>=100),reference_A_B_ALL_positive=bool((z.total_return_pct>0).all()),
   all_without_top3_positive=bool(z.loc['ALL','return_without_top3_days_pct']>0),
   A_double_friction_positive=bool(m[(m.symbol==s)&(m.period=='A')&(m.variant=='cost_0.02')].total_return_pct.iloc[0]>0),
   all_block20_ci_lower_positive=bool(u['blocks']['20']['conditional_daily_mean_ci95'][0]>0))
  for period in ('ALL','A','B'):
   u=json.loads((OUT/f'{s}_{period}_uncertainty.json').read_text(encoding='utf-8'));interval=u['blocks']['20']['conditional_daily_mean_ci95']
   ci.append(dict(symbol=s,period=period,lo=interval[0]*10000,hi=interval[1]*10000))
 passed=all(all(x.values()) for x in checks.values())
 decision='Candidat historique seulement, aucun lancement automatique.' if passed else 'Piste écartée pour un nouveau bot : les critères fixés avant les résultats ne sont pas tous satisfaits.'
 source.write_json(OUT/'SCREENING.json',dict(predeclared=True,checks=checks,all_passed=passed,decision=decision))
 figs=OUT/'figures';figs.mkdir(exist_ok=True);colors={'SPY':'#2375b5','QQQ':'#e38a22'}
 plt.rcParams.update({'font.size':10,'axes.grid':True,'grid.alpha':.2})
 fig,axes=plt.subplots(2,1,figsize=(11,7),sharex=True)
 for s in ('SPY','QQQ'):
  d=pd.read_csv(OUT/f'{s}_ALL_reference/daily.csv');dates=pd.to_datetime(d.date);eq=np.r_[100000.,d.equity]
  axes[0].plot(dates,(d.equity/100000-1)*100,label=s,color=colors[s]);axes[1].plot(dates,100*(eq/np.maximum.accumulate(eq)-1)[1:],color=colors[s])
 axes[0].set(title='Cassure ATR : référence, comptes conditionnels séparés',ylabel='Gain net cumulé (%)');axes[0].legend()
 axes[1].set(ylabel='Drawdown aux clôtures quotidiennes (%)',xlabel='Date');fig.tight_layout();fig.savefig(figs/'equity_drawdown.png',dpi=150);plt.close(fig)
 fig,axes=plt.subplots(1,2,figsize=(12,6),sharey=True);names=m.variant.drop_duplicates().tolist()
 for ax,s in zip(axes,('SPY','QQQ')):
  z=m[(m.symbol==s)&(m.period=='ALL')].set_index('variant').loc[names];ax.barh(np.arange(len(names)),z.total_return_pct,color=colors[s]);ax.axvline(0,color='black',lw=.7)
  ax.set(yticks=np.arange(len(names)),yticklabels=names,title=s,xlabel='Rendement net ALL (%)')
 axes[0].invert_yaxis();fig.suptitle('14 variantes figées avant calcul');fig.tight_layout();fig.savefig(figs/'sensitivity.png',dpi=150);plt.close(fig)
 fig,axes=plt.subplots(2,1,figsize=(11,7),sharex=True)
 for ax,s in zip(axes,('SPY','QQQ')):
  y=pd.read_csv(OUT/f'{s}_ALL_reference/by_year.csv');ax.bar(y.year,y.return_pct,color=colors[s]);ax.axhline(0,color='black',lw=.7);ax.set(title=s,ylabel='Net annuel (%)')
 axes[1].set(xticks=y.year,xlabel='Année (2026 arrêtée au 16 octobre)');fig.suptitle('Référence : années et capital recomposé');fig.tight_layout();fig.savefig(figs/'annual.png',dpi=150);plt.close(fig)
 fig,axes=plt.subplots(1,2,figsize=(12,5));causes=[]
 for ax,s in zip(axes,('SPY','QQQ')):
  t=pd.read_csv(OUT/f'{s}_ALL_reference/trades.csv');counts=t.exit_reason.value_counts();ax.barh(counts.index,counts.values,color=colors[s]);ax.set(title=s,xlabel='Nombre de trades')
  causes.extend(dict(symbol=s,exit_reason=k,count=int(v)) for k,v in counts.items())
 fig.suptitle('Référence : résolutions des sorties');fig.tight_layout();fig.savefig(figs/'exit_reasons.png',dpi=150);plt.close(fig)
 pd.DataFrame(causes).to_csv(OUT/'reference_exit_reasons.csv',index=False)
 audit=json.loads((ROOT/'audit/AUDIT_RESULTS.json').read_text(encoding='utf-8'));extra=json.loads((ROOT/'audit/ADDITIONAL_CHECKS.json').read_text(encoding='utf-8'));tests=json.loads((OUT/'TESTS.json').read_text(encoding='utf-8'))
 parts=['# Cassure ATR autour de l’ouverture — SPY et QQQ',
 'Calcul du 31 octobre 2026 ; historique du 4 janvier 2016 au 16 octobre 2026. Deux comptes indépendants de 100 000 USD. '+decision,
 '## Hypothèse et différences avec les sources',
 'Niveau fixe pour la séance : open09:30 + 0,33 × moyenne arithmétique des cinq True Ranges des séances immédiatement précédentes. Le TR inclut les gaps contre la clôture RTH précédente. Ni ATR du jour courant, ni lissage Wilder, ni moyenne d’un nombre de jours valides pris en sautant les trous.',
 '[AndrBene, dépôt primaire ETF](https://github.com/AndrBene/Volatility-Breakouts-Trading-ETFs/blob/master/readme.md) et [Albert, étude publique](https://mistakesoninvesting.substack.com/p/intraday-volatility-breakouts-an) décrivent cette famille, avec conventions différentes. Notre version LONG seulement, une tentative, confirmation par close, entrée retardée, capitalisation et plafond1× diffèrent des stop-orders LONG/SHORT et paniers externes. Aucun de leurs rendements n’est importé. [Recherche élargie et alternatives](../../RESEARCH.md).',
 '## Règle, exécution et frais',
 'Décisions sur bougies5min terminées de09:35 à15:30 New York. Acheter après la première clôture strictement au-dessus du niveau, à l’open une minute après décision : exemple09:35 →09:36. Stop fixe au cent inférieur de l’ouverture09:30, aucun TP, trailing ou break-even ; sortie sinon à l’open15:59. Demi-séances courantes exclues, demi-séances passées correctement agrégées dans l’historique.',
 'ATR normalisé à1e-8 décimal, seuil au cent supérieur. Quantité entière avant fill = min du plafond notionnel1× et du budget1 % divisé par la distance close signal–stop. Ni taille ni stop recalculés au fill futur. Gap sous stop => entrée et sortie au même open avec tous les coûts ; autre gap au stop => mauvais open observé. Sinon stop au niveau si low le touche, ordre intraminute inconnu. EOD avant ses mèches.',
 'Commission0,0035USD/action/côté, minimum0,35USD ; friction adverse0,01USD/action/côté, stresses0,02/0,03/0,05. Comptées exactement une fois via fills et commissions. LONG, donc emprunt0 ; cash sans intérêt. Risque de sizing1 % et notionnel1× sont des cibles avant frais ; gap, coûts et prix de fill peuvent augmenter l’exposition/perte. Financement, fiscalité, quotes/partiels/latence hors modèle.',
 '## Référence A, B et ALL',
 table(ref.to_dict('records'),[('symbol','ETF'),('period','Période'),('trades','Trades'),('total_return_pct','Net %'),('cagr_pct','Annualisé %'),('profit_factor','PF'),('win_rate_pct','Gagnants %'),('observed_close_drawdown_pct','DD minute observé %')]),
 'A se termine au30avril2024 ; B du1mai2024 au16octobre2026. Capitaux remis à100000USD pour chaque période, historique des features conservé strictement antérieur. A/B déjà explorées dans de nombreuses études : pas de nouvel OOS aveugle. ETF corrélés, pas deux validations indépendantes.',
 '![Courbes et drawdowns](figures/equity_drawdown.png)',
 '## Coûts, concentration et risque',
 table(allref.to_dict('records'),[('symbol','ETF'),('price_move_pnl','Mouvement de prix USD'),('friction_cost','Friction USD'),('commission','Commissions USD'),('net_pnl','Net USD'),('return_without_top3_days_pct','Sans top3 %'),('top3_positive_profit_share_pct','Top3/gains %'),('worst_trade_usd','Pire trade USD'),('worst_observed_mae_usd','Pire MAE prix USD'),('regular_time_exposure_pct','Exposition RTH max %')]),
 'La décomposition utilise les quantités de la trajectoire nette originale, pas un nouveau portefeuille sans frais redimensionné. Retrait top3 : mettre ces retours à zéro, sans nouvelles quantités. DD aux coûts d’entrée, closes entièrement détenus et sortie nette ; pas pire tick. MAE/MFE de prix incluent les fills après friction et les extrêmes entièrement détenus, hors commissions et mèches terminales. Durée intrabar en borne supérieure.',
 '![Années](figures/annual.png)',
 '## Sensibilités fixées avant PnL',
 table(m[m.period=='ALL'].to_dict('records'),[('symbol','ETF'),('variant','Variante'),('trades','Trades'),('total_return_pct','Net %'),('profit_factor','PF'),('observed_close_drawdown_pct','DD minute %')]),
 '84comptes publiés. ATR3/10, multiplicateurs0.25/0.50, grilles1/15minutes, cutoff12:00, gap_record5, no_stop et resolved_prefix sont des sensibilités, pas de nouveaux gagnants promus après observation. Les grilles gardent une fenêtre commune mais des instants de décision différents.',
 'gap_record5 utilise abs(log(openCourant/closePrécédent)) > maximum des cinq gaps immédiatement précédents ; aucun open futur et pas la formule ambiguë abs(open/close) du dépôt externe. Prix raw : dividendes non ajustés, donc effet possible sur gap et TR. no_stop conserve le stop hypothétique pour le sizing mais supprime son exécution ; les risques au stop y sont hypothétiques et ne bornent aucune perte.',
 '![Sensibilités](figures/sensitivity.png)',
 '## Incertitude et critères préétablis',
 table(ci,[('symbol','ETF'),('period','Période'),('lo','IC95 bas quotidien bps'),('hi','IC95 haut bps')]),
 'Bootstrap descriptif3000tirages seed20261031, blocs circulaires5/20séances et clusters annuels ; pas correction des recherches multiples. Jours exclus au zéro de chaînage et non cash observé. La réutilisation de A/B et les choix de nombreuses études limitent toute inférence.',
 table([dict(symbol=s,**{k:'passe' if v else 'échoue' for k,v in c.items()}) for s,c in checks.items()],[('symbol','ETF'),('trades_all_ge100','>=100 ALL'),('reference_A_B_ALL_positive','Références A/B/ALL positives'),('all_without_top3_positive','Sans top3 positif'),('A_double_friction_positive','A frais doublés positif'),('all_block20_ci_lower_positive','IC95 blocs20 bas>0')]),
 '## Couverture et vérifications',
 table(ref.to_dict('records'),[('symbol','ETF'),('period','Période'),('data_excluded_sessions','Séances inconnues/exclues'),('unresolved_sessions','Trades non résolus'),('max_entry_fill_leverage','Levier max fill'),('max_modeled_stop_net_risk_pct','Risque net stop modélisé max %')]),
 'ATR exige des séances antérieures entières valides, sans sauter un trou. Le scan exige toutes les minutes de l’ouverture à la première sélection. Une lacune future courante ne change pas le signal, mais complete_days impose ensuite la séance entière : filtre de couverture connu après coup, explicitement conditionnel. resolved_prefix retire ce filtre ; trou actif/fill inconnu omet tout le PnL et archive les coûts connus d’entrée. Pas de portefeuille continuellement observé.',
 table(causes,[('symbol','ETF'),('exit_reason','Sortie'),('count','Trades')]),
 '![Sorties](figures/exit_reasons.png)',
 f'{tests["passed"]}tests passent ; oracle scalaire :{audit["checks"]}contrôles,{audit["executions"]}comptes,{audit["trade_rows"]}lignes de trades,{audit["daily_rows"]}quotidiennes recouvrantes. {extra["numeric_checks"]}contrôles agrégés supplémentaires et6comptes bootstrap reproduits. Les lignes entre variantes/périodes se chevauchent et ne sont pas des observations indépendantes.',
 'Même source et chargeur, pas deuxième fournisseur. Hashes des acquisitions/caches/calendrier vérifiés, aucune clé/API. Données révisables ; absence de quotes, profondeur, exécution partielle, rejets broker ou ordre exact des ticks. Aucun split renvoyé par l’acquisition archivée, complétude non certifiée. Pas de comparaison directe avec les bots sur les seuls rendements : expositions/risques différents.',
 '## Décision et reproduction',decision+' Aucun nouveau bot ni passage au réel. Noise Area et ORB restent inchangés en simulation.',
 '[84comptes](comparison_all.csv) · [Critères](SCREENING.json) · [Gel avant PnL](PRE_EXECUTION_PROTOCOL.json) · [Source](DATA_SOURCE_PROFILE.json) · [Tests](TESTS.json) · [Audit](../../audit/AUDIT_RESULTS.json) · [Agrégats](../../audit/ADDITIONAL_CHECKS.json) · [Protocole](../../PROTOCOL_EXECUTION.md). Trades/daily/unresolved/by_year/summary par compte, features/gaps par ETF, snapshots et manifest. Archives brutes et secrets exclus de Git.']
 recent=m[(m.period=='B')&m.variant.isin(['reference','cost_0.02'])]
 index=parts.index('![Courbes et drawdowns](figures/equity_drawdown.png)')
 parts[index:index]=['## Fragilité de la période récente',
  table(recent.to_dict('records'),[('symbol','ETF'),('variant','Variante B'),('total_return_pct','Net B %'),('profit_factor','PF B'),('return_without_top3_days_pct','B sans top3 %')]),
  'SPY B est presque à l’équilibre et devient négatif à friction doublée. En référence, retirer les trois meilleurs jours de B rend le résultat négatif pour les DEUX ETF ; les IC95 blocs20 de moyenne quotidienne B comprennent zéro sur les deux. Les cinq critères initiaux passent car ils imposaient top3 et IC sur ALL, et coûts doublés sur A. Ils n’ont pas été déplacés après résultats. Cela reste un candidat historique à évaluer prospectivement, pas une robustesse récente démontrée.']

 text='\\n\\n'.join(parts).replace('\\n','\n')+'\n'
 replacements={'open09:30':'open 09:30','bougies5min':'bougies de 5 min','de09:35 à15:30':'de 09:35 à 15:30','exemple09:35 →09:36':'exemple 09:35 → 09:36',
  'open15:59':'open 15:59','ouverture09:30':'ouverture 09:30','à1e-8':'à 1e-8','notionnel1×':'notionnel 1×','plafond1×':'plafond 1×','budget1 %':'budget 1 %',
  'Commission0,0035USD':'Commission 0,0035 USD','minimum0,35USD':'minimum 0,35 USD','adverse0,01USD':'adverse 0,01 USD','stresses0,02/0,03/0,05':'stresses 0,02/0,03/0,05 USD','emprunt0':'emprunt 0',
  'au30avril2024':'au 30 avril 2024','du1mai2024 au16octobre2026':'du 1er mai 2024 au 16 octobre 2026','à100000USD':'à 100 000 USD',
  '84comptes':'84 comptes','ATR3/10':'ATR 3/10','multiplicateurs0.25/0.50':'multiplicateurs 0.25/0.50','grilles1/15minutes':'grilles 1/15 minutes',
  'descriptif3000tirages seed20261031':'descriptif : 3 000 tirages, seed 20261031','circulaires5/20séances':'circulaires de 5/20 séances',
  '40tests passent':'40 tests passent','et6comptes':'et 6 comptes'}
 for old,new in replacements.items():text=text.replace(old,new)
 (OUT/'RAPPORT_FINAL.md').write_text(text,encoding='utf-8',newline='\n');print(decision)
if __name__=='__main__':main()
