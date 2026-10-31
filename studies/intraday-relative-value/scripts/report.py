"""Present audited paired-account exports; no strategy parameter selection."""
from pathlib import Path
import sys,json,argparse,math
ROOT=Path(__file__).resolve().parents[1]
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def table(rows,cols):
 def cell(x):
  if x is None or isinstance(x,(float,np.floating)) and not math.isfinite(x):return '—'
  return f'{x:.2f}' if isinstance(x,(float,np.floating)) else str(x)
 return '| '+' | '.join(label for _,label in cols)+' |\n|'+ '|'.join('---' for _ in cols)+'|\n'+'\n'.join('| '+' | '.join(cell(r.get(k)) for k,_ in cols)+' |' for r in rows)

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=ROOT/'results/2026-10-31-v1');out=p.parse_args().out.resolve()
 df=pd.read_csv(out/'comparison_all.csv');audit=json.loads((ROOT/'audit/AUDIT_RESULTS.json').read_text());assert audit['status']=='passed'
 def row(period='ALL',variant='reference'):return df[(df.period==period)&(df.variant==variant)].iloc[0].to_dict()
 u=json.loads((out/'ALL_uncertainty.json').read_text());checks={'pairs_all_ge100':row()['pairs']>=100,'reference_A_B_ALL_positive':all(row(p)['net_pnl']>0 for p in ['A','B','ALL']),
  'all_without_top3_positive':row()['return_without_top3_days_pct']>0,'A_double_friction_positive':row('A','cost_0.02')['net_pnl']>0,'all_block20_ci_lower_positive':u['blocks']['20']['conditional_daily_mean_ci95'][0]>0}
 passed=all(checks.values());decision='Candidat historique à discuter, aucun bot automatique.' if passed else 'Piste écartée pour un nouveau bot : critères fixés avant résultats non satisfaits.'
 screening=dict(criteria=checks,all_passed=passed,decision=decision,blind_oos=False,multiple_testing_adjusted=False)
 (out/'SCREENING.json').write_text(json.dumps(screening,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 figs=out/'figures';figs.mkdir(exist_ok=True);plt.rcParams.update({'font.size':10})
 fig,ax=plt.subplots(figsize=(10,5))
 for v,label,style in [('reference','Référence : journées complètes','-'),('resolved_prefix','Préfixe résolu, autre couverture','--')]:
  d=pd.read_csv(out/f'ALL_{v}/daily.csv');ax.plot(pd.to_datetime(d.date),(d.equity/100000-1)*100,label=label,linestyle=style)
 ax.axhline(0,color='black',lw=.7);ax.set(title='Paire QQQ/SPY — comptes historiques conditionnels',ylabel='Rendement net cumulé (%)');ax.grid(alpha=.2);ax.legend();fig.tight_layout();fig.savefig(figs/'equity.png',dpi=150);plt.close(fig)
 fig,ax=plt.subplots(figsize=(9,4.5));costs=[0,.01,.02,.03,.05];values=[row('ALL','friction_zero' if c==0 else 'reference' if c==.01 else f'cost_{c:g}')['total_return_pct'] for c in costs]
 ax.bar(range(5),values,color='#376997');ax.set_xticks(range(5),[f'{c:.2f}' for c in costs]);ax.axhline(0,color='black',lw=.7);ax.set(xlabel='Friction USD/action/côté — commissions et emprunt restent',ylabel='Rendement net ALL (%)',title='Stress de friction fixé avant résultats');fig.tight_layout();fig.savefig(figs/'costs.png',dpi=150);plt.close(fig)
 d=pd.read_csv(out/'ALL_reference/daily.csv');year=d.assign(year=pd.to_datetime(d.date).dt.year).groupby('year').return_net.apply(lambda r:((1+r).prod()-1)*100)
 fig,ax=plt.subplots(figsize=(10,4.5));ax.bar(year.index.astype(str),year,color=['#287968' if v>0 else '#a64534' for v in year]);ax.axhline(0,color='black',lw=.7);ax.set(title='Portefeuille de paire — années civiles, 2026 partielle au 16 octobre',ylabel='Rendement annuel net (%)');fig.tight_layout();fig.savefig(figs/'years.png',dpi=150);plt.close(fig)
 l=pd.read_csv(out/'ALL_reference/legs.csv');lc=l.groupby('symbol').agg(price_move_pnl=('price_move_pnl','sum'),commission=('commission','sum'),friction_cost=('friction_cost','sum'),borrow_fee=('borrow_fee','sum'),net_pnl=('net_pnl','sum')).reset_index()
 fig,ax=plt.subplots(figsize=(8,4.5));ax.bar(lc.symbol,lc.net_pnl,color=['#985c12','#376997']);ax.axhline(0,color='black',lw=.7);ax.set(title='Contributions des deux jambes au même portefeuille',ylabel='Contribution nette ALL (USD)');fig.tight_layout();fig.savefig(figs/'legs.png',dpi=150);plt.close(fig)
 refs=df[df.variant=='reference'].to_dict('records');ci=[]
 for p in ['ALL','A','B']:
  u=json.loads((out/f'{p}_uncertainty.json').read_text());ci.append(dict(period=p,low=u['blocks']['20']['conditional_daily_mean_ci95'][0]*10000,high=u['blocks']['20']['conditional_daily_mean_ci95'][1]*10000))
 exits=pd.read_csv(out/'ALL_reference/trades.csv').groupby('exit_reason').agg(pairs=('net_pnl','size'),net_pnl=('net_pnl','sum')).reset_index()
 sections=['# Valeur relative intraday QQQ/SPY — rapport final','**'+decision+'**',
  'Un seul portefeuille initial de100000USD, deux jambes simultanées QQQ/SPY. Les contributions par actif ci-dessous ne sont pas deux stratégies ou deux comptes indépendants. Les bots Noise Area et ORB restent inchangés en simulation.',
  '## Règles réellement testées',
  'Écart des log-retours depuis l’open RTH du jour. Avant chaque séance, moyenne et écart-type échantillon du même créneau sur20séances passées, sans sauter une séance invalide ; demi-séances structurelles traitées selon le protocole. Première close5min entre10:00et14:30 où2<=abs(Z)<3 : acheter l’ETF relativement faible et vendre l’autre. Quantités entières figées aux closes, dollar-neutres approximativement, gross cap1x et proxy de risque cible1%. Entrée aux opens suivants.',
  'Cible à la moyenne et stop3sigma fixés à la décision ; contrôle aux closes1minute, sortie aux opens suivants, EOD préprogrammé au dernier open15:59/12:59. Pas de stop intrabar garanti : gaps et mouvements entre closes peuvent dépasser la perte proxy. Une paire maximum/jour, pas de nuit ni de réentrée.',
  'Commission0.0035USD/action/côté minimum0.35 pour chacun des quatre ordres ; friction0.01USD/action/côté ; emprunt SHORT1%annuel/360 minimum1jour sur valeur au fill. Les produits de short ne sont pas un profit réutilisé pour augmenter l’exposition. Référence cash sans intérêt0%.',
  '## Résultats du portefeuille après frais',
  table(refs,[('period','Période'),('pairs','Paires'),('leg_trades','Jambes'),('total_return_pct','Net %'),('cagr_pct','CAGR %'),('win_rate_pct','Paires gagnantes %'),('profit_factor','PF'),('observed_drawdown_pct','DD observé %'),('return_without_top3_days_pct','Sans top3 %')]),
  'ALL2016-01-04–2026-10-16 ; A jusqu’au2024-04-30 ; B2024-05-01–2026-10-16. Chaque compte de période repart de100000USD. A et B ont déjà été étudiées ; aucun nouvel OOS aveugle. Comptes historiques conditionnels aux données résolues, pas portefeuille observé sans interruption.',
  '![Comptes conditionnels](figures/equity.png)',
  '## Attribution des coûts et des jambes',
  table([row()],[('price_move_pnl','Mouvement brut USD'),('friction_cost','Frictions USD'),('commission','Commissions USD'),('borrow_fee','Emprunt USD'),('net_pnl','Net USD'),('worst_pair_usd','Pire paire USD'),('max_entry_leverage','Levier réf max'),('max_entry_fill_leverage','Levier fill max'),('max_proxy_risk_pct','Risque proxy max %')]),
  table(lc.to_dict('records'),[('symbol','Jambe'),('price_move_pnl','Mouvement USD'),('friction_cost','Friction USD'),('commission','Commissions USD'),('borrow_fee','Emprunt USD'),('net_pnl','Contribution nette USD')]),
  'La somme des contributions nettes des deux jambes égale le résultat du portefeuille. Une jambe positive isolée ne constitue pas une stratégie ETF autonome. Les parts notionnelles ne sont pas parfaitement égales après arrondis ; ce hedge en dollars ne neutralise pas nécessairement le bêta ou le risque sectoriel.',
  '![Contributions par jambe](figures/legs.png)',
  '## Sorties et calendrier',
  table(exits.to_dict('records'),[('exit_reason','Sortie'),('pairs','Paires ALL'),('net_pnl','Net USD')]),
  '![Années](figures/years.png)',
  '## Sensibilités fixées avant PnL',
  table(df.to_dict('records'),[('period','Période'),('variant','Variante'),('pairs','Paires'),('total_return_pct','Net %'),('profit_factor','PF'),('observed_drawdown_pct','DD %')]),
  'friction_zero conserve commissions et emprunt : ce n’est pas un scénario gratuit. cost_gate est un filtre causal basé sur un proxy de retour à la moyenne comparé à deux fois les coûts anticipés ; son absence d’effet éventuelle ne prouve pas les fills. Les comptes de sensibilités se chevauchent et aucune variante ne remplace après coup la référence.',
  '![Friction](figures/costs.png)',
  '## Incertitude et décision',
  table(ci,[('period','Période'),('low','IC95 moyen/jour bas, bps'),('high','IC95 haut, bps')]),
  'Bootstrap descriptif3000tirages, blocs circulaires5/20séances, seed20261031. Les jours exclus entrent comme zéros de chaînage, pas cash observé. Pas de correction de toutes les hypothèses antérieures ; IC conditionnels et histoire réutilisée.',
  table([dict(criterion=k,result='passe' if v else 'échoue') for k,v in checks.items()],[('criterion','Critère avant résultats'),('result','Résultat')]),decision,
  '## Couverture, preuve et limites',
  table(refs,[('period','Période'),('data_excluded_sessions','Jours exclus'),('unresolved_sessions','Paires non résolues'),('simulated_rth_time_exposure_pct','Exposition RTH simulée %')]),
  f'Replay scalaire indépendant :{audit["checks"]}contrôles,{audit["scenarios"]}scénarios,{audit["pair_rows"]}lignes de paires et{audit["leg_rows"]}jambes,{audit["daily_rows"]}lignes quotidiennes. Ces observations se chevauchent entre scénarios et périodes. L’oracle recalcule features, choix, deux fills, quatre frais, emprunt, comptes et DD sans appeler le moteur ; même source/chargeur, pas deuxième feed.',
  'Le principal complete_days filtre la qualité de la journée courante connue après coup. resolved_prefix le retire mais conserve les prix nécessaires aux décisions et à la position ; un signal inconnu n’est pas sauté pour en chercher un autre favorable. Une paire non résolue est omise en entier, coûts d’entrée connus archivés. Le résultat n’est pas une performance continue certifiée sur les périodes exclues.',
  'Fills aux deux opens simultanés hypothétiques : pas d’atomicité broker, carnet, quotes, liquidité, fills partiels ou risques de legging modélisés. delay2 retarde les deux jambes ensemble et ne simule pas une seule jambe bloquée. Taux et disponibilité réels d’emprunt non vérifiés ; spread/slippage réel peut excéder le modèle. Données historiques susceptibles de révisions, pas véritable archive point-in-time certifiée. DD aux marks observés, pas maximum de tick ; MAE/MFE excluent commissions et emprunt.',
  'Aucune cointégration, vitesse de retour ou neutralité de marché n’est déduite de la corrélation des ETF. Cette adaptation diffère des sources Kalman, niveaux daily ou univers de paires sélectionnées ; aucun rendement externe reproduit.',
  '## Accéder aux preuves',
  '[42comptes](comparison_all.csv) · [Critères](SCREENING.json) · [Gel financier](PRE_EXECUTION_PROTOCOL.json) · [Données](DATA_SOURCE_PROFILE.json) · [Tests](TESTS.json) · [Audit](../../audit/AUDIT_RESULTS.json) · [Recherche](../../RESEARCH.md) · [Protocole](../../PROTOCOL_EXECUTION.md). Exports de chaque compte : daily, trades de paire, legs, unresolved, by_year et summary. Historiques minute complets et clés restent locaux. Aucun nouveau bot ni ordre réel.']
 (out/'RAPPORT_FINAL.md').write_text('\n\n'.join(sections)+'\n',encoding='utf-8');print(json.dumps(screening,ensure_ascii=True))
if __name__=='__main__':main()
