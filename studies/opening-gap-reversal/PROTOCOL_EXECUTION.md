# Précisions d'exécution — fixées avant le premier calcul du P&L

20 octobre 2026. Exécution du protocole déjà publié dans README.md, autorisée par la demande « fait la nouvelle piste ».

La question est de savoir si le retour après un gap absolu strictement supérieur à 2 % présente un avantage net sur SPY ou QQQ. Aucun changement de seuil ou d'horaire après les résultats. Périodes indépendamment initialisées à 100 000 USD : ALL du 04/01/2016 au 16/10/2026 ; A jusqu'au 30/04/2024 ; B du 01/05/2024. B est une comparaison chronologique exploratoire, pas un nouvel échantillon aveugle. Les observations antérieures et le comptage sont déjà connus.

## Données et suspensions

Réutiliser les acquisitions SIP raw validées et leurs empreintes. Le cache conserve les NaN des minutes absentes et le calendrier XNYS complet. La clôture précédente est celle de la dernière minute régulière de la séance précédente, y compris une demi-séance ; ne pas sauter à une autre date.

Profil principal `endpoints` : exiger open 09:30, open 09:31, open 10:00 et clôture précédente valides. Les données OHLCV observées des 31 premières minutes doivent être cohérentes ; les doublons contradictoires, données invalides ou heures hors grille signalés dans le cache excluent la séance ambiguë. Les trous de cotation intermédiaires sont conservés et comptés, puisque la stratégie sans stop ne demande aucun ordre pendant ces minutes. Les prix d'entrée et sortie doivent être observés. Une suspension intra-trade n'est pas interpolée ; MAE/MFE et drawdown intraday sont mesurés seulement sur les prix effectivement observés.

Ainsi, une suspension après 10:00 n'annule pas un trade passé, et une suspension intermédiaire n'exclut pas automatiquement un événement de crise exécutable aux deux bornes. Chaque séance incomplète est auditée, sans assimiler automatiquement un trou à une suspension officielle. Une absence de prix à une borne empêche la simulation : elle est publiée comme exclusion, pas comme absence de signal.

Profil de sensibilité `complete_days` : séance actuelle et précédente intégralement valides, pour rapprocher les anciens comptes 42 SPY / 77 QQQ. Ce filtre utilise une qualité de séance connue après coup et ne constitue pas une règle de déploiement.

## Quantité, coûts et risque

La quantité est fixée à 09:31 à partir de l'open 09:30 déjà connu : `floor(capital / open_09:30)`. Exposition cible 1x ; l'exposition effective à 09:31 peut varier avec le mouvement entre les deux minutes et les frais. Aucun prix futur d'exécution n'est utilisé pour déterminer la quantité. Direction reversal = opposée au gap ; contrôle momentum = même sens, mêmes dates et même règle de taille.

Entrée à l'open 09:31 plus friction adverse selon le sens ; sortie à l'open 10:00 moins friction adverse selon le sens. Commission par ordre max(0,35 USD, quantité × 0,0035 USD). Emprunt SHORT = quantité × prix d'entrée simulé × 0,01 / 360. Aucun dividende reçu pour une position ouverte après le détachement ; le dividende ex-date sert uniquement à corriger la référence du gap.

Friction fixée à 0,01 / 0,02 / 0,03 / 0,05 USD/action/côté, hypothétique et non mesurée. Les ouverts de crise peuvent être moins exécutables que cette hypothèse. Pas de stop, objectif ou liquidation de marge ajoutés. Après insolvabilité simulée, aucune nouvelle entrée ; publier cet état s'il survient.

## Sorties et contrôles

54 scénarios : 2 instruments × 3 périodes × 4 frictions × 2 sens = 48 ; plus 6 sensibilités complete_days/reversal à 0,01. Cash sans rémunération = 0 %. Pas de sélection du meilleur scénario.

Exports des trades, journées, mesures nettes, coûts, exposition, MAE/MFE observés, années et directions. Drawdown principal quotidien et drawdown secondaire des clôtures minute observées ; ni les deux ni leurs extrêmes ne sont présentés comme un drawdown tick réel.

Incertitude : bootstrap de blocs annuels sur les rendements nets en bps par trade, 5 000 répétitions, seed 20261020. Un bloc contient tous les événements d'une année, y compris années sans événement. La période B ne possède que trois blocs annuels partiels/complets : intervalle descriptif très fragile, pas un test de preuve d'avantage. Publier aussi l'effet de retirer les meilleures journées et les trades de 2020.

Comparer les P&L quotidiens B avec Noise Area next_open, plafond 1x, friction 0,01, aux dates communes. Corrélation descriptive, sans optimiser un portefeuille. Auditer indépendamment chaque trade à partir des tableaux sources et rapprocher trades, coûts, solde et métriques. Revue indépendante avant ajout des résultats sur GitHub. Le bot actif n'est pas modifié.
