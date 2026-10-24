# Plan — ORB QQQ shadow et nouvelle étude NR7

Demande explicite : lancer aussi ORB QQQ en simulation en arrière-plan, chercher une autre piste QQQ/SPY à mêmes frais et publier les résultats dans trading-backtests. Exécution directe dans ce chat, pas de nouvelle saisie de clés ; données locales pour recherche. Noise Area et études précédentes inchangées.

## Bot ORB

Créer bots/qqq-orb avec ledger/runtime isolé, capital virtuel100000, moteur ORB d'origine SHA0ee6f0f9e7b7f1080d444e90a055aeb4ed2dc63349cfc7ab05f66d1d4f5f1810 réutilisé pour sorties, règles1%/cap1x/10R/stopfirst/slip0.01 et commissions/emprunt inchangés. Pas de filtre futur complete_days ; disponibilité causale du préfixe. SIP différé16min ; réutiliser coffre Windows en mémoire, transport limité GET données, jamais brokerorders. Arrêt/refus des nouvelles entrées après données incohérentes ou insolvabilité.

Core.advance(account,day,bars,session,asof) pur et testable ; Ledger.tick transactionnel, SQLite séparée ; service pythonw+processlock/logsmasqués ; tâcheWindows dédiée au logon et maintenant ; monitorlectureseule. Pas de rattrapage d'entrée après09:37logique, attendre prochaine séance si lancement tardif. Fills simulés aux prix des barres fermées disponibles : entrée09:35 observée au plus tôt09:36logique, pas preuve de fills réels. Position persistante reprise vers sortie avec retard signalé ; trou actif>120s nonrésolu, frais/position conservés, pas de cash fictif ni nouvel événement duplicaté. Règles détaillées dans bots/qqq-orb/PROTOCOL.md.

## Recherche NR7

Créer studies/nr7-breakout : sept séances immédiatement précédentes complètes, NR7 strict si rangeveille<chacunesixautres ; limitesveille corrigées du dividendeex-date ; première clôture minute au-delà d'une limite jusqu'àn−3, entréeopenminute suivante, stoplimiteopposée/EOD, risque1%/cap1x. Pas d'objectif ou filtre réglé après P&L. Principaux4frictions, LONG,SHORT,sansfiltreNR7,toujoursconditionnalitépréfixe =>48scénarios. Protocole/source/versions/codegelés avant P&L.

## Étapes

1. [x] 29tests bot passent : entrée causale, fills/coûts du moteur gelé, doji, gaps, stop/cible simultanés, demi-séance, latences, restart/idempotence, données manquantes, GETguard et monitor ; parité2707séances/2688trades.
2. [x] Revue indépendante ; reprise après minuit et qualification d'une position héritée corrigées avant lancement. Tâche cachée installée le24octobre, GET SIP4717barres vérifié, compte distinct100000USD, aucun ordre. Première séance éligible26octobre2026.
3. [x] NR7 : 16tests,48scénarios figés ; audit Decimal19510lignes de trades recouvrantes/6392716marks,2324contrôles secondaires ; 16séances/30300champs rapprochés des sources,108extraits ;4figures et revue. Aucune modification des règles après P&L. B principale négative sur les deux ETF, aucun bot NR7.
4. [x] Rapport/registre et preuves d'activation livrés ; anciennes études et code Noise Area inchangés. Publication limitée au bot ORB, à l'étude NR7, au registre et à ce plan ; clés et runtime exclus. Le hash distant est contrôlé lors du push de livraison.

Livraison du24octobre2026 : `bots/qqq-orb/README.md`, `studies/nr7-breakout/VALIDATION.md` et le rapport daté contiennent les commandes et les limites. Les audits/rapports ont été enrichis après calcul sans changement du moteur ou des fichiers financiers ; snapshots initiaux et finaux conservés. Le monitor ORB est local, le suivi Codex automatique Noise Area reste distinct.
