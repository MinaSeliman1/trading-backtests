"""Delivery prose from audited exports; no financial changes."""
from pathlib import Path
import json
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/2026-10-31-v1'
def main():
 m=pd.read_csv(OUT/'comparison_all.csv');refs=m[m.variant=='reference'];allref=refs[refs.period=='ALL'].set_index('symbol')
 j=lambda p:json.loads(p.read_text(encoding='utf-8'))
 audit=j(ROOT/'audit/AUDIT_RESULTS.json');extra=j(ROOT/'audit/ADDITIONAL_CHECKS.json');tests=j(OUT/'TESTS.json');frozen=j(OUT/'PRE_EXECUTION_PROTOCOL.json');screen=j(OUT/'SCREENING.json')
 write=lambda name,text:(ROOT/name).write_text(text,encoding='utf-8',newline='\n')
 results=' ; '.join(f"{s} {allref.loc[s,'total_return_pct']:+.2f} % / {int(allref.loc[s,'trades'])} trades" for s in ('SPY','QQQ'))
 body=['# Compression de midi, cassure après 13 h — QQQ et SPY',
 '**Statut : '+screen['decision']+'** Références2016–16/10/2026 après mêmes frais : '+results+'.',
 'Range midi11:30–12:30 strictement inférieur à30 % du range matin09:30–11:30. Première nouvelle traversée au-dessus du highMidi après13:00 jusqu’à14:30, clôture5min et volume/minute supérieur à la moyenne du midi. Une candidate consommée même si son volume échoue. Achat au marché une minute après décision ; stop milieu du midi, sortie15:59 au plus tard. LONG, risque1 % et objectif1× avant fill/frais ; ces cibles peuvent être dépassées par un gap.',
 'Commission0.0035USD/action/côté min0.35USD ; friction adverse0.01USD/action/côté, stresses0.02/0.03/0.05. Une formalisation mécanique inspirée d’un article, pas une réplication certifiée. A/B déjà réutilisées, portefeuille conditionnel à la couverture, aucun nouvel OOS aveugle.',
 '[Rapport et quatre figures](results/2026-10-31-v1/RAPPORT_FINAL.md) · [84comptes](results/2026-10-31-v1/comparison_all.csv) · [Protocole](PROTOCOL_EXECUTION.md) · [Recherche](RESEARCH.md) · [Interprétation](INTERPRETATION.md) · [Validation](VALIDATION.md).',
 '## Reproduction locale',
 'Python3.14 et versions requirements-lock.txt. Archives SIP et préparations locales vérifiées nécessaires, ignorées par Git et non redistribuées. Aucun API/clé/ordre. Recalcul dans une copie séparée du checkout au même niveau, avec mêmes archives/préparations disponibles ; cela protège les preuves originales. Depuis la racine de cette copie, dépendances installées :',
 '~~~powershell\n$env:PYTHONUTF8="1"\n$env:PYTHONDONTWRITEBYTECODE="1"\npython -m pytest studies/lunch-compression-breakout/tests -q -p no:cacheprovider\npython studies/lunch-compression-breakout/scripts/run_study.py --out studies/lunch-compression-breakout/results/reproduction\n~~~',
 'Le runner refuse un dossier non vide. Dans la copie seulement, donner le même --out à audit/independent.py ; il doit rester SOUS studies/lunch-compression-breakout. L’oracle écrit audit/AUDIT_RESULTS.json à une position fixe : ne pas lancer une reproduction dans le checkout original, car cette preuve serait remplacée. Les scripts de statistiques et de présentation ciblent le run archivé ; adapter leurs chemins dans la copie avant emploi sur une reproduction.',
 'Vérification en lecture seule de la livraison originale :',
 '~~~powershell\n$env:PYTHONUTF8="1"\n$env:PYTHONDONTWRITEBYTECODE="1"\npython studies/lunch-compression-breakout/scripts/verify_delivery.py --raw\n~~~',
 'Empreintes = intégrité des octets, pas certification de complétude ou de fills réels. Aucun nouveau bot ; les deux simulations existantes sont préservées.']
 replacements={'Références2016':'Références 2016','midi11:30':'midi 11:30','à30 %':'à 30 %','matin09:30':'matin 09:30','après13:00':'après 13:00','jusqu’à14:30':'jusqu’à 14:30','clôture5min':'clôture 5 min','sortie15:59':'sortie 15:59','risque1 %':'risque 1 %','objectif1×':'objectif 1×','Commission0.0035USD':'Commission 0.0035 USD','min0.35USD':'min 0.35 USD','adverse0.01USD':'adverse 0.01 USD','stresses0.02/0.03/0.05':'stresses 0.02/0.03/0.05','84comptes':'84 comptes'}
 text='\n\n'.join(body)+'\n'
 for a,b in replacements.items():text=text.replace(a,b)
 write(Path('README.md'),text)
 lines=['# Interprétation', 'Référence après frais : '+results+'. Les gains faibles sur ALL ne prouvent pas un avantage robuste ; examiner les périodes et le nombre de transactions.']
 for s in ('SPY','QQQ'):
  rr=refs[refs.symbol==s].set_index('period');ci=j(OUT/f'{s}_ALL_uncertainty.json')['blocks']['20']['conditional_daily_mean_ci95'];stress=m[(m.symbol==s)&(m.period=='ALL')&(m.variant=='cost_0.02')].iloc[0]
  failed=[k for k,v in screen['checks'][s].items() if not v]
  lines.append(f"{s} : {int(rr.loc['ALL','trades'])} trades, seuil préétabli100. A {rr.loc['A','total_return_pct']:+.2f} %, B {rr.loc['B','total_return_pct']:+.2f} %, ALL sans top3 {rr.loc['ALL','return_without_top3_days_pct']:+.2f} %, ALL friction doublée {stress.total_return_pct:+.2f} %. IC95 quotidien blocs20 [{ci[0]*10000:.3f}, {ci[1]*10000:.3f}] bps. Critères échoués : {', '.join(failed) or 'aucun'}.")
  loose=m[(m.symbol==s)&(m.period=='ALL')&(m.variant=='compression_0.5')].iloc[0]
  lines.append(f"{s}, variante compression0.50 : {int(loose.trades)} trades / {loose.total_return_pct:+.2f} %. Elle n’est pas substituée à la référence pour atteindre un nombre de trades après avoir vu les résultats.")
 lines+=['Décomposition avec les quantités du compte net, pas portefeuille gratuit recalculé. Sans top3 neutralise ces retours sans nouvelles quantités. Filtre de journée entière futur dans complete_days ; resolved_prefix et inconnus publiés. Aucun carnet, tick ou preuve d’exécution réelle.', 'Les choix d’heures, seuils et variantes ont été figés avant PnL. Ces archives A/B ont déjà servi à de nombreuses recherches, SPY/QQQ corrélés et IC descriptifs sans correction de sélection multiple. '+screen['decision']+' Aucun nouveau bot ni passage au réel.']
 write(Path('INTERPRETATION.md'),'\n\n'.join(lines)+'\n')
 lines=['# Validation',f"{tests['passed']} tests passent : compression/égalité, niveaux fixes, nouveau croisement, premier échec volume, unités1/5/15min, fenêtres/cutoff, taille/frais/gaps/unknowns, ledger et configurations exportées. WR/PF/Sharpe indéfinis testés sans les confondre avec zéro.",
 f"Oracle complet : {audit['checks']} contrôles, {audit['executions']} comptes, {audit['feature_rows']} lignes de caractéristiques, {audit['trade_rows']} lignes de trades, {audit['daily_rows']} lignes quotidiennes. Recouvrements entre variantes/périodes, pas observations indépendantes. {extra['numeric_checks']} contrôles agrégés et six références bootstrap blocs5/20 reproduites.",
 f"Gel avant premier PnL : {len(frozen['code_sha256'])} fichiers code/tests/runner/oracle/vérification, {len(frozen['dependencies_sha256'])} dépendances et deux protocoles conservés avec texte. Présentation après gel et manifest final distinct. Les notes héritées de dividendes ne changent pas les prix bruts de ce test.",
 'Revue pré-PnL lunch_pre_review :47tests puis51tests après corrections,112comptes synthétiques/20850comparaisons supplémentaires avant les derniers guards statistiques. Défaut Config-only stop_enabled absent des lignes exportées corrigé (stop toujours actif), avec régression RED puis GREEN. Audit agrégé renforcé sur zéro-trade/all-winning/variance nulle et manquants, quatre tests RED puis GREEN. Test de matrice charge le runner par chemin exact pour éviter un namespace scripts d’une ancienne étude. Aucune règle changée après PnL.']
 for s in ('SPY','QQQ'):
  d=pd.read_csv(OUT/f'{s}_ALL_reference/daily.csv');t=pd.read_csv(OUT/f'{s}_ALL_reference/trades.csv')
  lines.append(s+' : '+', '.join(f'{k}={v}' for k,v in d.eligibility.value_counts().items())+f". Trades résolus du {t.date.min()} au {t.date.max()}.")
 lines+=['Source/calendrier/caches/acquisitions vérifiés, même chargeur et fournisseur pour l’oracle. Aucun deuxième fournisseur, quote/partiel/latence réelle. Cache de l’oracle retient les marchés pour empêcher réemploi d’identité ; ils doivent rester immuables pendant main. Couverture conditionnelle explicite, exclusions au zéro de chaînage, pas cash observé.',
 '[Tests](results/2026-10-31-v1/TESTS.json) · [Oracle](audit/AUDIT_RESULTS.json) · [Agrégats](audit/ADDITIONAL_CHECKS.json) · [Gel](results/2026-10-31-v1/PRE_EXECUTION_PROTOCOL.json) · [Sources](WEB_SOURCE_STATUS.json). Quatre figures inspectées avant publication ; reproduction dans copie séparée, --out sous l’étude et audit fixe protégé, détails README. verify_delivery.py --raw vérifie la livraison originale en lecture seule. Aucun bot, coffre, tâche Windows, SQLite ou paramètre actif modifié.']
 write(Path('VALIDATION.md'),'\n\n'.join(lines)+'\n');print(results)
if __name__=='__main__':main()
