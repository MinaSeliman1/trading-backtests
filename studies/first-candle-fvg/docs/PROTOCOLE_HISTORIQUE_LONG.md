# Extension avec sources gratuites — protocole fixé avant les nouveaux résultats

Date : 19 octobre 2026. Demande : obtenir gratuitement au moins un an de données 1 minute et exécuter la validation chronologique hors échantillon.

## Source privilégiée ETF

Alpaca Market Data, endpoint officiel stock bars, `feed=sip`, `timeframe=1Min`, `adjustment=raw`, `sort=asc`. La FAQ officielle permet le SIP historique gratuit dès lors que la fin de requête est antérieure aux quinze dernières minutes. Une clé API personnelle reste nécessaire. Aucun endpoint d'ordre, position ou compte ne doit être appelé. Aucun abonnement ou ordre financier ne doit être créé.

Demande fixée : **2023-01-01 inclus à 2026-09-21 exclu**, soit dernière séance normalement disponible le 18 septembre 2026. Ce plafond exclut les séances du 21 septembre au 19 octobre déjà examinées lors du développement. Il empêche de présenter ces journées déjà vues comme une validation nouvelle. Les dates effectivement reçues et retenues après contrôle qualité seront rapportées.

Le protocole de stratégie et les hypothèses d'exécution restent ceux de `PROTOCOLE.md`, dans leur version corrigée fixant la quantité au close de confirmation. Aucune recherche du meilleur paramètre. Séparation 70/30 par séances retenues, arrêtée par le code existant. Comptes indépendants par scénario/segment. Sensibilités 1/2/3/5 ticks et variantes préfixées conservées. Pas de modification après inspection du P&L hors échantillon.

La disponibilité annoncée n'est pas encore un téléchargement réussi. Contrôler pagination, complétude, fuseau, heures, doublons, OHLC et provenance. Conserver les réponses brutes et leur SHA-256. Les identifiants Alpaca sont saisis localement dans une console masquée ou lus dans les variables de processus prévues ; ils ne sont pas sauvegardés dans le dossier OneDrive ni dans un manifeste.

## Pistes futures

Le dépôt public `kfccolonel1/BARS` annonce plus d'un an de ES/NQ 1 minute, avec prix continus non ajustés, volumes et sources hétérogènes. Ses originaux et son catalogue sont téléchargés uniquement pour audit. Ne pas inventer l'identité d'un contrat, ne pas confondre un continu avec des contrats datés, ne pas utiliser ses résultats comme validation finale par défaut. Les séries datées IBKR annoncées dans ce dépôt ne couvrent à première lecture que décembre 2025–octobre 2026, insuffisant pour une année.

Si un historique long de contrats datés fiables ne peut pas être obtenu gratuitement, l'indiquer séparément pour ES/NQ tout en complétant SPY/QQQ si leur accès fonctionne. Une partition chronologique d'un continu non vérifié ne transforme pas sa qualité en données de validation suffisantes.

## Pistes écartées ou conditionnelles

- HF Data Library : plusieurs années, flux IEX uniquement ; une minute absente peut représenter une absence de transaction sur IEX, et ses hauts/bas ne sont pas consolidés. Éviter d'assimiler ses signaux et volumes au SIP. Accès complet authentifié et conditions académiques à respecter.
- FirstRate Data : le résultat de recherche annonce parfois un an, mais la page actuelle inspectée indique deux semaines (21 septembre–2 octobre 2026). Retenir le contenu réellement accessible, pas l'extrait de recherche périmé.
- CFD Dukascopy : ne pas substituer un CFD aux ETF ou aux vrais contrats CME.
- Données explicitement synthétiques : exclues de toute performance historique.
