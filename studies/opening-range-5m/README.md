# ORB cinq minutes — SPY et QQQ

**Backtest terminé le 20 octobre 2026 : 54 scénarios, 42 tests, audit indépendant et rapport complet.** Aucun ajout au bot Noise Area actif. [Rapport](results/2026-10-20/RAPPORT_FINAL.md), [comparaisons](results/2026-10-20/comparison_all.csv), [validation](VALIDATION.md).

À coûts de base, QQQ principal : **+50,93 % ALL / +7,76 % B**, 2 688 /615 trades ; SPY : **+1,40 % ALL / −0,84 % B**, 2 679 /615 trades. Ce sont des comptes historiques conditionnels à la couverture source, pas une performance continue déployable sur toutes les journées. B réutilise l'historique étudié précédemment. QQQ mérite une recherche prospective, mais ses trois meilleurs jours B et les frais rendent le résultat fragile ; pas de nouveau bot justifié.

Hypothèse : le mouvement des cinq premières minutes se prolonge suffisamment pour rémunérer un stop défini par la première plage. [Zarattini et Aziz, définition de la stratégie, pp. 4–6](https://concretumgroup.com/wp-content/uploads/2026/02/Can-Day-Trading-Really-Be-Profitable.pdf) étudient une version simplifiée ORB : direction de la première bougie, entrée à la suivante, stop à l'extrême opposé, objectif 10R. Notre test l'adapte à SPY/QQQ non levierisés, aux coûts déjà utilisés et à la disponibilité de l'information ; aucune performance publiée n'est revendiquée comme nôtre.

Le détail figé figure dans [PROTOCOL_EXECUTION.md](PROTOCOL_EXECUTION.md). Principaux choix : signal open 09:30 vers close 09:34 ; entrée open 09:35 ; risque cible 1 % du capital, exposition plafonnée à 1x ; taille basée sur close 09:34 et extrêmes 09:30–09:34, connus avant entrée. Stop fixe, objectif 10R calculé après constat du fill ; sortie au premier événement ou open 15:59 (12:59 en demi-séance). Un trade maximum par séance, sans overnight.

Capital initial 100 000 USD. Mêmes coûts : 0,0035 USD/action/côté, minimum 0,35 USD/ordre ; friction adverse 0,01 USD/action/côté, stress 0,02/0,03/0,05 ; emprunt SHORT 1 %/360 avec un jour minimum. Le plafond 1x, les frais, le capital, le prix causal de dimensionnement et la sortie avant clôture diffèrent du papier source ; ceci n'est pas une réplication exacte.

**Qualité : les résultats sont conditionnels aux séances dont l'exécution est observable.** Un stop nécessite des minutes intermédiaires exploitables. Le profil principal utilise les séances intégrales validées, filtre de recherche connu après coup, non déployable à l'ouverture. Une sensibilité observe seulement le préfixe jusqu'à la sortie et conserve les séances qui deviennent incomplètes ensuite ; un trou avec position active est déclaré non résolu. Aucun trou n'est interpolé ou assimilé automatiquement à une suspension. Un solde calculé en omettant ces séances ne représente pas le portefeuille réel qui les aurait traversées.

ALL : 04/01/2016–16/10/2026 ; A jusqu'au 30/04/2024 ; B du 01/05/2024 au 16/10/2026. Capital réinitialisé séparément par période. B réutilisée reste exploratoire, sans nouveau label de validation aveugle. Le gel original du protocole, des données et du code précède les calculs ; README et précision éditoriale ont ensuite été mis à jour pour présenter les résultats, sans modification numérique.

## Reproduire

Depuis ce dossier, avec les dépendances de `requirements.txt` et les caches SIP locaux de l'étude Noise Area aux empreintes indiquées dans le profil :

```powershell
python -m pytest -q --basetemp=.test_tmp_local
python scripts/run_study.py --out results/ma-nouvelle-execution
python scripts/audit_independent.py results/ma-nouvelle-execution
python scripts/validate_outputs.py results/ma-nouvelle-execution
python scripts/write_report.py results/ma-nouvelle-execution
```

Les preuves de livraison de référence peuvent être revérifiées par `python scripts/verify_delivery.py`. Le manifest final couvre les fichiers de l'étude, et le manifest initial permet de confirmer que les ajouts d'audit/rapport n'ont changé aucune sortie financière. Les versions directes des bibliothèques sont dans `requirements-lock.txt` ; `BUILD_EVIDENCE.json` trace l'environnement réellement utilisé.

Le lanceur refuse d'écraser un dossier non vide. Les tests utilisent des cas synthétiques hors données de performance. L'audit recalcule 85 526 lignes recouvrantes et 9 282 328 marks sans appeler le moteur ; frais, P&L et capital sont rapprochés à la tolérance publiée de 3×10⁻⁶ USD, avec écarts mesurés distincts par unité. Seize transactions sont illustrées par 112 références OHLCV relues dans les fichiers bruts. Les historiques complets, pickles et clés restent locaux ; seuls des extraits limités et résultats dérivés sont publiés.

Les helpers de chargement/calendrier et de statistiques des études précédentes sont réutilisés sans modification, avec empreintes et versions conservées. Aucune connexion Alpaca n'est nécessaire au calcul avec caches présents ; les identifiants déjà protégés Windows ne doivent pas être transmis dans le chat.
