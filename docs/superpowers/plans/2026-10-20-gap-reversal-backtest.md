# Opening Gap Reversal Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans for inline execution. The user explicitly requested execution of the published protocol; no renewed design authorization is needed.

**Goal:** évaluer les gaps >2 % avec une exécution causale 09:31–10:00, puis publier les preuves et conclusions.

**Architecture:** cache SIP validé en lecture seule ; moteur isolé par étude ; script reproductible de 54 scénarios ; audit indépendant et rapport Markdown avec figures exportables.

**Tech Stack:** Python 3.14.6, numpy/pandas/matplotlib/exchange-calendars figés dans Noise Area.

**Spec:** studies/opening-gap-reversal/README.md et PROTOCOL_EXECUTION.md.

## Global Constraints

- SPY/QQQ, strict >2 %, 09:31–10:00 New York, quantité entière sur open 09:30, exposition cible 1x.
- Frictions 0,01/0,02/0,03/0,05 ; commission 0,0035 minimum 0,35 par ordre ; emprunt SHORT 1 %/360.
- Aucun changement du bot, aucune réécriture des anciennes études ; aucun historique brut ou secret dans Git.
- B exploratoire et rareté des signaux explicites ; garder les bornes observées des séances avec trous intermédiaires.

## Review Focus

- Seuil exactement ±2 % : aucun signal malgré l'arrondi flottant du ratio.
- Dividende et demi-séance précédente : prendre la bonne référence, jamais une autre date.
- Suspension avant/après 10:00 : distinguer bornes manquantes, trou intermédiaire et journée complète.
- Causalité : le signal et la quantité ne dépendent ni du prix futur d'entrée ni de la suite de la journée.
- Ledger : minimum de commission, emprunt, compounding, absence de trades et insolvabilité.

## Tâches

1. [x] Créer les tests rouges `tests/test_engine.py` des cinq risques ci-dessus, puis `gap_reversal/engine.py` avec Config, prepare(market, dividends, profile) et simulate(market, prepared, config, start, end). Vérifier la suite verte.
2. [x] Ajouter tests rouges des agrégats et du bootstrap annuel, puis `gap_reversal/analysis.py`. Garder les périodes initialisées séparément et les années sans événement.
3. [x] Créer `scripts/run_study.py` : vérifier les hashes sources, écrire PRE_EXECUTION_PROTOCOL.json avant simulation, exporter les 54 scénarios et la qualité. Lancer les vraies données sans écraser un dossier d'exécution.
4. [x] Auditer tous les trades indépendamment des helpers du moteur, rapprocher les anciens comptes complete_days, vérifier les suspensions et la comparaison Noise Area.
5. [x] Revue indépendante du moteur et des preuves ; corriger les défauts démontrés avec régressions. Rapport complet, figures contrôlées visuellement, registre et statut exacts.
6. [x] Tests de l'étude + intégrité des archives, vérification des fichiers/empreintes/liens, commit et publication demandée dans trading-backtests. Vérifier aussi que le bot reste actif et répondre à la question sur son fonctionnement local.

## Journal

Ruling: le profil principal utilise les bornes nécessaires et conserve les trous intermédiaires — un filtre de journée complète excluait des crises sur des informations postérieures au trade. Le profil complet reste une sensibilité explicite ; aucun P&L n'a été consulté lors de cette précision.

Résultat : 20 tests verts ; 54 scénarios dans chacune des versions v1/v2/v3 ; audit final de 2 334 lignes, erreur monétaire maximale 4,42e-11 USD. Trois défauts de précision corrigés après revue sans changer le P&L. V3 est la référence. Bot observé actif en shadow/SIP pendant le travail ; aucune modification de son code.
