# QQQ Paper Bot Implementation Plan

> **For agentic workers:** utiliser `superpowers:executing-plans`, tâche par tâche. La demande explicite de l'utilisateur autorise l'implémentation et la publication du bot de simulation décrit dans DESIGN.md.

**Goal:** suivre prospectivement QQQ Noise Area dans Alpaca paper et/ou shadow avec coûts conservateurs et traces reproductibles.

**Architecture:** calcul causal partagé avec le décideur historique figé ; adaptateur HTTP paper borné ; état SQLite et ledger net locaux. Pas de modification des sources ou résultats des études précédentes.

**Tech Stack:** Python 3.14, bibliothèque standard, pandas/numpy/exchange-calendars déjà figés dans l'étude.

**Spec:** [DESIGN.md](DESIGN.md).

## Global Constraints

- QQQ, lookbacks 14/14, décisions 30 minutes, cible 0,02, cap cible 4, capital virtuel 100 000 USD.
- Endpoint paper fixe ; aucun hôte de trading réel ; aucune clé sur disque ou dans Git.
- Commission 0,0035/action/côté, minimum 0,35/ordre ; buffer 0,01 ; emprunt 0,01/360 par SHORT fermé.
- IEX exige un choix explicite, SIP périmé ne déclenche aucun ordre paper.
- Historique, tests et résultats des études existantes préservés.

## Review Focus

Timeout après ordre accepté ; fill partiel puis annulation ; redémarrage avec position ; minute de clôture manquante ; mauvais flux ou calendrier. Chaque cas doit avoir un test et un statut explicite.

## Tâches

1. **Calcul causal** (`strategy.py`, `tests/test_strategy.py`) : tests rouges des fenêtres, préfixes, volatilité, dividendes, quantité et demi-séance ; implémenter puis vérifier vert.
2. **Ledger durable** (`ledger.py`, `tests/test_ledger.py`) : tests rouges des commissions cumulées, emprunt, ordre rejoué, quantité partielle et configuration incompatible ; implémenter puis vérifier vert.
3. **API paper et exécution** (`alpaca.py`, `runner.py`, tests dédiés) : tests rouges d'hôte refusé, timeout sans réenvoi aveugle, renversement séquentiel, fermeture et données anciennes ; implémenter puis vérifier vert.
4. **CLI et preuve réelle** (`__main__.py`, `scripts/replay_parity.py`, lanceur PowerShell) : tests des paramètres et un replay des prix QQQ archivés ; connexion uniquement après saisie sécurisée des clés paper.
5. **Piste suivante** : documenter une hypothèse de retour à la moyenne après gap d'ouverture, sources primaires et protocole non optimisé ; aucun résultat inventé et aucune fusion automatique avec le bot.
6. **Livraison** : tests complets bot + étude, audits d'intégrité, revue indépendante, documentation du statut d'activation, scan des fichiers puis commit et ajout à main.

Les cases de réalisation et preuves seront consignées dans VALIDATION.md après exécution, sans prétendre qu'une connexion ou un ordre a eu lieu avant observation.
