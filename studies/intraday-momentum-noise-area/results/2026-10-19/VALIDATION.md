# Validation de la livraison Noise Area

L'étude a réellement exécuté **220 scénarios** sur des acquisitions OHLCV 1 minute réelles. Les performances s'arrêtent le **16 octobre 2026**. Les données artificielles servent uniquement aux tests unitaires.

| Vérification | Résultat observé | Pièce |
|---|---|---|
| Tests critiques Python | **32 passés en 9,15 s**, dernière exécution de livraison ; aucune alerte | `python -m pytest -q --basetemp=.test_tmp_delivery` |
| CSV vs pages JSON d'acquisition | 4 258 678 lignes rapprochées, hashes vérifiés | [DATA_VALIDATION.json](DATA_VALIDATION.json) |
| Nouvelle préparation intégrale | Six fichiers préparés aux hashes exactement identiques | [DATA_REPRODUCTION_VALIDATION.json](DATA_REPRODUCTION_VALIDATION.json) |
| Exports | 220 scénarios : sommes des trades, comptes quotidiens, capital final et composition rapprochés | [AUDIT_HISTORIQUE.json](AUDIT_HISTORIQUE.json) |
| Signaux et P&L indépendants | 32 principaux, 335 136 décisions et 24 352 lignes de trades, calcul scalaire séparé du moteur | [Audit historique](AUDIT_HISTORIQUE.json) |
| Risque et exposition | 11 218 144 marques, P&L et drawdown minute rapprochés ; écart de ledger maximal inférieur à 0,000001 USD | [INTRADAY_RISK_AUDIT.json](INTRADAY_RISK_AUDIT.json) |
| Examen historique détaillé | Quinze transactions, dont dix premières chronologiques ; contrôle des seuils, VWAP, quantités, sorties et P&L | [EXAMEN_MANUEL.md](EXAMEN_MANUEL.md) |
| Incertitude | 5 000 bootstrap par blocs de cinq séances ; 1 000 directions aléatoires à horaires conditionnels | [IC coûts B](UNCERTAINTY_B_COSTS.json), [D](POST_REVISION_VALIDATION.json), [SPY passif](B_VS_SPY_PASSIVE.json) |
| Figures | 73 PNG produits depuis les exports ; synthèse et échantillons détaillés examinés visuellement | [FIGURES_PROVENANCE.json](FIGURES_PROVENANCE.json) |
| Intégrité du projet précédent | 1 977 fichiers d'import FVG aux SHA-256 identiques | `python tools/verify_snapshot.py`, depuis la racine du dépôt |
| Pine v6 | Compilation réelle et sauvegarde privée ; zéro trade sur l'historique accessible | [Statut TradingView](../../tradingview/README.md) |

Les fenêtres passées, l'exclusion du jour courant, les perturbations de prix futurs, VWAP causal, DST, demi-séances, doublons, trous, références ex-dividende, décision sur minute terminée, exécution close/open suivant, coûts minimaux, emprunt, retournements, quantités nulles et absence d'overnight disposent de tests contrôlés. L'audit historique indépendant partage seulement le cache OHLCV préalablement rapproché des acquisitions.

Une revue indépendante n'a trouvé aucun défaut matériel de causalité ou de P&L. Elle a fait ajouter les hashes des fichiers préparés au script de préparation, puis une reproduction intégrale ; elle a aussi fait distinguer la durée du drawdown quotidien de celle du drawdown minute et compléter le levier effectif pondéré par les minutes détenues. Aucun paramètre principal, signal ou résultat de marché n'a été modifié en conséquence.

Le code du moteur et le protocole ont les mêmes hashes que lors de l'exécution. Les ajouts de rapport, d'audit, de figures et de provenance sont distincts. Quatre lignes de diagnostic « gap non ajusté » utilisent la valeur de cache interne `lookback=99` ; la fenêtre calculée est **14**, sans incidence sur le P&L. [Annotation des métadonnées](OUTPUT_METADATA_NOTES.json).

La validation ne démontre pas les remplissages réels, la disponibilité de l'emprunt, un plafond dur de marge ni une concordance annuelle Pine/Python. La sélection de séances entièrement complètes est effectuée après acquisition et retire notamment quatre jours d'interruptions de marché de mars 2020 ; la couverture A est donc partielle. B commence avant la première publication, et le PDF consulté est une révision de 2025 : C et D sont présentées séparément. Ces réserves restent dans le [rapport](RAPPORT_FINAL.md), indépendamment de la réussite technique des tests.

Le [contrôle final de livraison](FINAL_VALIDATION.json) vérifie aussi les hashes des figures, du rapport, des sources figées, les liens locaux et la syntaxe des scripts. L'[inventaire SHA-256](DELIVERY_FILES_SHA256.json) couvre les fichiers livrés hors données minute. Les résultats restent locaux ; aucun envoi GitHub n'a été effectué.
