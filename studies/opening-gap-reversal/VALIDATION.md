# Validation et versions — 20 octobre 2026

Référence de publication : [résultats v3](results/2026-10-20-v3/RAPPORT_FINAL.md). Analyse partageable avec les limites de liquidité et d'échantillon décrites dans le rapport ; aucun avantage prospectif n'est démontré.

## Exécutions et preuves

- **20 tests passent en 1,19 seconde** : `python -m pytest -q --basetemp=.test_tmp_release` depuis ce dossier. Seuil exactement ±2 %, dividendes, fenêtres, demi-séance précédente, quantités causales, suspensions intermédiaires, bornes manquantes, frais minimaux, emprunt, résultats vides, recomposition, bootstrap annuel et durée du drawdown.
- **54 scénarios** dans la version finale, paramètres et hashes gelés avant son calcul. La toute première inscription avant consultation du P&L est conservée dans [PRE_EXECUTION_PROTOCOL initial](results/2026-10-20/PRE_EXECUTION_PROTOCOL.json). Les résultats étaient déjà connus lors des corrections ultérieures ; ces réexécutions ne constituent pas de nouveaux tests indépendants.
- **2 334 lignes de trades auditées en Decimal**, source par source, sans helpers du moteur : appartenance des événements, clôture précédente et dividende, taille, sens, temps, fills, commissions, emprunt, capital, rendements et DD quotidien. Erreur monétaire maximale : **4,42 × 10⁻¹¹ USD**. [Preuve finale](results/2026-10-20-v3/AUDIT_INDEPENDANT.json).
- Les lignes auditées incluent des périodes et variantes qui se recouvrent. Les événements principaux ALL sont **48 SPY et 83 QQQ**, pas 2 334 trades indépendants.
- Une seconde revue indépendante a vérifié les 54 scénarios, les 131 trades principaux ALL depuis les tableaux sources, les drawdowns minute, les intervalles annuels et les empreintes du manifeste.
- Trois figures PNG ont été ouvertes et contrôlées : dates, légendes, unités, bases communes, absence de clipping et fidélité aux valeurs. Les figures sont des exports scientifiques statiques.

## Corrections de revue, sans changement de règles

1. **Seuil strict après dividende** : 128,01 − 2,01 pouvait devenir 125,99999999999999 en flottant et produire un faux trade à exactement +2 %. Un test rouge a reproduit le problème ; soustraction et comparaison sont désormais décimales. Aucune date réelle de l'échantillon ne change.
2. **Corrélation** : publier séparément les P&L quotidiens USD demandés par le protocole et les rendements quotidiens. La version initiale ne publiait que les seconds.
3. **Durée du drawdown** : mesurer depuis le dernier sommet du plateau avant la perte, au lieu d'inclure les jours antérieurs à plat. Correction locale à cette étude, sans modifier les statistiques ou résultats Noise Area archivés. Test rouge puis vert.

La revue finale a confirmé les trois points clos et n'a trouvé aucun défaut résiduel dans ces corrections. [Comparaison v1/v3](results/2026-10-20-v3/VERSION_COMPARISON.json) : **P&L des 54 scénarios inchangés**. V1 et V2 restent archivées, V3 est la référence. Le code exécuté initial est conservé dans `results/2026-10-20/code_snapshot/` ; ses fichiers sont des archives à restaurer dans la structure de l'étude pour reproduire l'ancienne version, pas une seconde suite active de tests.

Une collecte pytest intermédiaire a rencontré les tests archivés et leur ancien chemin d'import. `pytest.ini` borne désormais la suite active à `tests/` ; la collecte et les 20 tests passent. Les absences initiales de modules et les tests rouges des corrections ont précédé leur implémentation ; aucune donnée de ces tests contrôlés n'est utilisée dans les résultats financiers.

## Sources et intégrité

Acquisitions Alpaca SIP raw déjà validées dans Noise Area, jusqu'au 16 octobre 2026. Les SHA-256 des deux pickles, deux fichiers de dividendes et deux rapports de qualité sont vérifiés avant chaque simulation. Aucun téléchargement, identifiant ou compte Alpaca n'est nécessaire pour exécuter cette étude locale.

La qualité primaire repose sur les bornes observées, sans interpolation des minutes suspendues. Les quatre dates de circuit breaker de mars 2020 sont confirmées par [NYSE](https://www.nyse.com/article/assessing-nyse-model-performance). Les autres trous ne sont pas arbitrairement déclarés suspensions officielles.

Les résultats d'origine FVG et Noise Area sont conservés. Le bot Noise Area reste séparé et utilise SIP shadow différé ; son code n'est pas modifié par ce backtest. Les résultats prospectifs futurs ne sont ni présents ni supposés dans ce rapport.

## Commandes réellement exécutées

```powershell
python -m pytest -q --basetemp=.test_tmp_release
python scripts/run_study.py
python scripts/run_study.py --out results/2026-10-20-v2 --rerun-reason "Corrections de précision de revue"
python scripts/run_study.py --out results/2026-10-20-v3 --rerun-reason "Corrections finales de revue, aucun ajustement de stratégie"
python scripts/audit_results.py --out results/2026-10-20-v3
python scripts/write_report.py
```

Les textes exacts des motifs de réexécution sont enregistrés dans chaque PRE_EXECUTION_PROTOCOL.json. Les variantes de commande ci-dessus abrègent ces motifs, sans modifier les paramètres de calcul.
