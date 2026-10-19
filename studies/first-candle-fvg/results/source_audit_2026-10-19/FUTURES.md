# Audit des historiques futures gratuits

| instrument | raw_rows | rth_rows | complete_sessions | complete_span_days | overlap_minutes | overlap_ohlc_match_half_tick_fraction |
|---|---|---|---|---|---|---|
| ES | 464160 | 129705 | 329 | 477 | 5850 | 0.6162 |
| NQ | 772780 | 215655 | 547 | 795 | 5460 | 0.2910 |

Les deux fichiers publics contiennent effectivement plus d'un an de minutes et des volumes, sans remplissage ajouté ici. Les sessions complètes sont mesurées avec le même contrôle que le moteur. Le rapprochement récent porte sur les contrats datés décembre 2026 acquis séparément chez Yahoo ; il ne valide pas l'identité des contrats des années précédentes.

**Limite bloquante pour une validation finale :** les fichiers contiennent le symbole racine ES/NQ mais aucune échéance ni règle de rollover authentifiable pour chaque minute. Le dépôt amont cité `kfccolonel1/AlfordLabs` renvoie 404 lors du contrôle. Aucun nom de contrat n'a été ajouté à partir d'une supposition et aucun résultat de performance n'est présenté comme validation hors échantillon de contrats datés. Les variantes de tableaux de bord communautaires ne constituent pas une provenance de marché suffisante à elles seules.

Source : [dépôt BARS](https://github.com/kfccolonel1/BARS), catalogue et fichiers originaux archivés avec leurs URL et SHA-256 dans `data/free_sources/BARS`. Les données continuent d'être disponibles pour une exploration explicitement conditionnelle, mais ne remplacent pas une série de contrats traçable.
