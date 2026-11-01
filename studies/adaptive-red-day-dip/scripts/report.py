"""Post-run presentation, screening and figures; no rule changes."""
from pathlib import Path
import json,sys,math
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/2026-10-31-v1';sys.path.insert(0,str(ROOT))
from dip.data import source
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
 axes[0].set(title='Repli estimé sur jours rouges : comptes conditionnels séparés',ylabel='Gain net cumulé (%)');axes[0].legend()
 axes[1].set(ylabel='Drawdown aux clôtures quotidiennes (%)',xlabel='Date');fig.tight_layout();fig.savefig(figs/'equity_drawdown.png',dpi=150);plt.close(fig)
 fig,axes=plt.subplots(1,2,figsize=(12,6),sharey=True,sharex=True);names=m.variant.drop_duplicates().tolist()
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
 parts=['# Repli estimé sur les séances rouges — SPY et QQQ',
 'Calcul le 31 octobre 2026 (date locale), historique du 4 janvier 2016 au 16 octobre 2026. Deux comptes indépendants de 100 000 USD. '+decision,
 '## Hypothèse et sources',
 'Chaque matin, estimer la profondeur du repli par la moyenne des max(Open−Close,0) des 21 séances précédentes : les jours verts comptent zéro. Le niveau fixe est ouverture du jour moins cette moyenne, arrondi au cent inférieur. Ce n’est ni Open−Low, ni une moyenne conditionnée aux seuls jours rouges, ni une information du jour courant.',
 '[Daniel Peer, code primaire](https://raw.githubusercontent.com/daniel100peer/stocks_master/main/strategies/dip_buying_clean/quick_dip_check.py) est la source de cette hypothèse. Son code utilise des OHLC quotidiens pour supposer un ordre limite rempli au niveau dès que le low le touche, des fractions d’actions et un capital fixe sans nos coûts. Notre adaptation confirme le repli puis utilise une entrée au marché différée, des minutes, un stop et un capital recomposé. Ses chiffres ne sont pas nos résultats. [Recherche élargie et alternatives](../../RESEARCH.md).',
 '## Règles et mêmes frais',
 'Première clôture de 5 minutes strictement sous le niveau, décisions de 09:35 à 15:30 New York. Entrée LONG à l’open une minute après décision : 09:35 → 09:36. Le rebond au-dessus du niveau n’annule pas l’entrée au marché. Si la première clôture candidate est déjà sous/égale au stop, aucune transaction ce jour et aucune seconde candidate sélectionnée.',
 'Stop fixe = niveau − moyenne des ranges High−Low des 14 séances immédiatement précédentes. Moyennes quantifiées à 1e−8 et niveaux arrondis au cent inférieur avant les comparaisons. Pas de TP, de trailing, de break-even ou d’overnight. Sortie sinon à l’open 15:59 ; ses mèches ne sont pas détenues. Demi-séances passées incluses à leur vraie longueur, journée actuelle de 210 minutes sans entrée.',
 'Quantité entière avant fill = min(capital/close signal, budget 1 %/(close signal−stop)). Objectif 1× avant fill et frais ; gap et coûts peuvent dépasser ce plafond ou le budget. Aucun redimensionnement au prix futur. Gap sous stop : sortie au mauvais open, y compris entrée déjà sous le stop avec tous les frais. Sinon low touchant le stop : sortie au niveau, séquence exacte intraminute inconnue.',
 'Commission 0,0035 USD/action/côté, minimum 0,35 USD ; friction adverse 0,01 USD/action/côté ajoutée à l’entrée et retirée à la sortie, stresses 0,02/0,03/0,05. Comptées une seule fois. LONG donc emprunt nul ; trésorerie non rémunérée. Pas de fiscalité, financement, carnet, partiels ni latence variable.',
 '## Résultats de référence',
 table(ref.to_dict('records'),[('symbol','ETF'),('period','Période'),('trades','Trades'),('total_return_pct','Net %'),('cagr_pct','Annualisé %'),('profit_factor','PF'),('win_rate_pct','Gagnants %'),('observed_close_drawdown_pct','DD minute observé %')]),
 'ALL couvre 2016–16/10/2026 ; A s’arrête au 30/04/2024 et B couvre 01/05/2024–16/10/2026. Chaque compte/période repart de 100 000 USD, avec historique antérieur des caractéristiques conservé. A et B déjà réutilisées dans de nombreuses études : aucun nouvel OOS aveugle. SPY et QQQ sont corrélés.',
 '![Courbes et drawdowns](figures/equity_drawdown.png)',
 '## Fragilité récente : coût et concentration',
 table(m[(m.period=='B')&m.variant.isin(['reference','cost_0.02'])].to_dict('records'),[('symbol','ETF'),('variant','Variante B'),('total_return_pct','Net B %'),('profit_factor','PF B'),('return_without_top3_days_pct','B sans top3 %')]),
 'Ces diagnostics sont publiés sans déplacer les critères préétablis, qui imposaient top3 et IC sur ALL et friction doublée sur A. Une variante positive isolée ne remplace pas la référence.',
 '## Décomposition, pertes et risque',
 table(allref.to_dict('records'),[('symbol','ETF'),('price_move_pnl','Prix USD'),('friction_cost','Friction USD'),('commission','Commissions USD'),('net_pnl','Net USD'),('return_without_top3_days_pct','Sans top3 %'),('top3_positive_profit_share_pct','Top3/gains %'),('worst_trade_usd','Pire trade USD'),('worst_observed_mae_usd','Pire MAE prix USD'),('regular_time_exposure_pct','Temps RTH comptabilisé %')]),
 'Décomposition avec les quantités de la trajectoire nette ; pas un portefeuille gratuit recalculé. Sans top3 = rendements de ces journées mis à zéro, sans nouvelles quantités. DD aux frais d’entrée, clôtures entièrement détenues et sortie nette, pas au pire tick. MAE/MFE prix incluent fills et extrêmes des seules minutes entièrement détenues, hors commissions et mèches terminales. Durée du stop intrabar : borne supérieure d’une minute.',
 '![Années](figures/annual.png)',
 '## Toutes les sensibilités prédéclarées',
 table(m[m.period=='ALL'].to_dict('records'),[('symbol','ETF'),('variant','Variante'),('trades','Trades'),('total_return_pct','Net %'),('profit_factor','PF'),('observed_close_drawdown_pct','DD minute %')]),
 '14 variantes × 2 ETF × 3 périodes = 84 comptes. Fenêtres 10/42, profondeur ×0,5/1,5, bougies 1/15 min, cutoff 12:00, red2, no_stop, resolved_prefix et trois stresses de coûts. red2 exige les deux séances précédentes close<open ; le compteur est plafonné à deux. no_stop conserve le stop notionnel de sizing mais ne borne pas les pertes. Les grilles de décision gardent la même fenêtre commune. Aucune variante promue après calcul.',
 'Comptes ALL positifs parmi les variantes : '+('; '.join(f"{r.symbol}/{r.variant} {r.total_return_pct:+.2f} %" for r in m[(m.period=='ALL')&(m.total_return_pct>0)].itertuples()) or 'aucun')+'. Ces résultats ne changent pas les critères ni la référence.',
 '![Sensibilités](figures/sensitivity.png)',
 '## Incertitude et critères fixés avant PnL',
 table(ci,[('symbol','ETF'),('period','Période'),('lo','IC95 bas quotidien bps'),('hi','IC95 haut bps')]),
 'Bootstrap descriptif : 3 000 tirages seed 20261031, blocs circulaires 5/20 séances et clusters annuels. Ces IC ne corrigent ni les nombreux essais du dépôt ni la sélection de la source ; aucune garantie de rentabilité. Les jours exclus restent au zéro comptable du chaînage.',
 table([dict(symbol=s,**{k:'passe' if v else 'échoue' for k,v in c.items()}) for s,c in checks.items()],[('symbol','ETF'),('trades_all_ge100','>=100 ALL'),('reference_A_B_ALL_positive','Références A/B/ALL positives'),('all_without_top3_positive','Sans top3 positif'),('A_double_friction_positive','A frais doublés positif'),('all_block20_ci_lower_positive','IC95 blocs20 bas>0')]),
 '## Couverture et vérifications',
 table(ref.to_dict('records'),[('symbol','ETF'),('period','Période'),('data_excluded_sessions','Séances inconnues/exclues'),('unresolved_sessions','Trades non résolus'),('max_entry_fill_leverage','Levier max fill'),('max_modeled_stop_net_risk_pct','Risque net stop modélisé max %')]),
 'Premières et dernières transactions de référence effectivement résolues : '+('; '.join(f"{s} {pd.read_csv(OUT/f'{s}_ALL_reference/trades.csv').date.min()} au {pd.read_csv(OUT/f'{s}_ALL_reference/trades.csv').date.max()}" for s in ('SPY','QQQ')))+'. Le compte commence au 4 janvier 2016, y compris warmup et exclusions ; aucune exposition inventée avant ces transactions.',
 'Les fenêtres d’historique exigent toutes les séances consécutives valides ; aucun trou sauté. Le scan exige toutes les minutes depuis l’ouverture jusqu’au premier signal. Une lacune de l’après-midi courant n’altère pas le signal matinal. Ensuite complete_days impose la validité de toute la journée courante : c’est un filtre futur de disponibilité, et les performances sont explicitement conditionnelles, pas un portefeuille continu observé.',
 'resolved_prefix retire ce filtre de journée entière. Lacune dans le scan ou la trajectoire active : trade entier omis si issue inconnue, observed_return manquant, frais d’entrée connus archivés dans unresolved.csv. Le zéro de chaînage d’une exclusion ne signifie pas journée de cash réellement observée. Une minute de délai non détenue peut manquer sans empêcher une exécution autrement résolue.',
 table(causes,[('symbol','ETF'),('exit_reason','Sortie'),('count','Trades')]),
 '![Sorties](figures/exit_reasons.png)',
 f'{tests["passed"]} tests passent. Oracle scalaire : {audit["checks"]:,} contrôles, {audit["executions"]} comptes, {audit["trade_rows"]:,} lignes de trades et {audit["daily_rows"]:,} lignes quotidiennes recouvrantes. {extra["numeric_checks"]} vérifications agrégées et six comptes bootstrap blocs 5/20 reproduits. Les variantes et périodes se recouvrent, ces lignes ne sont pas indépendantes.',
 'Sources SIP/calendrier XNYS/caches/acquisitions vérifiés par empreintes. L’oracle recalcule les caractéristiques et ledgers sans importer le moteur, mais partage le chargeur et le fournisseur : pas une deuxième source. Les notes de rapprochement dividendes héritées du profil concernent l’étude originale ; ici corps et ranges utilisent les prix bruts, sans cet ajustement. Aucun split renvoyé dans l’acquisition archivée, complétude non certifiée. Prix révisables, absence de quotes/depth/partiels/rejets, pas d’exécution réelle démontrée.',
 '## Décision et reproduction',decision+' Aucun nouveau bot ni passage au réel. Les simulations QQQ Noise Area et ORB ne sont pas modifiées par cette étude. Risques et leviers différents : ne pas classer les stratégies sur les seuls rendements bruts.',
 '[84 comptes](comparison_all.csv) · [Critères](SCREENING.json) · [Gel avant PnL](PRE_EXECUTION_PROTOCOL.json) · [Source](DATA_SOURCE_PROFILE.json) · [Tests](TESTS.json) · [Audit](../../audit/AUDIT_RESULTS.json) · [Agrégats](../../audit/ADDITIONAL_CHECKS.json) · [Protocole](../../PROTOCOL_EXECUTION.md) · [Reproduction](../../README.md). Trades/daily/unresolved/by_year/summary par compte, caractéristiques/gaps par ETF, snapshots et manifest. Archives brutes et secrets exclus de Git.']
 (OUT/'RAPPORT_FINAL.md').write_text('\n\n'.join(parts).replace('\\n','\n')+'\n',encoding='utf-8',newline='\n');print(decision)
if __name__=='__main__':main()
