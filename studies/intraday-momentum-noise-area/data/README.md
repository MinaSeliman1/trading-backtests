# Données Noise Area conservées localement

Aucun historique minute complet ni identifiant n'est inclus dans Git. Les rapports de qualité, hashes, dividendes résolus et audits sont copiés dans `../results/2026-10-19/`.

L'acquisition du 19 octobre 2026 combine les dossiers suivants sous `Trading/data/` :

| Dossier | Dates UTC de requête, fin exclusive | Contenu |
|---|---|---|
| `alpaca_sip_2023_2026` | 2023-01-01 → 2026-09-21 | Historique précédent, hashes et pages réconciliés |
| `noise_area_extension/2016_2022` | 2016-01-01 → 2023-01-01 | Extension SIP raw SPY/QQQ |
| `noise_area_extension/recent` | 2026-09-21 → 2026-10-19 | Dernière séance incluse : 16 octobre |
| `noise_area_extension/corporate_actions` | 2016-01-01 → 2026-10-19 | Dividendes, dédoublonnés et réconciliés |
| `noise_area_sources` | Acquisitions publiques datées | PDF, HTML auteurs, SSGA, CBOE VIX, quotidien Yahoo et reçus |

Pour une nouvelle acquisition, lancer les commandes depuis le dossier d'étude. Les clés existantes sont saisies dans une **console interactive masquée**, jamais dans le chat ou dans un fichier.

```powershell
$studyWorkspace = 'C:/chemin/du/dossier/de/travail'
python scripts/alpaca_download_base.py --start 2023-01-01 --end 2026-09-21 --out "$studyWorkspace/data/alpaca_sip_2023_2026" --prompt-credentials
python scripts/download_extension.py --out "$studyWorkspace/data/noise_area_extension"
python scripts/download_public_sources.py --workspace $studyWorkspace
python scripts/resolve_dividends.py --workspace $studyWorkspace
python scripts/prepare_data.py --workspace $studyWorkspace --out data/prepared
```

La première console réutilise l'utilitaire du projet précédent et porte encore son titre FVG ; les requêtes restent exclusivement des lectures de Market Data. `download_extension.py` acquiert les deux extensions et les corporate actions. Les scripts ne sauvegardent pas les clés. L'accès SIP historique a fonctionné avec le compte gratuit utilisé ; une future politique du fournisseur peut changer.

`resolve_dividends.py` vérifie les **43 SPY / 44 QQQ** de cette étude figée. Pour prolonger la période, créer une nouvelle étude datée et étendre explicitement les bornes et assertions, en conservant les résultats précédents. Ces scripts ne sont pas un système de trading en direct.

Les manifests conservent les chemins d'origine. Pour déplacer les acquisitions archivées, remapper leurs champs `path` et ceux des pages vers les fichiers réellement conservés ; préserver les hashes des contenus. Une nouvelle acquisition possède automatiquement les nouveaux chemins et sa propre provenance. Les fichiers pickle ne sont pas un format d'import pour une source non fiable.

Le filtre NYSE contrôle horaires, jours fériés, DST, demi-séances, doublons et OHLCV. Toute minute attendue absente exclut la séance entière, y compris les journées d'interruptions de marché de mars 2020. Aucun remplissage ni ajustement des OHLC minute. Les dividendes corrigent seulement les références du gap et le rendement total passif ; disponibilité historique de l'annonce supposée.
