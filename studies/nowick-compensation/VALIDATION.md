# Validation — 24 octobre 2026

## Périmètre livré

Deux stratégies Pine v6 natives (mêmes règles, frais USD/JPY distincts), marqueurs et niveaux, ordres limites et bracket SL/TP figés, filtres, taille1% du risque de prix, tableaux natif/stress et Wilson95%. Documentation des conventions et du plan de100trades par paire. Rentabilité **non évaluée**.

## Vérifications réellement effectuées

- TDD : le premier lancement des tests a échoué sur l'absence de `reference.py`, avant son implémentation.
- **27tests unitaires Python passent** : pips/ticks, coût1pip dans les deux devises, risque et arrondi, Nowick/tolérance, confirmation de pivot sur fixture sans égalités, structure, TTLexact, DSThiver/été, news datées/chevauchements/rejets, S/Rstrict, Double2–4, seuil d'équilibre, Wilsonvide/extrêmes/50sur100, stress et drawdownRfermé ; quatre cas supplémentaires de fills contigus, hors session, news dans la bougie et trou interséances.
- Les fichiers USD et JPY coïncident exactement après les quatre substitutions déclarées par `build_variants.py`.
- Une revue indépendante en lecture seule a trouvé un `=>` manquant dans la déclaration d'une méthode Pine ; il a été corrigé avant publication. Elle a demandé une garde du fill sur **toute la bougie**, ajoutée pour refuser une bougie chevauchant une news. Une garde supplémentaire refuse tout nouveau fill immédiatement après un trou de données, y compris si son heure serait admissible mais que l'ordre aurait traversé une fin de session absente. Le warm-up200heures de l'EMA est mémorisé avec l'heure confirmée.
- Relecture finale : les limites non remplies sont aussi annulées sur la première bougie après un trou ; les clôtures partielles ou hors identifiants de bracket sont refusées. Le réviseur ne relève plus de P1/P2 confirmé, tout en maintenant la compilation/runtime Pine et le backtest FX non acquis.

Ces tests sont un oracle de cas contrôlés, **pas une exécution du Pine**. Ils ne prouvent ni la compilation ni l'identité de toutes les transitions du moteur natif. Les règles de tie des pivots restent celles de `ta.pivot*` ; les fixtures ne certifient pas les égalités.

## Vérifications non acquises

- **Compilation Pine v6 : non confirmée.** TradingView Desktop a été ouvert et le graphique observé ; les tentatives de remise au premier plan ont renvoyé «user input was detected in this window», suivies de «window is minimized». Aucun code n'a été collé, compilé, enregistré ni appliqué à un symbole dans TradingView par cette session. Ne pas transformer l'ouverture de l'application en preuve de compilation.
- **Backtest Forex marché : non exécuté.** Aucun historique FX validé ni export de transactions de ces paires n'est présent dans cette étude. Les données Alpaca des études précédentes sont des ETF et n'ont pas été réutilisées comme Forex.
- **100trades par paire, moitiés A/B, filtres ON/OFF : à exécuter** selon le protocole. Aucun win rate, PF, PnL, DD de marché ou conclusion de rentabilité n'est inventé.
- Comparaison historique/temps réel/rechargement de l'EMA1h, broker emulator/bar magnifier, exactitude du paramétrage des Propriétés, marge et coûts réels : restent à valider dans l'environnement cible.

## Écarts explicites au modèle idéal

La cancellation front-run intrabar n'est pas certifiée par un script de clôture15m. Le tableau stress pénalise des ambiguïtés après leur observation ; il ne change ni le capital natif ni les trades et ne constitue pas une autre simulation exécutable. Le SL n'est pas imposé avant le TP dans les fills natifs lorsque les deux sont dans la même bougie. La pénétration limite s'applique également au TP. Ces écarts empêchent de qualifier ce script de reproduction tick exacte de toutes les règles.

Le coût de1pip est un modèle constant par commission en devise de cotation, pas un historique de spreads. Aucun swap ni minimum de commission n'est modélisé. Le R du tableau est le risque prévu au signal ; le DD R est fondé sur les clôtures. Les résultats futurs doivent conserver ces qualifications.
