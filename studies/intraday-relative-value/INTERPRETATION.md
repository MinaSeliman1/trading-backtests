# Interprétation — valeur relative intraday

Cette adaptation échoue sur la référence et sur toutes les sensibilités prédéfinies. ALL perd 14,24 % sur 539 paires, A 12,24 % sur 411 et B 2,26 % sur 128, mêmes frais inclus. La période B est réutilisée et non aveugle ; ces résultats ne démontrent ni impossibilité universelle du pairs trading ni performance future garantie, mais ne justifient pas un nouveau bot avec ces règles.

La perte ne s'explique pas uniquement par les coûts. Sur les quantités réellement prises dans la référence, le mouvement des deux jambes produit déjà −8786,18 USD avant attribution des frais ; frictions, commissions et emprunt ajoutent 5451,87 USD. Retirer simplement ces frais ne serait pas un nouveau portefeuille recalculé : la capitalisation et les quantités changeraient. La variante friction_zero conserve commissions et emprunt et reste perdante, à −11,00 % ALL.

La contribution QQQ est −26626,18 USD et SPY +12388,14 USD, somme −14238,04 USD. Ces contributions dépendent des positions opposées et de leur même capital de sizing ; elles ne permettent pas de promouvoir une stratégie SPY autonome. La neutralité en dollars n'est pas une neutralité aux facteurs de marché, au bêta ou à la technologie.

Les variantes de seuil, fenêtre, direction, délai, coût et couverture sont conservées. La variante ALL la moins perdante à seuil2,5 est encore négative (−4,21 %) ; aucun seuil n'est choisi après observation. cost_gate n'écarte ici aucune des paires de référence, ce qui ne prouve pas le réalisme de son proxy. Le prefix résout une paire supplémentaire et donne −14,00 %, sans éliminer les exigences de données passées ou certifier une couverture continue.

L'IC95 descriptif de moyenne quotidienne en blocs20 est entièrement négatif, environ −0,76 à −0,37 bp/jour. Ce n'est ni un test universel de rentabilité ni une correction de nos nombreux essais historiques ; il décrit la même trajectoire conditionnelle. Seul le minimum de 100 paires passe parmi cinq critères figés.

Les limites d'exécution des deux jambes sont importantes : opens synchronisés hypothétiques, pas de risque de legging, quotes, profondeur, fills partiels ou taux/locates réels. Les stops sont surveillés aux closes, pas garantis intrabar. Le drawdown de 14,34 % observe les marks définis ; il ne certifie pas le pire tick ou la marge broker. Les sources externes ont des méthodes différentes et ne prouvent pas une cointégration de QQQ/SPY.

Décision : archiver cette piste, sans installer de moteur supplémentaire. Les bots Noise Area et ORB restent inchangés en simulation ; une variante ultérieure serait une nouvelle hypothèse, avec nouvelle exécution et sans réécriture de ce résultat.
