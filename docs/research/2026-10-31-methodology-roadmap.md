# Feuille de route : audit externe et compléments utilisateur

Les assertions de l'avis externe sont à vérifier ; leur archivage n'est pas une validation. Aucun ancien verdict ou réglage n'est réécrit.

- 0 (en cours) : replay statistique à code figé, séparé du live opérationnel ; pré-enregistrement avant calcul, rapport et validation utilisateur.
- 1 : suspensions/calibration de coûts/emprunt intraday, seulement après feuvert.
- 2 : nouveaux instruments, règles GapReversalv3/ATR exactes, liste figée et corrélation ; après rapport0 et feuvert, ordre à confirmer si arrêt7 prioritaire.
- 3 : nouvelle étude sizing1%/4x QQQ, comparatif1x, faisabilité marge/PDT à vérifier aux règles alors en vigueur.
- 4 : nouvelles études journalières et nuit, protocoles et témoins figés.
- 5 : classement comparable des candidats, sans promotion rétrospective.
- 6 optionnelle : faisabilité StocksinPlay sans lancement de backtest avant rapport ; biais de survie.
- 7 : préenregistrer les bandesP&L20/60 par bootstrapblocs, arrêt sous5epercentile, drawdown>1,5x historique et seuil de parité pour enquête. L'utilisateur exige cela avant nouvelle séance ; priorité par rapport à0–5 demandée, nouveau suivi inactif jusque-là. Aucun changement des pauses ou positions existantes.
- 8 : ledgers statistique (toutes séances, SHA poussé avant date) et opérationnel (live qualifié), PROTOCOL.md expliquant OOSstratégie vs exploitation. Cible GitHubActions gratuit, rattrapages, GitHubSecrets et GETdonnées uniquement ; jamais de clés dans chat/dépôt.
- 9 : pushgratuitTelegram/ntfy, viequotidienne et alertes crash/retard/nonrésolu/STOP, après choix et validation ; aucun message envoyé maintenant.
- 10 : vue agrégée exposition/P&L/DD/corrélation et proposition limiteglobale pour éventuelréel, sans activationréelle.
- 11 : AGENTS.md/CLAUDE.md méthode àracine : préenregistrement, témoins, Holm, aucune retouche après résultat, distinction statistique/opérationnel, gratuité et secrets horschat.

Un rapport par tâche et feu vert avant la suivante. Les priorités7/8 qui recoupent0 ont fait l'objet de deux questions ciblées ; la préparation commune continue sans activation ni dépendance à une réponse supposée.
