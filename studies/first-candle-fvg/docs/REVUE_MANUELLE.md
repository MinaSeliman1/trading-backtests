# Revue manuelle et conventions limites

Les observations suivantes ont été lues directement dans les CSV réels acquis, puis rapprochées du journal. Elles complètent les assertions de `scripts/audit_historical_trades.py` ; elles ne mesurent pas l'ordre des transactions à l'intérieur d'une minute.

## SPY, 9 octobre 2026, SHORT

Le FVG formé sur 09:43/44/45 est connu à 09:46 : high de la troisième bougie 775,820007 inférieur au low de la première 775,960022. Le corps de la deuxième bougie baisse de 776,099976 à 775,594971 en traversant L. Le retour commence sur la minute 09:46 ; la bougie 09:48, de 775,719971 à 775,434998, englobe le corps haussier précédent (775,559998 à 775,710022). Signal connu à 09:49, puis open observé 775,429993. Le modèle exécute le SHORT à 775,41 après coûts de prix. Aucun prix de la minute 09:49 n'est requis pour fixer la quantité au close 09:48. Les stops des variantes A et B sont distincts et les deux sorties sont perdantes.

## QQQ, 30 septembre 2026, LONG

Le FVG connu à 10:43 se situe approximativement entre 742,719971 et 742,729980 ; il est très petit et n'a pas été filtré après observation du résultat. La bougie 10:44 est baissière (742,885010 à 742,510010), puis celle de 10:45 est haussière (742,494995 à 742,919983) et englobe entièrement son corps. Signal connu à 10:46. La variante A protège l'extrême du retest jusqu'à confirmation (low 742,419983, arrondi et buffer conduisant à 742,40). La variante B utilise le bord du FVG et un stop plus serré, 742,70. Les deux variantes partagent une entrée, mais leurs sorties diffèrent : A atteint son objectif, B subit son stop. Cette divergence provient du placement demandé des stops, pas d'un choix rétrospectif.

## ES décembre 2026, 15 octobre, LONG

Le FVG sur 10:00/01/02 est connu à 10:03 : high de la première 7732,00 ; low de la troisième 7740,75. La deuxième bougie monte de 7730,75 à 7743,25 en traversant H. La minute 10:03 reteste la limite supérieure à 7740,75 et est baissière. La minute 10:04 ouvre à 7740,75 et clôture à 7742,50, englobant son corps. L'ordre est confirmé à 10:05 ; open suivant 7741,75, fill LONG 7742,00 avec un tick de slippage. Stop A 7740,50, donc objectif 7746,50. Sur la minute d'entrée, low 7741,00 reste au-dessus du stop et high 7747,00 dépasse le TP : cette sortie gagnante ne dépend pas d'un choix favorable de l'ordre stop/TP. Le prix de sortie simulé est 7746,25 après slippage.

## Limite d'acceptation d'ordre et donnée manquante

La revue a ajouté un test qui modifie uniquement l'open suivant et exige une quantité inchangée. Le risque est désormais estimé au close de confirmation et mesuré à nouveau après le fill. Un gap peut faire dépasser la cible ; aucun redimensionnement rétrospectif n'est permis. Le rejet d'un stop invalide ou d'un ordre non finançable au premier prix est une convention de simulation exigée par le cahier des charges. Un ordre au marché réel déjà envoyé pourrait devoir être exécuté puis fermé : cet écart est explicitement documenté.

QQQ contient le 7 octobre une minute à 16:42 UTC / 12:42 NY dont open/high/low/close/volume sont tous NaN. La séance entière a été exclue, plutôt que de la conserver parce que le trou survient après l'heure limite d'entrée. Cette politique de qualité peut elle-même introduire un biais de sélection et figure dans le protocole.
