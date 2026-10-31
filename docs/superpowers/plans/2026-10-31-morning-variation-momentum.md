# Morning variation momentum implementation plan

> Use executing-plans for task-by-task work and requesting-code-review before publication.

**Goal:** Nouvelle piste QQQ/SPY, frais identiques, rÃ©sultats publiÃ©s et bots inchangÃ©s.
**Architecture:** Score de parcours matinal, quantile empirique appris seulement du passÃ©, une entrÃ©e/ETF10:31 et sortie mÃªme jour,1x sans stop. ArchivesSIP locales, aucun transport broker.
**Tech stack:** Python3.14,numpy,pandas,pytest,matplotlib,XNYS.
**Spec:** studies/morning-variation-momentum/PROTOCOL_EXECUTION.md.

## Contraintes et revue

Deux comptes100000, LONG seul, tailles entiÃ¨res avant fill, commission0.0035/action/cÃ´tÃ© min0.35, friction0.01/action/cÃ´tÃ©. Sources/trades diffÃ©rents des quote-midpoints de l'article. A/B rÃ©utilisÃ©es et couverture conditionnelle. VÃ©rifier grille exacte, RVsans overnight, quantile sans jour courant, warmup/panel, demi-sÃ©ances, exÃ©cution sans stop et coÃ»ts uniques.

- [x] Lire sources/pistes existantes et figer protocole/recherche avant PnL,14variantes/84comptes et critÃ¨res.
- [x] Tests rouges puis moteur minimal et verts ; revue des features/fills avant PnL.
- [x] Runner financier avec gelSHA, source vÃ©rifiÃ©e,84scÃ©narios et exports.
- [x] Oracle scalaire indÃ©pendant, contrÃ´les numÃ©riques/IC et revue.
- [ ] Rapport/figures/validation/interprÃ©tation, manifest et registreREADME ; publication atomique avec garde main.

## Ledger

Ruling : conserver l’autonomie et la publication explicitement demandées ; aucune nouvelle approbation de conception nécessaire. Recherche strictement hors des bots.

37tests initiaux échouent sur stub. Fixtures corrigées avant PnL : les anciens rendements alternés avaient involontairement la même pente sur la grille2min ; le helper de bougie écrasait les extrêmes explicites. Aucun réglage stratégique issu de ces corrections.

Revue avant PnL : invalid_ohlcv après-midi effaçait un matin valide. Deux régressions rouges observées, puis correction et42tests verts. Conflits/décalages globaux restent rejetés. Oracle et protocole examinés avant calcul.

84comptes après gel financier SHA, aucune règle changée après résultats. Scripts de présentation/contrôles ajoutés ensuite conformément au §12. A/B exploratoires réutilisées.

Revue finale indépendante :42tests relancés,10fichiers gelés/15dépendances/463exports et84résumés vérifiés,4PNG inspectés. Instructions UTF-8 Windows corrigées ; transcription lisible de recherche ajoutée en préservant l’original gelé. Aucune règle financière modifiée.
