# Revue séparée — Turn of Month intraday

## Avant premier PnL

Reviewer distinct, lecture seule : protocole, moteur, tests, agrégateur mensuel, runner, audit, rapport et vérificateur. Aucun accès aux performances de marché, bots, runtime, clés ou coffre.

28tests initiaux relancés avec succès. Audit synthétique en mémoire :24scénarios,58lignes résolues et4276contrôles, aucune divergence.500parcours aléatoires comparés avec une boucle scalaire indépendante : aucune divergence. Aucun fichier de marché ou PnL lu pour ces essais.

Blocage détecté : sessions_in_range sur un calendrier construit aux limites de mois peut rejeter le premier/dernier jour civil non ouvré. La plage source réelle commence avec un mois précédent dont le1novembre2015 est dimanche. Deux régressions échouent avant correction (borne initiale dimanche et borne finale dimanche), puis passent après usage des sessions du calendrier construit. Aucun PnL de marché n'avait encore été calculé.

Suite finale :30tests, tous verts ; relance indépendante30/30 en3,68s. Le vérificateur exige au moins30tests. Calendrier indépendant de l'audit construit mois par mois sur un calendrier plus large. Revue du rapport : contraste mensuel issu du contrôle all_days et critère de candidature conformes au protocole ; risque virtuel no_stop et comptes conditionnels explicités. Aucun autre problème bloquant avant gel.

## Après exécution

Revue finale en lecture seule :17862contrôles, aucune divergence. Empreintes courantes/figées/snapshots :9fichiers d'étude,12dépendances et2protocoles ;6préparations,6acquisitions brutes, validation et corporate actions rapprochées au profil source gelé. Les72résumés JSON concordent avec la matrice, ainsi que les6références, coûts et contrôles du rapport.

Calendrier XNYS reconstruit séparément par mois pour les trades all_days ;6contrastes mensuels et IC95 à3000tirages reproduits.130/100/30mois par ETF, soit520lignes mensuelles recouvrantes. IC95 ALL identiques : SPY[−0,2651085884 ;13,4902230997], QQQ[−2,2809001716 ;15,3939632835]bps. Les deux comprennent zéro ; la décision d'échec du critère prédéfini est correcte.

Quatre figures inspectées. Limites de couverture conditionnelle, B réutilisée, comptes composés séparément et absence de conclusion causale présentes. Aucun nouveau calcul de stratégie de marché par le reviewer, aucune modification de fichier, runtime, clé ou bot.
