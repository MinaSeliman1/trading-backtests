# Retour vers VWAP après la première heure — SPY / QQQ

**Backtest terminé le 20 octobre 2026 : 48 scénarios, 46 tests et audit indépendant.** [Rapport complet](results/2026-10-20/RAPPORT_FINAL.md), [comparaisons](results/2026-10-20/comparison_all.csv), [validation](VALIDATION.md).

Principaux nets de frais : **SPY −9,64 % ALL /−0,33 % B**, 393 /107 trades ; **QQQ −15,79 % ALL /−0,87 % B**, 506 /129 trades. Archiver cette version comme négative, aucun nouveau bot justifié. Les résultats restent conditionnels à la couverture et B réutilisée est exploratoire. Le protocole initial reste dans le gel avant P&L, sans changement des règles ou des résultats.

Hypothèse propre de retour à la moyenne ; les sources Alpaca définissent l'indicateur et les barres, sans valider la rentabilité de notre stratégie.

Données SIP minute 2016–16/10/2026, archives brutes `vw` × volumes réguliers, pas proxy HLC3. Décision à close 10:29 : acheter sous VWAP, vendre à découvert au-dessus, seulement si écart absolu > 0,25 × ADR20. ADR20 = moyenne des amplitudes high-low des 20 séances immédiatement précédentes complètes, sans overnight. Entrée supposée open 10:30, taille connue avant entrée, risque cible 1 %, plafond causal 1x, stop fixe à une ADR20 de l'open d'entrée. Sortie au prochain open après clôture revenue au-delà du VWAP courant, ou stop, ou dernier open 15:59/12:59. Un trade maximum/jour.

Mêmes coûts : commission 0,0035 USD/action/côté, min 0,35 USD/ordre ; friction adverse 0,01 USD/action/côté, stress 0,02/0,03/0,05 ; SHORT 1 %/360, un jour minimum, cash non rémunéré. Capital initial 100 000 USD séparément par instrument et période.

48 scénarios : 2 instruments × A/B/ALL × 8 spécifications (principal quatre frictions, LONG seul, SHORT seul, sans sortie VWAP mais mêmes stop/EOD, et couverture resolved_prefix). ALL 04/01/2016–16/10/2026 ; A jusqu'au 30/04/2024 ; B 01/05/2024–16/10/2026, historique réutilisé et exploratoire, pas nouveau test aveugle. Le seuil, le stop et les horaires ne seront pas optimisés après résultat.

Résultats conditionnels à l'observabilité historique : le principal exige la séance actuelle complète après les filtres causaux de signal ; sensibilité jusqu'à sortie seulement. Les jours non résolus ne sont pas des rendements cash observés. Le protocole détaillé a été gelé avec le code et les sources avant toute boucle de P&L. Les études précédentes, le bot et les clés restent inchangés.

Sources primaires : [Alpaca, calcul de VWAP](https://alpaca.markets/learn/algorithmic-trading-with-twap-and-vwap-using-alpaca), [construction des barres](https://alpaca.markets/learn/stock-minute-bars), [FAQ des données et VWAP](https://docs.alpaca.markets/us/docs/market-data-faq). Le tutoriel présente une autre logique de signal ; notre version contrariante n'en est pas une réplication.

## Reproduire

Depuis ce dossier, avec `requirements.txt` et les archives locales aux empreintes indiquées dans le profil :

```powershell
python -m pytest -q --basetemp=.test_tmp_local
python scripts/run_study.py --out results/ma-nouvelle-execution
python scripts/audit_independent.py results/ma-nouvelle-execution
python scripts/validate_outputs.py results/ma-nouvelle-execution
python scripts/write_report.py results/ma-nouvelle-execution
```

Le lanceur refuse d'écraser un dossier non vide. `data.load_sources` contrôle les six caches/CSV et les 428 pages brutes, rapproche tous OHLCV RTH et prépare des `.npy` VWAP locaux ignorés par Git ; les SHA/source/calendrier sont publiés dans `DATA_SOURCE_PROFILE.json`. Aucun accès API ni saisie de clé nécessaire avec ces archives présentes. Ne pas désérialiser de pickle de provenance inconnue.

L'audit recalcule 12 586 lignes recouvrantes et 2 125 058 marks ; les 16 extraits complets jusqu'à sortie donnent 3 168 barres /19 008 champs OHLCV/VWAP relus sans écart. Les tests synthétiques ne sont pas des observations de performance. `python scripts/verify_delivery.py` vérifie les performances initiales, les helpers inchangés et le manifest final. Les bibliothèques et contrôles finaux sont tracés dans `BUILD_EVIDENCE.json`.

[ORB QQQ : décision et prochaine validation recommandée](../../docs/research/2026-10-20-orb-qqq-decision.md). ORB reste candidate, sans nouvelle activation de bot dans cette étude.
