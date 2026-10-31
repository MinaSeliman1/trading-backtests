"""Post-run presentation, screening and figures; no rule changes."""
from pathlib import Path
import json,sys,math
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/2026-10-31-v1';sys.path.insert(0,str(ROOT))
from bb.data import source
def table(rows,cols):
 def fmt(x):
  if x is None or isinstance(x,(float,np.floating)) and not math.isfinite(x):return '—'
  return f'{x:.2f}' if isinstance(x,(float,np.floating)) else str(x)
 return '| '+' | '.join(label for key,label in cols)+' |\\n|'+'|'.join('---' for x in cols)+'|\\n'+'\\n'.join('| '+' | '.join(fmt(r.get(k)) for k,label in cols)+' |' for r in rows)
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
 axes[0].set(title='Bollinger : référence, comptes conditionnels séparés',ylabel='Gain net cumulé (%)');axes[0].legend()
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
 parts=['# Bollinger : réintégration intraday — SPY et QQQ',
 'Calcul du 31 octobre 2026. Historique du 4 janvier 2016 au 16 octobre 2026. Deux comptes indépendants de 100 000 USD. '+decision,
 '## Hypothèse, sources et règles',
 'Barres RTH de 5 minutes, SMA 20 et écart-type population, bandes à ±2 écarts-types. Entre 11:15 et 14:30 New York, attendre un close sous la bande basse puis un close revenu au-dessus. Choisir le premier setup de géométrie valide. Achat à l’open une minute après la décision, stop sous les deux dernières bougies, objectif à la moyenne figée. Une tentative par jour, aucune nuit, sortie au plus tard à l’open de 15:59.',
 '[Bollinger, règles primaires](https://www.bollingerbands.com/bollinger-band-rules) et [StockCharts, formules](https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-overlays/bollinger-bands) décrivent les bandes sans garantir un retour à la moyenne. [Recherche et alternatives](../../RESEARCH.md) : dépôts QQQ/SPY, forum, étude académique repérée mais texte inaccessible, exemple de réintégration sur futures. Aucune performance externe n’est importée. Notre intraday avec reset quotidien et stop diffère matériellement des versions swing et multi-indicateurs.',
 '## Exécution, coûts et risque',
 'Taille entière décidée au close du signal : minimum du plafond notionnel 1× et du budget 1 % divisé par la distance au stop. Stop et TP figés avant le fill. TP moyen normalisé à 1e-8 puis arrondi au cent inférieur ; stop au cent inférieur des deux plus bas moins 0,01 USD. Aucune garantie de perte maximale de 1 % : gap, friction et commissions peuvent augmenter le risque réalisé.',
 'Commission de 0,0035 USD/action/côté, minimum 0,35 USD, friction adverse de 0,01 USD/action/côté, comptées une seule fois. Stress à 0,02/0,03/0,05 USD. LONG uniquement, emprunt nul, cash sans intérêt. Hypothèses communes aux autres études, sans prétendre certifier un tarif ou fill broker.',
 'Gap sous stop : sortie à l’open observé ; gap au-dessus du TP : sortie à cet open, même dès l’entrée avec aller-retour de coûts. Stop et TP dans la même minute : stop prioritaire, ambiguïté exportée. Aucun prix de clôture de signal utilisé comme fill. Les mèches de la minute terminale ne sont pas ajoutées artificiellement aux excursions.',
 '## Référence : A, B et ALL',
 table(ref.to_dict('records'),[('symbol','ETF'),('period','Période'),('trades','Trades'),('total_return_pct','Net %'),('cagr_pct','Annualisé %'),('profit_factor','PF'),('win_rate_pct','Gagnants %'),('observed_close_drawdown_pct','DD minute observé %')]),
 'A se termine le 30 avril 2024 ; B couvre le 1er mai 2024 au 16 octobre 2026. Comptes séparés de 100 000 USD pour chaque période. Les bandes n’utilisent aucun jour antérieur. A/B sont déjà réutilisées dans de nombreuses recherches : aucun nouvel OOS aveugle et pas deux validations indépendantes sur des ETF corrélés.',
 '![Courbes et drawdowns](figures/equity_drawdown.png)',
 '## Coûts, pertes et concentration',
 table(allref.to_dict('records'),[('symbol','ETF'),('price_move_pnl','Mouvement de prix USD'),('friction_cost','Friction USD'),('commission','Commissions USD'),('net_pnl','Net USD'),('return_without_top3_days_pct','Sans top3 %'),('top3_positive_profit_share_pct','Top3/gains %'),('worst_trade_usd','Pire trade USD'),('worst_observed_mae_usd','Pire MAE prix USD'),('regular_time_exposure_pct','Exposition RTH max %')]),
 'Le retrait des trois meilleurs jours met leurs retours à zéro sur la trajectoire initiale ; il ne redimensionne pas les quantités ultérieures. MAE/MFE incluent les deux fills après friction et les seules minutes entièrement détenues, hors commissions. L’exposition inclut une borne supérieure pour la minute de sortie intrabar. Le DD aux closes minute n’est pas le pire tick.',
 '![Années](figures/annual.png)',
 '## Sensibilités préétablies',
 table(m[m.period=='ALL'].to_dict('records'),[('symbol','ETF'),('variant','Variante'),('trades','Trades'),('total_return_pct','Net %'),('profit_factor','PF'),('observed_close_drawdown_pct','DD minute %')]),
 'Les 84 comptes sont publiés. Les variantes changent largeur, fenêtre, cible 1R, horaire, confirmation, délai et couverture. bars10lookback10 garde un horizon nominal de 100 minutes mais change la grille et les premières décisions. outside_touch achète sous la bande sans attendre le retour. delay_0 entre immédiatement à l’open suivant et suppose une exécution plus optimiste. Différences de fréquence, géométrie et capitalisation : aucun contraste causal isolé.',
 '![Sensibilités](figures/sensitivity.png)',
 '## Incertitude et critères fixés avant résultats',
 table(ci,[('symbol','ETF'),('period','Période'),('lo','IC95 bas moyen quotidien bps'),('hi','IC95 haut bps')]),
 'Bootstrap descriptif de 3 000 tirages, seed 20261031, blocs circulaires de 5/20 séances et clusters annuels. Les exclusions restent à zéro de chaînage, pas des observations de cash. Pas de correction des essais multiples ; les rendements conditionnels ne prouvent pas un avantage prospectif.',
 table([dict(symbol=s,**{k:'passe' if v else 'échoue' for k,v in c.items()}) for s,c in checks.items()],[('symbol','ETF'),('trades_all_ge100','>=100 ALL'),('reference_A_B_ALL_positive','A/B/ALL positifs'),('all_without_top3_positive','Sans top3 positif'),('A_double_friction_positive','A frais doublés positif'),('all_block20_ci_lower_positive','IC95 blocs20 bas>0')]),
 '## Couverture, sorties et vérifications',
 table(ref.to_dict('records'),[('symbol','ETF'),('period','Période'),('data_excluded_sessions','Séances exclues/inconnues'),('unresolved_sessions','Trades non résolus'),('ambiguous_trades','Minutes stop+TP'),('max_entry_fill_leverage','Levier max au fill'),('max_modeled_stop_net_risk_pct','Risque net stop modélisé max %')]),
 'complete_days impose une séance complète après sélection : condition future de couverture explicitement reconnue. resolved_prefix retire ce filtre et exige le scan causal et le trajet jusqu’à sortie. Un trou avant le premier signal interdit de choisir un signal ultérieur. Trou actif/fill inconnu : PnL entier omis avec coûts d’entrée connus archivés. Cela ne constitue pas un portefeuille continuellement observé.',
 table(causes,[('symbol','ETF'),('exit_reason','Sortie'),('count','Trades')]),
 '![Sorties](figures/exit_reasons.png)',
 f'{tests["passed"]} tests passent. Rejeu scalaire indépendant : {audit["checks"]:,} contrôles, {audit["executions"]} comptes, {audit["trade_rows"]:,} lignes de trades et {audit["daily_rows"]:,} lignes quotidiennes recouvrantes. {extra["numeric_checks"]} contrôles agrégés supplémentaires et six comptes bootstrap vérifiés. Ces lignes ne sont pas des observations indépendantes.',
 'Même fournisseur et chargeur vérifié, pas une seconde source. Hashes des acquisitions/caches/calendrier vérifiés, aucune clé ni API. Historique révisable ; absence de quotes, profondeur, fills partiels, rejets broker et séquence intraminute. Financement, fiscalité et frais réglementaires distincts non ajoutés. Les risques et expositions diffèrent des bots existants, donc aucun classement sur les seuls rendements.',
 '## Décision et reproduction',decision+' Les bots Noise Area et ORB restent inchangés, exclusivement en simulation. Aucun nouveau bot ni passage au réel.',
 '[84 comptes](comparison_all.csv) · [Critères](SCREENING.json) · [Gel avant PnL](PRE_EXECUTION_PROTOCOL.json) · [Source](DATA_SOURCE_PROFILE.json) · [Tests](TESTS.json) · [Audit](../../audit/AUDIT_RESULTS.json) · [Agrégats](../../audit/ADDITIONAL_CHECKS.json) · [Protocole](../../PROTOCOL_EXECUTION.md). Dossiers : trades/daily/unresolved/by_year/summary ; features/gaps par ETF, snapshots et manifest final. Archives brutes et secrets exclus de Git.']
 text='\\n\\n'.join(parts).replace('\\n','\n')+'\n';(OUT/'RAPPORT_FINAL.md').write_text(text,encoding='utf-8',newline='\n');print(decision)
if __name__=='__main__':main()
