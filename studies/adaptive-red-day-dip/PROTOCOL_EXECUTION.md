# Protocole figé : repli estimé sur les séances rouges

Avant tout PnL de cette étude. Données locales SIP 1 minute SPY/QQQ vérifiées, 2016-01-04 au 2026-10-16, comptes indépendants 100000 USD. A 2016-01-04/2024-04-30, B 2024-05-01/2026-10-16 déjà réutilisée : aucune nouvelle validation aveugle.

## Signal et exécution

- Historique : 21 séances XNYS immédiatement précédentes, demi-séances incluses à leur longueur réelle, chacune intégralement valide. AverageDrop = moyenne arithmétique en dollars de max(Open-Close,0), avec zéro les jours non rouges ; ce n'est ni la moyenne sur les seuls jours rouges ni Open-Low. Pas de saut d'une journée manquante. ADR = moyenne High-Low des 14 séances immédiatement précédentes. Cours bruts, pas d'ajustement dividende ajouté à ces caractéristiques ; pas d'overnight.
- Chaque jour complet prévu de 390 minutes : niveau = floor_cent(Open - multiplier*AverageDrop), multiplier=1. AverageDrop et ADR sont quantifiés à 8 décimales avant calcul des niveaux. Si moyenne nulle : aucun trade. Stop = floor_cent(niveau-ADR). Niveaux non positifs : aucun trade.
- Première clôture de bougie de 5 minutes strictement inférieure au niveau, décisions de 09:35 à 15:30 New York incluses ; égalité insuffisante. Toutes les minutes depuis l'ouverture jusqu'à cette décision doivent être valides. La première candidate est consommée même si sa clôture est sous/égale au stop : motif invalid_geometry, aucun signal ultérieur choisi.
- Entrée LONG seulement, open de la minute décision+1 (09:35 -> 09:36), donc une minute de délai après constat. Même un rebond au-dessus du niveau n'annule pas cette entrée au marché. Ce n'est pas une simulation d'ordre limite.
- Quantité entière avant le fill, min(capital/clôture signal, 1% capital/(clôture signal-stop)). Objectif 1x avant fill ; aucune réduction de quantité après un gap. Le fill peut dépasser 1x ou 1% ; publier les maxima. Une transaction maximum par séance. Aucun TP.
- Stop dès l'entrée : gap au-dessous du stop -> prix open, y compris entrée déjà sous le stop avec deux côtés de frais ; sinon premier low<=stop -> stop. Pas de prix intrabar deviné. Sortie à open15:59 (minute389) si encore détenu ; les mèches de cette dernière minute ne sont pas détenues. Journée actuelle de 210 minutes : aucune entrée.
- Coûts identiques aux autres études : commission par côté max(0.35 USD,0.0035 USD/action), friction adverse 0.01 USD/action/côté ajoutée à l'entrée et retirée à la sortie. Long seul, emprunt nul, trésorerie non rémunérée. Pas de taxes/funding ni carnet de cotations. Stops gaps non plafonnés. La variante sans stop conserve la même quantité fondée sur le stop notionnel.

## Couverture et risque

Principal complete_days : filtrage de complétude de la journée actuelle seulement après sélection du signal. Il utilise une propriété future de disponibilité et produit une performance conditionnelle, pas un portefeuille continu certifié. resolved_prefix : la minute de délai non détenue peut manquer, mais le scan et toute trajectoire détenue doivent être résolus ; une minute inconnue avant sortie exclut entièrement le trade, conserve les frais d'entrée connus dans unresolved.csv et observed_return manquant. Zéro de comptabilité d'une exclusion ne signifie pas journée de cash observée.

Drawdown observé : frais d'entrée, clôtures des minutes intégralement détenues et equity nette à la sortie. Aucun extrême exact intraminute revendiqué. MAE/MFE prix incluent fills effectifs et extrêmes des seules minutes entièrement détenues ; exclure les mèches de la minute de sortie. Horizon intrabar du stop inconnu, durée de cette minute comptée comme borne supérieure.

## Matrice immuable avant résultats : 14 variantes x 2 ETF x 3 périodes = 84 comptes

reference ; cost_0.02/0.03/0.05 ; window_10/window_42 ; depth_0.5/depth_1.5 ; bars_1/bars_15 ; cutoff_1200 ; red2 (deux journées précédentes close<open, connu uniquement au passé) ; no_stop ; resolved_prefix. Une dimension modifiée à la fois. Aucun choix du meilleur après calcul.

Cinq critères historiques prédéfinis, tous exigés sur chaque ETF : >=100 trades ALL ; références A/B/ALL positives ; ALL sans les trois meilleurs jours positive ; A à friction doublée positive ; IC95 de la moyenne quotidienne ALL par bootstrap blocs20, borne basse>0. 3000 réplications, seed20261031, blocs5/20 et clusters annuels descriptifs. Les jours exclus restent zéro pour les statistiques comptables. Les IC ne corrigent ni les essais multiples de ce dépôt ni les recherches du fournisseur. Un succès indique un candidat historique, jamais une autorisation de bot ni de trading réel.

Le champ previous_red_count est plafonné à2 : seuls les deux jours précédents comptent pour red2. Une lacune plus ancienne que les fenêtres21/14 ne bloque pas ce filtre.
