# Plan — retour VWAP après première heure

Demande autorisée : choisir une autre piste QQQ/SPY, mêmes frais, tests/rapport et publication dans trading-backtests ; donner une décision pratique pour ORB. Exécution directe dans ce chat, sans clé ni changement de bot. Réutiliser les archives locales après SHA, extraire les champs VWAP conservés dans les gzip.

## Interfaces et fichiers

- vwap_reversion/data.py : load_sources() -> marchés vérifiés plus tableaux `vwap` et profil/empreintes ; données supplémentaires sous data/ ignoré, jamais Git.
- engine.prepare(market) -> table décisionnelle (historique20/premièreheure/seuil), incluant sommes Decimal canoniques.
- engine.trace(market,index,feature,exit_policy) -> géométrie causale, prix/marks/résolution, ou UnresolvedExecution ; aucun P&L.
- engine.simulate(market,features,config,start,end) -> daily,trades,unresolved,capital/DD conditionnels.
- analysis.summarize/uncertainty : helpers statistiques existants immuables quand applicables ; adapter champs nouveaux et exposition variable.
- scripts run/audit/validate/report/verify : 48 sorties, audit Decimal sans appels moteur, rapprochements, figures et preuve d'intégrité.

## Tâches

1. [x] Moteur/data/stats rouges puis verts ; 46tests, revue indépendante et corrections avant P&L (ablation par rendement, VWAP inutilisé du témoin EOD).
2. [x] 428pages SHA, 2108361barres RTH rapprochées ; versions/dépendances/protocole/code gelés avant 48calculs.
3. [x] 48calculs ; audit indépendant12586lignes/2125058marks et1776agrégats ; six IC reproduits depuis CSV en revue. Aucun correctif financier post-P&L.
4. [x] Rapport,16préfixes bruts/3168barres/19008champs,4figures inspectées, revue finale ; recommandation ORB sans activation.
5. [x] Tests finaux et archives/anciennes études inchangées ; bot lu sans mutation. Livraison GitHub autorisée sur main/branche, hash distant à vérifier avant réponse finale.

Résultats : principaux VWAP négatifs A/B/ALL, à archiver ; ORB QQQ conserve son statut de candidate pour observations prospectives distinctes, pas de nouveau bot. Le texte courant README présente les résultats, le gel original est conservé.

## Vérifications de revue

- Les 20 séances ADR sont immédiatement précédentes, sans journée actuelle/future.
- Aucun close/VWAP d'une minute non terminée pour sortir au même open ; une touche VWAP seule ne vaut pas clôture de retour.
- Stop à l'open ou sortie déjà planifiée/EOD résolue même si fin de barre manquante ; stop intrabar ignore prix postexit.
- VWAP source peut sortir de OHLC à cause des filtres ; ne pas filtrer arbitrairement, valider positif quand volume positif, zéro volume sans poids.
- Exclusions source ne deviennent pas cash observé ; abstentions causales ADR sont distinguées.
