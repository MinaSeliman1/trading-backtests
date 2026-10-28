# Cassure puis premier retest confirmé — SPY et QQQ

**Cette formalisation n’est pas retenue pour un nouveau bot.** Après les mêmes frais, les références perdent sur la période complète du4janvier2016 au16octobre2026. QQQ gagne sur B, mais perd sur A et sur ALL ; quatre des cinq critères prédéfinis échouent.

| ETF | Trades ALL | Net cumulé | CAGR | Profit factor | DD observé |
| --- | --- | --- | --- | --- | --- |
| SPY | 497 | -6,16 % | -0,59 % | 0,853 | 8,80 % |
| QQQ | 509 | -5,50 % | -0,52 % | 0,907 | 10,71 % |

Capital initial de100000USD indépendant par ETF et scénario. Comptes conditionnels aux données résolues ; DD aux coûts d’entrée, closes minute détenus et sorties, sans borne de tous les ticks. B, du1mai2024 au16octobre2026, a déjà été explorée : ce n’est pas un nouveau hors-échantillon aveugle.

- [Rapport complet, coûts, incertitude et quatre figures](results/2026-10-28-v1/RAPPORT_FINAL.md)
- [Décision et interprétation](INTERPRETATION.md)
- [72scénarios réellement calculés](results/2026-10-28-v1/comparison_all.csv)
- [Recherche Web et limites des sources](RESEARCH.md)
- [Protocole fixé avant performance](PROTOCOL_EXECUTION.md), [gel/code/source](results/2026-10-28-v1/PRE_EXECUTION_PROTOCOL.json)
- [42tests, revue et audit indépendant](VALIDATION.md)

## Hypothèse testée

Fixer le haut/bas des15premières minutes RTH, puis attendre la première clôture5minutes qui casse ce range. Sur le premier toucher ultérieur, dans6bougies maximum, exiger maintien extérieur en clôture et corps dans le sens. Un premier toucher raté annule la journée. Entrée open suivant09:55–11:30NY, stop à la mèche du retest±0,01USD, objectif2R, une entrée/jour, sortie dernier open de séance. Sizing au close du signal : risque cible1%, plafond1x ; gaps et frais peuvent augmenter le risque effectif.

Commission0,0035USD/action/côté minimum0,35 ; friction0,01USD/action/côté ; empruntSHORT1%/360 minimum1jour. Stress de friction0,02/0,03/0,05 et sensibilités de délai, objectif, direction, sans retest et qualité, toutes publiées sans choisir un gagnant après calcul.

Le contrôle sans retest utilise un range15minutes et objectif2R ; il diffère du bot ORB5minutes/10R actuellement installé. Il change aussi stops, sizing, nombre de trades et exposition, donc ne mesure pas un effet causal propre à l’attente. Les deux simulations existantes restent inchangées.

## Reproduction locale

Python3.14 et dépendances exactes dans [requirements-lock.txt](requirements-lock.txt). Les tests sont synthétiques et n’utilisent aucune API. Le run exige les archives locales vérifiées déjà décrites dans l’étude Noise Area, exclues deGit ; le dépôt seul ne contient pas l’historique sous licence.

```powershell
python -m pytest tests -q --basetemp .test_tmp_local
python scripts/run_study.py --out results/nouvelle_execution
python audit/independent.py --out results/nouvelle_execution
python scripts/report.py --out results/nouvelle_execution
```

Choisir un dossier neuf : aucun écrasement d’exécution. L’audit vérifie séparément le range, l’automate et chaque compte. `python scripts/verify_delivery_v2.py --raw` contrôle la livraison datée et ses empreintes ; le manifest ne porte que sur cette étude, pas sur le registre global évolutif.
