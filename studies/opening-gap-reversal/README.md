# Opening Gap Reversal — backtest

**Statut au 20 octobre 2026 : backtest terminé, 54 scénarios et 20 tests ; rapport de référence v3. QQQ mérite un suivi virtuel, preuves insuffisantes pour un bot autonome. La stratégie ne passe aucun ordre.**

[Rapport complet](results/2026-10-20-v3/RAPPORT_FINAL.md) · [54 scénarios](results/2026-10-20-v3/comparison_all.csv) · [Audit indépendant](results/2026-10-20-v3/AUDIT_INDEPENDANT.json) · [Validation](VALIDATION.md).

Sur B (01/05/2024–16/10/2026), cible 1x et friction 0,01 USD/action/côté plus frais : QQQ +8,47 % avec 18 trades ; SPY +1,32 % avec 11 trades. B est une comparaison chronologique exploratoire sur un historique réutilisé. Les faibles échantillons et la concentration des gains empêchent de conclure à un avantage robuste.

Le [protocole d’exécution](PROTOCOL_EXECUTION.md) précise avant P&L le traitement des bornes observées et suspensions. Le profil principal donne 48 événements SPY /83 QQQ sur ALL ; le filtre historique de journées complètes ci-dessous reste une sensibilité, avec 42 /77. Les comptes B sont identiques.

Après un grand écart entre la clôture précédente et l'ouverture, tester une position opposée au gap pendant la première demi-heure. Cette logique de retour à la moyenne explore un comportement différent de la poursuite de mouvement de Noise Area. Sa complémentarité financière reste à mesurer.

## Source et adaptation causale

Le [code publié par Concretum Group](https://concretumgroup.com/backtesting-7-years-of-free-data-beat-the-market-an-effective-intraday-momentum-strategy-for-the-sp500-etf-spy/) contient une composante de gap reversal : seuil absolu de 2 %, sens opposé au gap, sortie après la première demi-heure. La source la combine avec la stratégie de momentum ; une performance de leur combinaison ne prouve pas celle du reversal isolé.

La source suppose une entrée au prix d'ouverture qui sert aussi au calcul du signal. Notre protocole attend la fin de la minute 09:30 puis entre à **09:31**, et sort à **10:00**. C'est une adaptation explicite pour respecter l'information disponible, pas une reproduction exacte de l'entrée originale.

## Protocole fixé avant calcul du P&L

1. Instruments : SPY et QQQ évalués séparément, données Alpaca SIP raw, heures régulières de New York.
2. Gap : `open_09:30 / (close_RTH_précédent - dividende_ex_date) - 1`. Ne pas traiter le détachement du dividende comme un signal.
3. Condition unique : `abs(gap) > 0,02`. Acheter après un gap négatif ; vendre à découvert après un gap positif.
4. Connaître le signal à 09:31 ; entrer à l'open 09:31 ; sortir à l'open 10:00. Un seul trade par séance, sans maintien overnight. Aucune entrée si les minutes nécessaires ou la clôture précédente ne sont pas valides.
5. Capital initial 100 000 USD ; exposition principale 1x, actions entières, capital recomposé. Aucun levier 4x dans la première comparaison.
6. Commission 0,0035 USD/action/côté, minimum 0,35 USD/ordre, emprunt SHORT 1 %/360 minimum un jour. Scénarios de friction adverse 0,01 / 0,02 / 0,03 / 0,05 USD/action/côté. Ce sont des hypothèses à confronter aux coûts observés.
7. Première version sans objectif de gain ni stop ajouté après observation. Mesurer la perte adverse intratrade, les pertes extrêmes, jours de suspension et ouvertures perturbées ; ne pas considérer un open comme exécutable pendant un halt.
8. Aucun balayage de seuil ou d'horaire avant ce test fixé. Une modification ultérieure sera une nouvelle hypothèse et ne bénéficiera pas d'un nouveau label hors échantillon sur le même historique.

## Faisabilité réellement calculée

Le script [count_events.py](scripts/count_events.py) a seulement compté les gaps de plus de 2 %, avec les données préparées déjà utilisées dans Noise Area. Les empreintes sources et dates sont dans [la preuve JSON](evidence/feasibility_2026-10-20.json).

| Instrument | 2016–16/10/2026 : événements / séances utilisables | A : jusqu'au 30/04/2024 | B : 01/05/2024–16/10/2026 |
|---|---:|---:|---:|
| SPY | 42 / 2 696 | 31 / 2 078 | 11 / 618 |
| QQQ | 77 / 2 700 | 59 / 2 082 | 18 / 618 |

Ces nombres ne sont ni des trades exécutés, ni des résultats de stratégie. Le filtre de journées complètes de l'étude exclut notamment plusieurs séances avec halts de mars 2020 ; les comptes sont conditionnels à cet univers. Le backtest v3 audite explicitement ces séances et distingue les exclusions de qualité des bornes sans prix exécutable.

Le faible nombre d'événements, surtout en B, est une limite forte de puissance statistique. Ne pas abaisser le seuil après ce constat uniquement pour obtenir davantage de trades. Le comptage initial ne calculait aucun rendement ; le backtest et ses limites sont maintenant publiés séparément dans la référence v3.

## Validation effectuée et limites

Les périodes A et B ci-dessus servent de comparaison chronologique exploratoire. L'historique a déjà été étudié pour d'autres stratégies et le comptage vient d'être consulté : **B ne sera pas présenté comme un nouveau test aveugle**. Le protocole est daté du 20 octobre ; une observation prospective intacte peut commencer le 21 octobre 2026.

Les exports publient pour chaque instrument et coût les trades détaillés, P&L net, drawdown, pertes, exposition, nombre de trades par année et par sens, concentration des gains et incertitude des moyennes. Les témoins cash et dans le sens du gap ainsi que les corrélations avec Noise Area sont publiés, sans supposer de diversification.

Les intervalles regroupent les événements par année et leur faible nombre limite fortement leur portée. Un faible échantillon positif sera une piste à suivre, pas une preuve suffisante pour lancer un bot. La stratégie n'est pas intégrée au bot QQQ livré.

## Reproduire uniquement le comptage

Avec les dépendances et les pickles locaux de l'étude Noise Area :

```powershell
python studies/opening-gap-reversal/scripts/count_events.py
```

Les historiques minute et pickles restent locaux et ignorés par Git. Ne charger que des pickles de confiance.

## Installation et reproduction du backtest

Python 3.14.6, depuis ce dossier :

```powershell
python -m pip install -r requirements.txt
python -m pytest -q --basetemp=.test_tmp_local
python scripts/run_study.py --out results/nouvelle-execution --rerun-reason "Reproduction sans modification des paramètres"
python scripts/audit_results.py --out results/nouvelle-execution
python scripts/write_report.py --out results/nouvelle-execution
```

Les scripts nécessitent les caches préparés locaux de Noise Area et vérifient leurs hashes avant calcul. Le rapport compare aussi avec les résultats Noise Area existants et la première exécution Gap Reversal archivée. Aucun téléchargement ni clé API ne sont nécessaires pour ce backtest. Une exécution ne remplace pas un dossier de résultats existant.
