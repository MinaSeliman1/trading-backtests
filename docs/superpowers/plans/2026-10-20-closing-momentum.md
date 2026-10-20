# Backtest momentum de clôture

Objectif autorisé : exécuter le protocole préparé, auditer les résultats et publier le code/tests/rapport dans trading-backtests. Exécution directe dans cette session ; revue indépendante avant publication. Le bot actif et ses journaux restent séparés.

Spécifications : studies/closing-momentum/README.md au commit 4d79c7f et PROTOCOL_EXECUTION.md avant P&L. Données locales SIP 2016–16/10/2026 ; A/B/ALL exploratoires, B réutilisée.

## Interfaces

- `closing_momentum.engine.Config` : mode, friction, capital et coûts.
- `prepare(market, dividends) -> DataFrame` : un état d'éligibilité causal par séance, signal, indices et prix nécessaires. Source : Market figé de Noise Area ; aucune mutation.
- `simulate(market, prepared, config, start, end, fixed_quantities=None)` : daily/trades et drawdown minute observé, sans ordre/réseau.
- `analysis.summarize(result)` et `uncertainty(result, benchmark)` : métriques, références et incertitude explicite.
- `scripts/run_study.py --out` : refuse écrasement, contrôle SHA, gèle protocole/code avant simulation, exporte 42 scénarios.
- `scripts/audit_results.py --out` : recomposition indépendante Decimal depuis les sources, sans importer le moteur.
- `scripts/write_report.py --out` : rapport, tableaux, examens de transactions et figures depuis exports audités.

## Étapes

1. [x] Tests rouges du moteur puis verts : signal, fenêtres, prix, coûts, témoins et drawdowns.
2. [x] Empreintes et calendrier contrôlés ; 33 tests après correction locale de la durée du drawdown. Revue indépendante du code et du protocole ; insolvabilité explicitée avant P&L.
3. [x] Deux exécutions conservées, v2 référence ; 42 scénarios chacune, 70 934 lignes auditées en Decimal, prix/frais/capital/DD rapprochés, agrégats secondaires contrôlés. P&L et chemins de capital identiques entre versions.
4. [x] Rapport complet, exclusions, coûts, références, années, concentration, 16 transactions détaillées et 80 références brutes sans écart. Quatre figures générées ; conclusions négatives et limites explicites, sans optimisation après observation.
5. [x] Tests finaux : 33 passent ; 1 977 empreintes historiques et manifestes initiaux/livraison concordants. Rapport, sources et preuves préparés pour publication GitHub dans le même commit.

## Points de revue prioritaires

1. Un prix plus tardif ou une journée incomplète après la sortie ne doit pas modifier le signal/éligibilité : test de mutation du futur dans engine.
2. Le dividende annulant exactement l'overnight ne doit pas provoquer un trade binaire résiduel : fixture décimale dans engine.
3. Une sortie manquante ne doit pas donner une performance plate : erreur explicite de simulation.
4. La quantité d'un témoin ne doit pas se redimensionner sur ses gains propres : comparaison sur séquence imposée.
5. Un drawdown intrajournalier récupéré avant sortie ne doit pas disparaître du rapport : fixture de baisse/reprise et audit minute indépendant.
