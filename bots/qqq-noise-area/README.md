# QQQ Noise Area — Alpaca paper

Bot local de simulation, avec les règles et le dimensionnement du [backtest Noise Area](../../studies/intraday-momentum-noise-area/README.md). Le trading passe exclusivement par `https://paper-api.alpaca.markets`. Il n'existe aucune option de compte réel.

Avec le compte gratuit vérifié le 20 octobre, le lancement retenu est **shadow / SIP**, différé de 16 minutes : les transactions sont simulées localement avec les données Alpaca, sans ordre envoyé au compte paper. L'essai connecté IEX a révélé des séances incomplètes incompatibles avec le filtre strict du backtest ; il a été suspendu et arrêté sans fill. Les règles n'ont pas été assouplies pour forcer des trades.

L'adaptateur **ordres Alpaca paper** reste disponible avec SIP temps réel si le compte possède ces droits et un historique valide. IEX est une expérience distincte, explicitement sélectionnée, dont les signaux peuvent différer de SIP et qui ne passe pas actuellement le contrôle d'historique observé. Aucun basculement silencieux de flux.

## Règles figées

| Paramètre | Valeur |
|---|---|
| Instrument et capital virtuel initial | QQQ ; 100 000 USD |
| Noise Area | 14 observations passées valides à la même minute |
| Volatilité quotidienne | 14 rendements de clôture passés ; écart-type ddof=1 |
| Exposition cible | min(4, 0,02 / volatilité) ; quantité entière, fixée pour la séance |
| Décisions | 10:00 puis toutes les 30 minutes jusqu'à 15:30, heure de New York |
| Signal et sorties | Décideur `combined` de l'étude : bandes et VWAP ; fermeture avant retournement |
| Fin de séance | Tentative de liquidation à 15:59 ; 12:59 pour une clôture à 13:00 |
| VWAP | HLC3 pondéré par les volumes des minutes terminées |
| Dividendes | Dividende ex-date soustrait de la clôture précédente pour les bandes |

Les fenêtres utilisent uniquement les séances passées et le préfixe terminé de la séance courante. Le décideur historique est importé avec contrôle SHA-256. Ce bot nécessite donc le dépôt complet.

## Coûts et résultats

Un compte net local applique les coûts suivants aux fills paper. En shadow, il utilise l'open de la minute de référence, reçu avec retard, sans exécution chez Alpaca :

- commission de **0,0035 USD/action/côté**, minimum **0,35 USD par ordre** ; minimum appliqué une seule fois malgré plusieurs fills ;
- buffer adverse **supplémentaire de 0,01 USD/action/côté** ;
- emprunt SHORT supposé à **1 % annuel / 360**, minimum un jour par transaction ; jours calendaires écoulés si maintien accidentel.

Ce sont des hypothèses prudentes comparables à celles de l'étude, pas une cotation des frais facturés par Alpaca. Le spread peut déjà être présent dans le fill paper : le cent supplémentaire sert de stress conservateur. Les frais réglementaires variables ne sont pas tarifés séparément. Le coût d'emprunt est hypothétique, sans garantie de disponibilité d'un prêt.

Le solde affiché chez Alpaca reste brut de cette surcouche. `net_realized_equity` est le capital local réalisé après frais ; il ne valorise pas la position ouverte. Le dimensionnement utilise ce capital local, pas l'equity brute Alpaca. Les ordres peuvent être refusés si les droits, la marge ou la disponibilité SHORT du compte ne suffisent pas ; le bot suspend alors les entrées.

Un ordre market paper arrive après la publication de la dernière minute, dans une fenêtre maximale de 20 secondes. Il ne garantit pas l'open exact du backtest. Le replay historique à +0,01 USD par côté vérifie les calculs, pas les prix d'exécution futurs.

## Installation et lancement

Depuis ce dossier, sous PowerShell, avec Python 3.14 :

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\launch-paper.ps1 -Mode shadow -Feed sip
```

Saisir les **clés du compte PAPER** dans la console, jamais dans le chat ou un fichier. Le lanceur masque la saisie, transmet les clés uniquement dans l'environnement de son processus enfant, puis efface ces variables à sa sortie. Aucun secret n'est enregistré dans SQLite, les exports ou Git. La machine, le réseau et la console doivent rester disponibles.

Pour contrôler la connexion sans ordre :

```powershell
.\launch-paper.ps1 -Mode shadow -Feed sip -Check
```

Le contrôle lit le compte paper et un échantillon SIP ancien ; il ne prouve pas l'accès à SIP temps réel ni la validité des signaux IEX. Il n'annule et ne ferme aucun ordre, y compris lors d'un Ctrl+C.

Avec des droits SIP temps réel, pour envoyer les ordres au compte paper :

```powershell
.\launch-paper.ps1 -Mode paper -Feed sip
```

La CLI Python a pour défaut `shadow / sip` :

```powershell
.\.venv\Scripts\python.exe -m qqq_paper --mode paper --feed sip --prompt
.\.venv\Scripts\python.exe -m qqq_paper --mode shadow --feed sip --prompt --once
.\.venv\Scripts\python.exe -m qqq_paper --help
```

`--once` effectue un cycle puis quitte ; en mode paper, une position peut donc rester ouverte. Utiliser le lancement continu pour la simulation de séance. Le mode paper/SIP demande des droits SIP temps réel ; les données refusées ou trop anciennes ne sont pas remplacées par IEX.

## État, interruption et reprise

Le dossier ignoré `runtime/shadow-sip/` contient `status.json`, `state.sqlite`, `fills.csv`, `decisions.csv` et les historiques locaux. Paper utilise son propre dossier. `paper.lock` empêche deux instances paper utilisant le même répertoire d'état.

Utiliser un compte paper dédié et initialement plat sur QQQ, avec au moins 100 000 USD d'equity au premier rattachement. Le compte et les paramètres sont liés au journal. Ne pas lancer une autre instance dans un autre dossier sur le même compte.

Les intentions sont enregistrées avant POST. Un envoi ambigu se rapproche par `client_order_id` et n'est jamais renvoyé aveuglément. Les fills partiels sont comptabilisés une fois. Au redémarrage, un ordre en attente est rapproché/annulé puis la position gérée est fermée avant toute nouvelle entrée. Une position héritée du jour précédent est fermée à la réouverture et suspend le bot.

Un trou de données, une décision dépassée avec position, un ordre refusé ou une incohérence de compte suspend les entrées et provoque une tentative de fermeture. La dernière minute peut être attendue jusqu'à expiration des 20 secondes. En paper, les décisions manquées au lancement ne sont pas rattrapées. Shadow peut rejouer le début de la séance aux opens archivés ; ces transactions de démarrage doivent être distinguées des décisions observées ensuite prospectivement. Le filtre historique qui exclut une journée entière incomplète ne peut pas être reproduit à l'avance : la surveillance du préfixe courant est une exception de sécurité explicite.

**Ctrl+C** suspend durablement les entrées et tente de fermer la position gérée si le marché est ouvert. Contrôler ensuite les positions et ordres QQQ dans Alpaca. Une panne de réseau, un arrêt du PC ou une fermeture du marché peut empêcher cette opération.

Après une pause durable ou un ordre incertain, inspecter le compte et le journal avant reprise. Ne pas supprimer la base ou remettre les pauses à zéro avec une position ou un ordre en attente. Aucun déblocage automatique n'est fourni. Une simple pause pour données incomplètes de la séance est réévaluée à la séance suivante.

Si shadow s'arrête avec une position et manque la clôture, la séance suivante est suspendue : reconstruire les décisions manquées depuis l'historique avant de continuer le journal. Il ne reporte pas silencieusement cette position virtuelle sur une nouvelle séance. Cette reconstruction n'est pas automatisée par le lanceur.

## Preuves disponibles

- **47 tests** hors ligne, dont conversion UTC/API, historique incomplet, reprise, timeouts, fills partiels, délais, coûts et clôture : [validation](VALIDATION.md).
- Replay SIP réel : **618 séances, 7 380 décisions, 504 transactions** ; résultat net identique au scénario historique à 0,01 USD/action/côté : [preuve JSON](validation/replay_2026-10-20.json).
- Le replay n'est pas une nouvelle validation hors échantillon. La simulation prospective doit accumuler ses propres observations avant conclusion.

```powershell
.\.venv\Scripts\python.exe -m pytest -q --basetemp=.test_tmp_local
.\.venv\Scripts\python.exe scripts/replay_parity.py
```

Le replay nécessite les pickles préparés locaux de l'étude et ses exports figés. Ils ne sont pas téléchargés par les tests unitaires. Ne charger que les pickles produits par l'acquisition de confiance.

## Sources

[Simulation Alpaca et limites des fills](https://docs.alpaca.markets/us/docs/paper-trading), [offres IEX/SIP](https://docs.alpaca.markets/us/docs/about-market-data-api), [barres historiques](https://docs.alpaca.markets/us/reference/stockbars), [envoi d'ordres](https://docs.alpaca.markets/us/reference/postorder), [recherche par client_order_id](https://docs.alpaca.markets/us/reference/getorderbyclientorderid). Documentation consultée le 20 octobre 2026.
