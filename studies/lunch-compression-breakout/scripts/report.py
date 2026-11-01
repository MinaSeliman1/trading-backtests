"""Post-run presentation, screening and figures; no rule changes."""
from pathlib import Path
import json,sys,math
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/2026-10-31-v1';sys.path.insert(0,str(ROOT))
from lunch.data import source
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
 axes[0].set(title='Compression de midi : comptes conditionnels séparés',ylabel='Gain net cumulé (%)');axes[0].legend()
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
 parts=['# Compression de midi, cassure après 13 h — SPY et QQQ',
 'Calcul du 31 octobre 2026, historique du 4 janvier 2016 au 16 octobre 2026. Deux comptes indépendants de 100 000 USD. '+decision,
 '## Hypothèse et sources',
 'Tester une reprise après une consolidation de midi étroite : le range de 11:30–12:30 doit mesurer moins de 30 % de celui de 09:30–11:30. Attendre ensuite une nouvelle cassure avec volume après 13 h. Aucun résultat public n’est repris comme résultat du dépôt.',
 '[TOSIndicators, setup2](https://tosindicators.com/research/lunch-trading) décrit cette famille et un stop au milieu de la zone. Sa discussion ne définit pas chaque détail et change parfois de fenêtre. Notre version LONG seule, traversée par closes, première candidate consommée, ratio de volume, délai et taille sont des choix propres, figés avant PnL. Ce n’est pas une réplication certifiée. [Recherche élargie et contrepoints](../../RESEARCH.md).',
 '## Règles et mêmes frais',
 'Range matin : max high−min low, minutes 0:120. Range midi : minutes 120:180, soit 11:30–12:30 exclue. Tous les OHLCV de ce contexte doivent être valides. Ranges quantifiés à 1e−8 ; ratio strictement inférieur à 0,30, égalité insuffisante. Niveau = highMidi au cent supérieur ; stop = milieu highMidi/lowMidi au cent inférieur.',
 'Bougies 5 minutes alignées à 09:30. Première traversée terminée après 13:00 jusqu’à 14:30 incluse : close>niveau ET close de la bougie précédente<=niveau. Déjà au-dessus à 13:00 sans nouveau croisement ne suffit pas. Volume par minute de cette bougie strictement supérieur à la moyenne par minute du midi. La première candidate est consommée même si le volume est insuffisant ; aucun deuxième essai choisi.',
 'Première décision possible 13:05, achat au marché à l’open 13:06, une minute de délai après décision. Quantité entière calculée avant le fill = min(capital/close signal, budget 1 %/(close signal−stop)). Objectifs 1× et 1 % avant frais et gap ; pas de resize au prix futur. Tous les OHLCV depuis l’ouverture au signal sont requis, y compris l’attente 12:30–13:00.',
 'Une transaction LONG maximum par jour, aucun TP/trailing/break-even. Stop actif immédiatement : gap sous stop => sortie au mauvais open, y compris entrée déjà sous stop avec tous les coûts ; sinon low touchant stop => sortie au niveau. Sortie sinon à open 15:59 ; ses mèches ne sont pas détenues. Journées de 210 minutes sans entrée.',
 'Commission 0,0035 USD/action/côté, minimum 0,35 USD. Friction adverse 0,01 USD/action/côté ajoutée à l’entrée et retirée à la sortie ; stresses 0,02/0,03/0,05. Coûts comptés exactement une fois. Long seul, emprunt nul, cash sans intérêt. Financement, fiscalité, quotes/partiels/rejets et latence variable hors modèle.',
 '## Référence : A, B et ALL',
 table(ref.to_dict('records'),[('symbol','ETF'),('period','Période'),('trades','Trades'),('total_return_pct','Net %'),('cagr_pct','Annualisé %'),('profit_factor','PF'),('win_rate_pct','Gagnants %'),('observed_close_drawdown_pct','DD minute observé %')]),
 'ALL commence le 4 janvier 2016 ; A s’arrête au 30 avril 2024 ; B va du 1er mai 2024 au 16 octobre 2026. Comptes remis à 100 000 USD séparément. A/B déjà réutilisées : aucun nouvel OOS aveugle. Deux ETF corrélés, pas deux preuves indépendantes. Un faible nombre de trades reste insuffisant, même sur dix ans.',
 '![Courbes et drawdowns](figures/equity_drawdown.png)',
 '## Période récente : coûts et concentration',
 table(m[(m.period=='B')&m.variant.isin(['reference','cost_0.02'])].to_dict('records'),[('symbol','ETF'),('variant','Variante B'),('total_return_pct','Net B %'),('profit_factor','PF B'),('return_without_top3_days_pct','B sans top3 %')]),
 'Ces diagnostics ne déplacent pas les critères : top3 et IC étaient exigés sur ALL, friction doublée sur A. Une variante plus permissive comptant davantage de trades n’est pas substituée après observation à la référence trop sélective.',
 '## Coûts, pertes et risque',
 table(allref.to_dict('records'),[('symbol','ETF'),('price_move_pnl','Prix USD'),('friction_cost','Friction USD'),('commission','Commissions USD'),('net_pnl','Net USD'),('return_without_top3_days_pct','Sans top3 %'),('top3_positive_profit_share_pct','Top3/gains %'),('worst_trade_usd','Pire trade USD'),('worst_observed_mae_usd','Pire MAE prix USD'),('regular_time_exposure_pct','Temps RTH comptabilisé %')]),
 'Décomposition selon les quantités originales du compte net, pas portefeuille gratuit recalculé. Sans top3 = mettre les rendements de ces jours à zéro sans nouvelles quantités. DD aux coûts d’entrée, closes entièrement détenus et sortie nette ; pas pire tick. MAE/MFE prix incluent fills et extrêmes entièrement détenus, pas commissions ni mèches de sortie. Minute du stop intrabar en durée supérieure ; le temps enregistré ne certifie pas le temps inconnu des exclusions.',
 '![Années](figures/annual.png)',
 '## Toutes les sensibilités figées',
 table(m[m.period=='ALL'].to_dict('records'),[('symbol','ETF'),('variant','Variante'),('trades','Trades'),('total_return_pct','Net %'),('profit_factor','PF'),('observed_close_drawdown_pct','DD minute %')]),
 '14 variantes × 2 ETF × 3 périodes = 84 comptes. Compression 0,20/0,50 ; fin du midi 13:00 ; volume désactivé ou multiplicateur 1,5 ; grilles 1/15 minutes ; matin haussier ; stop au lowMidi ; resolved_prefix et stresses de coûts. Une dimension à la fois. Même fin 14:30 ; premières décisions selon la grille 13:01/13:05/13:15. Aucun nouveau gagnant promu après calcul.',
 'Comptes ALL positifs : '+('; '.join(f"{r.symbol}/{r.variant} {r.total_return_pct:+.2f} %" for r in m[(m.period=='ALL')&(m.total_return_pct>0)].itertuples()) or 'aucun')+'. Ces chiffres restent des sensibilités exploratoires, pas une sélection corrigée des essais multiples.',
 '![Sensibilités](figures/sensitivity.png)',
 '## Incertitude et critères avant PnL',
 table(ci,[('symbol','ETF'),('period','Période'),('lo','IC95 bas quotidien bps'),('hi','IC95 haut bps')]),
 'Bootstrap descriptif : 3 000 tirages seed 20261031, blocs circulaires 5/20 séances et clusters annuels. Jours exclus au zéro du chaînage. Les IC ne corrigent ni les nombreuses stratégies testées ici ni les choix de la source. La rareté des setups réduit fortement la précision.',
 table([dict(symbol=s,**{k:'passe' if v else 'échoue' for k,v in c.items()}) for s,c in checks.items()],[('symbol','ETF'),('trades_all_ge100','>=100 ALL'),('reference_A_B_ALL_positive','Références A/B/ALL positives'),('all_without_top3_positive','Sans top3 positif'),('A_double_friction_positive','A friction doublée positive'),('all_block20_ci_lower_positive','IC95 blocs20 bas>0')]),
 '## Couverture et validation',
 table(ref.to_dict('records'),[('symbol','ETF'),('period','Période'),('data_excluded_sessions','Séances inconnues/exclues'),('unresolved_sessions','Trades non résolus'),('max_entry_fill_leverage','Levier max fill'),('max_modeled_stop_net_risk_pct','Risque net stop modélisé max %')]),
 'Le contexte et le scan doivent être connus sans trous. Les highs/lows post-midi ne changent pas les niveaux et une lacune future ne modifie pas le signal passé. Ensuite complete_days impose la journée entière : filtre futur de disponibilité, performance explicitement conditionnelle, pas portefeuille continu observé. resolved_prefix retire ce filtre ; issue active inconnue omet le trade entier et archive les coûts d’entrée connus, observed_return manquant. Zéro comptable d’une exclusion n’est pas une journée de cash observée.',
 table(causes,[('symbol','ETF'),('exit_reason','Sortie'),('count','Trades')]),
 '![Sorties](figures/exit_reasons.png)',
 f'{tests["passed"]} tests passent ; oracle scalaire : {audit["checks"]:,} contrôles, {audit["executions"]} comptes, {audit["trade_rows"]:,} lignes de trades et {audit["daily_rows"]:,} lignes quotidiennes recouvrantes. {extra["numeric_checks"]} vérifications agrégées et six références bootstrap blocs5/20 reproduites. Variantes/périodes se recouvrent ; ces lignes ne sont pas indépendantes.',
 'Sources SIP/calendrier XNYS/caches/acquisitions vérifiés par empreintes. L’oracle recalcule contexte, traversée, volume et ledger sans importer le moteur/statistiques, mais partage le fournisseur et le chargeur : pas deuxième source. Les notes héritées de rapprochement dividendes concernent l’étude originale ; ici prix bruts, sans cet ajustement. Aucun split renvoyé dans l’acquisition archivée, complétude non certifiée ; prix révisables et absence de carnet/ticks. Aucun fill réel démontré.',
 '## Décision',decision+' Aucun nouveau bot ni passage au réel. Les deux simulations Noise Area et ORB restent inchangées par cette étude. Les risques/expositions diffèrent : pas de classement sur rendement brut seul.',
 '[84 comptes](comparison_all.csv) · [Critères](SCREENING.json) · [Gel avant PnL](PRE_EXECUTION_PROTOCOL.json) · [Source](DATA_SOURCE_PROFILE.json) · [Tests](TESTS.json) · [Audit](../../audit/AUDIT_RESULTS.json) · [Agrégats](../../audit/ADDITIONAL_CHECKS.json) · [Protocole](../../PROTOCOL_EXECUTION.md) · [Reproduction](../../README.md). Trades/daily/unresolved/by_year/summary par compte, features/gaps par ETF, snapshots et manifest. Archives brutes et secrets exclus de Git.']
 (OUT/'RAPPORT_FINAL.md').write_text('\n\n'.join(parts).replace('\\n','\n')+'\n',encoding='utf-8',newline='\n');print(decision)
if __name__=='__main__':main()
