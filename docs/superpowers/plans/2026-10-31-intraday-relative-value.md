# Intraday relative-value implementation plan

> For agentic workers: use executing-plans task-by-task; review through requesting-code-review.

**Goal:** Tester puis publier une nouvelle piste sur QQQ/SPY, mêmes frais, sans toucher aux bots actifs.
**Architecture:** Un portefeuille deux jambes dollar-neutre ; calibration même créneau sur passé seulement, exécution close-based next-open, coûts par jambe. Modules ne disposent d’aucun accès API/coffre/runtime.
**Tech Stack:** Python3.14, numpy/pandas, calendrier XNYS, pytest, matplotlib.
**Spec:** studies/intraday-relative-value/PROTOCOL_EXECUTION.md

## Global constraints

Comptes100000USD, gross cap1x, proxy risque1%,4commissions0.0035/action min0.35, friction0.01/action/côté et short1%/360minimum1jour. RTH flatEOD ; A/B réutilisées, exclusions conditionnelles. Aucun bot ajouté.

## Review focus

Alignement des deux calendriers ; ordre causal closes/opens ; demi-séances dans calibration ; quatre frais et allocation par jambe ; trous actifs sans faux cash ou saut de signal.

- [x] Recherche/prior art et protocole avant PnL,14variantes/42comptes, critères de présélection.
- [x] Tests rouges de prepare/choose/execute/simulate : historiques, gaps, horaires, dollars, coûts4ordres, stopclose et inconnus.
- [x] Moteur minimal puis tests verts ; revue indépendante avant PnL.
- [x] Runner : gel SHA,42scénarios, exports portfolio/trades/legs/daily/unresolved, profil des sources.
- [x] Oracle scalaire indépendant et recalcul des frais/comptes ; revue chiffres/rapports/figures.
- [x] Rapport Markdown, figures, validation, sources, manifest et README ; publication gardée sur main.

42comptes calculés,41tests verts ; oracle1 972 227contrôles,statistiques378checks+6IC,revue4PNG. Toutes les références/variantes négatives, seul critère de fréquence passe. Modèle figé intact ; publication après contrôle du manifest et périmètre Git.
