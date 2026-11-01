# Protocole SMT — figé avant le premier calcul des résultats

## Portée et sources

L’utilisateur autorise les archives ES/NQ existantes comme **proxy**, avec la valeur d’un lot MNQ : 2 USD par point, tick de 0,25 point = 0,50 USD. ES est seulement le comparateur, sans position ES/MES. Les bougies et les divergences ES/NQ ne sont pas garanties identiques aux véritables MES/MNQ. Aucune validation micro, aucun nouvel ordre ou bot, aucun accès aux clés, au coffre ou aux journaux actifs.

Sources : fichiers gzip AlfordLabs/BARS. ES débute le 20 juin 2025 ; NQ débute en août 2024. Chevauchement évalué : 20 juin 2025–8 octobre 2026. Vérifier SHA-256 contre les reçus d’acquisition, OHLC positifs et cohérents, grille de 0,25, doublons et horodatages à la minute. Aucun remplissage. Le volume n’entre dans aucun signal.

Les entêtes indiquent des heures locales America/New_York sans offset. Localiser avec la base IANA (ambiguïtés/horaires inexistants bloquants), puis stocker en UTC. Toutes les fenêtres ci-dessous sont définies en America/New_York : jamais un décalage UTC fixe.

La documentation des archives décrit un **continu de première échéance non ajusté**, sans identifiant de contrat par ligne. Les courts fichiers Yahoo ESZ26/NQZ26 datés ne sont pas ces archives. Les jours exacts de changement d’échéance du continu sont inconnus : ne pas en inventer.

Protection calendaire commune ES/NQ, par précaution : exclure du premier jour de chaque mois trimestriel (mars, juin, septembre, décembre) à la première séance NYSE après son troisième vendredi, bornes incluses. Exclure aussi une date dont la séance précédente est dans cette zone. Pour A, exclure si l’un des 20 jours de moyenne est dans cette zone. Publier dates et nombres de ces **exclusions préventives**, sans les présenter comme des changements identifiés. La protection reste conditionnelle aux raccords trimestriels décrits ; elle ne certifie pas les contrats ni leur sélection au volume.

## Calendrier, niveaux et échantillon

Ancrage cash XNYS : uniquement les séances NYSE ouvertes ; RTH 09:30–16:00, ou 13:00 les demi-séances. Ce choix définit la bougie quotidienne et la moyenne ; ce ne sont pas des settlements Globex. La veille est la séance NYSE précédente : ne pas sauter une séance aux prix manquants.

Niveaux ES et NQ : Londres [04:00,07:00), prémarché [07:00,09:30), veille [09:30, clôture cash). Tous doivent être connus. Échantillon principal commun aux politiques d’une variante : prix ES complets [04:00,11:00), NQ complets [04:00,11:30), plus ouverture NQ 11:30 finie, positive et sur la grille. La complétude est constatée après coup : résultat conditionnel à la disponibilité, jamais utilisée par le calcul causal du signal. Une issue non observée ne devient pas un résultat nul.

## Six variantes principales

H1/H2 × A/B/C, sans autre filtre technique :

- A : clôture RTH NQ de la veille comparée à la moyenne des 20 clôtures RTH finissant la veille ; au-dessus long, au-dessous short, égalité neutre. Les 20 clôtures doivent être observées et hors fenêtre de raccord.
- B : bougie RTH NQ de la veille haussière long, baissière short, doji neutre.
- C : aucun biais ; les deux directions SMT sont admissibles.

Niveaux regroupés. Retenir le premier **signal admissible dans le sens du biais** par ordre temporel. Un balayage opposé au biais A/B n’est pas un signal du modèle. Priorité uniquement si plusieurs niveaux signalent dans la même minute : **Londres → prémarché → veille**. Si C produit deux directions dans une même minute sur le niveau prioritaire, l’ordre intraminute est inconnu : journée ambiguë, aucun ordre.

Un seul premier setup par jour et variante : après rejet de géométrie, annulation ou absence de confirmation, ne pas chercher un autre setup plus favorable.

## Détection et ordre causal

Balayage haut : high ≥ niveau + 0,25 ; balayage bas : low ≤ niveau − 0,25. Une simple touche exacte n’est pas un balayage. ES doit balayer ce niveau pour la première fois depuis 09:30 ; NQ ne doit pas avoir balayé son niveau correspondant depuis 09:30, bougie du signal comprise. Un niveau déjà balayé ne redéclenche pas au retest.

Entrées [09:32,11:00] incluses, après lecture de la bougie entièrement clôturée précédente. Les balayages admissibles sont donc sur les bougies 09:31–10:59. L’état à 09:30 est observé, mais un balayage 09:30 n’arme pas un setup H2 à reporter ensuite. Cette convention est identique sur toutes les variantes et décidée avant résultats.

H1 : balayage haut ES → long NQ, bas → short, sous réserve du biais. Stop : extrême des dix dernières bougies NQ entièrement clôturées, moins un tick long / plus un tick short.

H2 : balayage bas ES → long NQ, haut → short. Attendre la première clôture ES revenue strictement du côté intérieur du niveau. La bougie de balayage peut elle-même confirmer. Annuler si NQ balaye son niveau avant ou sur la confirmation. Stop : extrême NQ depuis 09:30 jusqu’à confirmation, plus un tick au-delà. Pas de confirmation dans la fenêtre : aucun ordre.

Prix estimé avant envoi = dernière clôture NQ + glissement adverse prévu. H1 : objectif = **premier niveau NQ** dans la priorité Londres/prémarché/veille strictement au-delà du prix estimé dans le sens du trade ; règle commune à SMT et aux témoins. Si aucun objectif, `no_target`. Ensuite exiger gain potentiel ≥ distance au stop ; ne pas essayer un autre niveau après rejet. H2 : objectif à 2R après remplissage.

## Remplissages, gaps et coûts

Entrée au prochain open avec glissement adverse. Le prochain open n’annule jamais gratuitement l’ordre : un gap dégradant le ratio reste compté. Le journal donne `ecart_ouverture` = open d’entrée − close du signal, en points signés, plus sa version en ticks.

Risque réel 1R = valeur absolue du prix d’entrée **rempli** moins le stop, × 2 USD. Un gap change donc le risque. Risque nul : net USD compté, R indéfini, cas comptés et signalés ; aucune validation reposant sur leur omission. H1 garde son objectif fixé avant l’ordre. H2 place son objectif à deux fois la distance positive au stop depuis le prix rempli ; si le stop est déjà dépassé, sortie immédiate.

Si l’open d’entrée ou d’une bougie détenue dépasse déjà stop ou objectif, sortie à cet open ; commissions et glissements des deux côtés restent comptés, y compris lors d’une entrée et sortie immédiates. L’open connu précède les mèches suivantes. Sinon, si stop et objectif sont touchés dans la même bougie, compter le stop. Sorties intrabar au niveau, puis glissement adverse. Sortie forcée à l’open 11:30, aucune mèche 11:30 utilisée. Aucun break-even, trailing ou sortie discrétionnaire.

Coût principal : **1,25 USD par côté + deux ticks au total aller-retour**, soit un tick par côté ; coût 3,50 USD par transaction d’un lot. Stress fixé : deux ticks par côté, soit quatre ticks au total, coût 4,50 USD. Le script TradingView cité emploie `slippage=2`, qui s’applique par remplissage : cette différence est explicitement couverte par le stress. Les plans sont recalculés causalement avec le coût concerné, sans nouveau réglage de stratégie. Glissement également appliqué aux sorties objectif, convention uniforme conservatrice et non promesse d’exécution limite. Les prix remplis ne sont pas plafonnés aux OHLC.

Un lot fixe ; pas de capital fictif choisi pour embellir un pourcentage. Publier USD, R, nombre de trades et exposition. Drawdown principal sur résultats clôturés ; les marques aux clôtures minute ne prouvent pas le drawdown intraminute.

## Témoins et hasard

Biais seul : entrée à 09:32, avec plan sur dernière clôture 09:31. Hasard : 1 000 portefeuilles ; une minute uniforme parmi les 89 minutes 09:32–11:00 par jour. Stops, objectifs, géométrie et frais identiques à ceux du modèle concerné. Aucun nouveau tirage après géométrie invalide ; journée sans ordre, exclusion comptée.

Graine racine **20261031**, PCG64. SeedSequence `[graine,0,AAAAMMJJ]` pour la pièce quotidienne C ; `[graine,1,AAAAMMJJ]` pour les 1 000 minutes de cette date. Une seule table de sens et de minutes réutilisée par tous les modèles/témoins/coûts, stable si l’on ajoute d’autres dates. Bootstrap : `[graine,2,identifiant_contraste,longueur_bloc]` ; permutation diagnostique : `[graine,3,identifiant_variante,période]`. Aucune recherche de meilleure graine.

A/B : direction connue par le biais avant l’entrée. C : pièce long/short 50/50 commune au biais seul et aux 1 000 hasards ; SMT-C garde le sens de son signal. L’autre convention demandée (sens futur SMT) est calculée seulement comme diagnostic **« contrefactuel, non tradable »**, sur les journées de trades SMT, exclue de tous les critères.

Comparaison principale : USD nets par journée sur **les mêmes dates éligibles**, y compris zéro observé sans ordre. Ajouter R par trade, fréquence, risque engagé et durée. Des témoins plus fréquents paient plus de coûts : publier leurs refus et l’exposition ; ne pas attribuer automatiquement les coûts évités à une capacité prédictive SMT.

Diagnostic supplémentaire : permuter entre dates des cartes (minute, direction, absence d’entrée), dans la même strate de biais A/B ; C sans strate de sens. Cela conserve marginalement les heures et directions, sans retirer une carte invalide. Placebo statistique non tradable, jamais critère de sélection.

## H3, annonces et séparation chronologique

H3 sans trade : au moins ES ou NQ balaye un haut ou bas Londres entre 07:00 et 09:30. Mesurer range NQ [09:30,11:00), points et points de base de l’open 09:30. Décrire aucun / ES seul / NQ seul / deux. Cohorte propre à H3 : prix courants nécessaires et exclusion du raccord courant, sans exiger un niveau de veille ou une moyenne quotidienne. Association, pas causalité ni preuve d’avantage de trading.

Calendrier figé CPI/NFP officiel BLS et FOMC Fed ; résultats avec et hors ces jours. FOMC 14:00 arrive **après** notre sortie 11:30. Les autres publications ne sont pas suivies : dire « hors calendrier retenu », jamais « sans news ». Conserver les sources et le mode d’acquisition (BLS direct 403, extraction du calendrier officiel via navigateur web).

Découverte A : 20 juin 2025–27 février 2026. Phase 2 B : 2 mars–8 octobre 2026. ALL : union. Les archives ont servi à d’autres recherches du dépôt ; B est une séparation chronologique pour ce protocole, pas un échantillon nouveau aveugle garanti. Tests par niveau séparé seulement sur A, après les principaux ; jamais sélection ni test B additionnel.

## Critères décidés avant résultats

Une des six variantes est seulement un candidat proxy à confirmer si **toutes** ces conditions sont remplies :

1. Au moins 100 trades ALL et 25 en B (suffisance exploratoire, pas preuve).
2. Net USD positif en A et B.
3. Avantage moyen USD/jour positif contre biais seul et moyenne du hasard en A.
4. En B, borne basse IC95 par blocs de 20 > 0 contre chacun des deux témoins.
5. En B, p joint = maximum des p bootstrap centrés des deux contrastes et du rang empirique parmi les 1 000 hasards ; ajustement Holm sur les six variantes ≤ 0,05.
6. Net B positif avec le stress de quatre ticks aller-retour.
7. R défini sur tous les trades ; risque nul déclaré, sans omission favorable.

Bootstrap circulaire de 3 000 répétitions, blocs de 5 et 20 **observations éligibles ordonnées** (les exclusions peuvent séparer les dates), intervalles percentiles descriptifs. Publier les différences d’exposition et les limites statistiques. H3, niveaux séparés, placebo et contrefactuel C ne participent jamais au passage. Même un passage signifie une piste proxy à vérifier sur véritables contrats MNQ/MES datés, pas une stratégie validée ni une autorisation de trading réel.
