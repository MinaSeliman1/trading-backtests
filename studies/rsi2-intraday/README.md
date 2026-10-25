# RSI(2) intraday SPY / QQQ

**Backtest terminé, formalisation écartée pour un bot.** Référence LONG au plafond1x après les mêmes coûts ETF : ALL SPY−5,47%/1591trades, QQQ−17,18%/1713trades ; A et B négatives.72scénarios fixés à l’avance,25tests et audit indépendant complet. La variante seuil10 positive en B reste négative en A et sur ALL ; elle ne remplace pas la référence après observation.

- [Rapport complet, coûts, périodes, sensibilités et quatre figures](results/2026-10-24-v1/RAPPORT_FINAL.md)
- [Toutes les72comparaisons](results/2026-10-24-v1/comparison_all.csv)
- [Validation et audit](VALIDATION.md)
- [Protocole figé avant performances](PROTOCOL_EXECUTION.md)
- [Bilan actuel des pistes et des deux bots QQQ](../../docs/research/2026-10-24-pistes-et-bots.md)

Adaptation exploratoire des idées RSI de Connors, pas une reproduction de sa stratégie journalière. Retour à la moyenne5min, filtre200closes RTH antérieurs corrigés du cash connu, stop2ATR14 et sortieRSI70 ou EOD ; risque cible1%, plafond causal1x. Commission0,0035USD/action/côté minimum0,35, friction0,01/côté, empruntSHORT1%/360. Données SIP déjà acquises jusqu’au16octobre2026 ; B déjà étudiée, aucun nouvel OOS aveugle.

## Reproduction

Python3.14 et versions dans requirements-lock.txt. Depuis ce dossier :

```powershell
python -m pip install -r requirements-lock.txt
python -m pytest -q -p no:cacheprovider --basetemp=.test_tmp_rsi2
python scripts/verify_delivery.py
python scripts/verify_delivery.py --raw
python scripts/run_study.py --out results/nouvelle-execution
python scripts/report.py --out results/nouvelle-execution
```

La vérification standard fonctionne sur le dépôt sans données brutes. Le runner, l’audit et --raw exigent les archives/préparations SIP des études antérieures, ignorées par Git. Les fichiers bruts ne sont pas téléchargés par ces commandes, aucune clé n’est nécessaire. Le runner refuse un dossier de résultats existant. Les scripts dépendent de modules historiques voisins ; leurs empreintes et copies sont conservées dans le gel et dependency_snapshot.

Les résultats complete_days sont conditionnels à un filtre de qualité connu après séance. resolved_prefix publie séparément les journées/trades incomplets et les coûts d’entrée connus ; aucune interpolation, aucune prétention de portefeuille continu sur journées inconnues. Tous les scénarios gardent leur compte indépendant.

Les bots Noise Area et ORB restent séparés, inchangés, et simulent localement sur SIP différé16minutes. Aucun bot RSI ou SPY n’est installé, aucun ordre envoyé. Le bilan des bots est une lecture seule datée, pas leur performance future.
