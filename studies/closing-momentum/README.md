# Piste : momentum de clôture sur SPY et QQQ

**Statut au 20 octobre 2026 : backtest terminé, 42 exécutions prédéfinies et 33 tests ; référence v2. Les scénarios principaux SPY/QQQ perdent après frais sur A, B et ALL : aucun nouveau bot justifié pour cette version.** Elle n'est pas ajoutée au bot Noise Area actif.

[Rapport complet](results/2026-10-20-v2/RAPPORT_FINAL.md) · [42 comparaisons](results/2026-10-20-v2/comparison_all.csv) · [Audit indépendant](results/2026-10-20-v2/AUDIT_INDEPENDANT.json) · [Examen de transactions et sources brutes](results/2026-10-20-v2/EXAMEN_TRANSACTIONS.md) · [Validation](VALIDATION.md).

Sur B (01/05/2024–16/10/2026), cible 1x et tous coûts prévus : SPY **−3,39 % /616 trades**, QQQ **−3,70 % /618 trades**. Sur ALL (2016–16/10/2026), **−34,72 % et −35,19 %**. La variante QQQ LONG seule gagne 2,01 % en B, mais reste négative sur ALL et sous le témoin LONG de B. B réutilise l'historique des précédentes études : comparaison exploratoire, sans nouveau label hors échantillon aveugle.

Les règles ci-dessous étaient enregistrées avant P&L au commit `4d79c7f` ; les précisions de qualité, témoins et insolvabilité ont été figées dans le [complément d'exécution](PROTOCOL_EXECUTION.md). Le texte antérieur et ses empreintes sont conservés dans [PRE_EXECUTION_PROTOCOL.json](results/2026-10-20-v2/PRE_EXECUTION_PROTOCOL.json). Le premier calcul reste archivé ; v2 corrige uniquement la durée du drawdown, sans modifier les fichiers de trades ou de capital quotidien.

L'hypothèse principale est que le signe du rendement entre la clôture précédente et la fin de la première demi-heure aide à prévoir la dernière demi-heure. Un article des auteurs Baltussen, Da, Lammers et Martens décrit cette relation étudiée par Gao et al. et présente une autre prédiction fondée sur le reste de la journée. [Source primaire, introduction et définitions, pp. 378 et 381](https://academicweb.nd.edu/~zda/intramom.pdf). Ce constat publié motive un test ; il ne fournit pas nos résultats SPY/QQQ après coûts.

## Règles à figer avant calcul

| Élément | Protocole principal |
|---|---|
| Instruments | SPY et QQQ, séparément ; ne pas choisir le gagnant après calcul |
| Données | OHLCV minute Alpaca SIP raw et dividendes de l'acquisition locale vérifiée |
| Signal | `close_09:59 / (clôture_RTH_précédente - dividende_ex_date) - 1` |
| Direction | LONG si positif, SHORT si négatif, aucune position si exactement nul |
| Entrée | Open 15:30 ; signal du matin déjà connu |
| Sortie | Open 15:59, sans maintien overnight |
| Demi-séance | Entrée 12:30, sortie 12:59 ; résultats identifiés séparément |
| Exposition | 1x ; quantité entière `floor(capital_net / close_15:29)` ; capital initial 100 000 USD |
| Stop/objectif | Aucun ; ne pas optimiser un stop après observation des gains/pertes |
| Frais | 0,0035 USD/action/côté, minimum 0,35 USD/ordre ; emprunt SHORT 1 %/360, minimum un jour |
| Friction adverse | Principal 0,01 USD/action/côté ; stress prédéfini 0,02, 0,03 et 0,05 |

Le rendement du matin inclut l'overnight ; `close_09:59 / open_09:30 - 1` serait une autre hypothèse. La sortie à 15:59 et les données ETF sont des choix de notre protocole : une réplication exacte aux enchères de clôture ou sur futures ne sera pas revendiquée.

Toutes les entrées nécessitent les minutes complètes servant au signal, au dimensionnement et à l'exécution, ainsi que la dernière séance NYSE précédente valide. Aucun remplissage de trous. Publier le nombre et les dates des séances exclues. Ne pas utiliser le volume final ou le prix de clôture pour décider l'entrée à 15:30. Contrôler splits, ex-dividendes et heure d'été.

## Évaluation prévue

Période A : début de l'historique commun vérifié à avril 2024 ; période B : mai 2024 au 16 octobre 2026. Ces périodes ont déjà servi aux études précédentes : B sera présenté comme **historique exploratoire réutilisé**, pas comme un échantillon vierge. Les futures observations après gel du protocole seront distinguées.

Publier tous les instruments et les quatre frictions, plus un diagnostic LONG seul à friction principale (10 scénarios au total). Mesurer résultat net, rendement annualisé, drawdowns quotidien et minute, nombre de transactions, exposition, répartition LONG/SHORT, coûts, résultats annuels et concentration des meilleurs jours. Ajouter l'ablation des trois meilleurs jours et une incertitude tenant compte des dépendances temporelles ; ne pas présenter un bootstrap avec trop peu d'années comme une preuve forte.

Comparer à une position LONG systématique sur le même créneau et au rendement du signal opposé, avec les mêmes quantités et frais. Ces références diagnostiques seront publiées séparément, sans les intégrer à un choix rétrospectif du meilleur modèle. Examiner manuellement des transactions gagnantes et perdantes, ex-dividendes et demi-séances. Tester causalité, décalage des prix, coûts, absence d'overnight et absence de fuite future.

Critère pour poursuivre en simulation : avantage net qui résiste aux coûts plus élevés, ne repose pas seulement sur quelques jours ou un seul régime, et reste crédible face aux références. Si ce n'est pas le cas, archiver le résultat négatif sans multiplier ensuite les filtres. Aucun passage en argent réel n'est prévu dans cette étude.

Une extension utilisant le rendement jusqu'à 15:29 sera une étude distincte, avec son propre gel de règles et une entrée tenant compte du délai de publication de cette minute. Elle ne sera pas introduite après coup comme une correction de l'hypothèse principale.

## Reproduction

Python 3.14.6, avec les caches préparés de confiance et les CSV bruts locaux déjà acquis pour Noise Area. Les chemins et empreintes sont contrôlés ; aucun téléchargement, clé ou compte connecté n'est nécessaire. Les données complètes restent ignorées par Git. Depuis ce dossier :

```powershell
python -m pip install -r requirements.txt
python -m pytest -q --basetemp=.test_tmp_local
python scripts/run_study.py --out results/nouvelle-execution --rerun-reason "Reproduction sans modification des regles"
python scripts/audit_results.py --out results/nouvelle-execution
python scripts/validate_outputs.py --out results/nouvelle-execution
python scripts/write_report.py --out results/nouvelle-execution
```

Un dossier d'exécution existant n'est jamais écrasé par `run_study.py`. Les témoins à quantités communes et les limites d'exécution aux opens sont détaillés dans le rapport ; ils ne sont pas des ordres exécutés. Les contrôles qualité et résultats peuvent aussi être consultés dans le [notebook de synthèse](notebooks/quality_and_results.ipynb).
