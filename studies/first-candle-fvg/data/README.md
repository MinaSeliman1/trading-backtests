# Historiques locaux

Les CSV OHLCV complets, les pages brutes et les clés API ne sont pas versionnés. Les résultats dérivés et quelques extraits de bougies nécessaires à l'audit sont inclus dans `results/`.

## Échantillon de référence

| Instrument | Barres avant filtrage RTH | SHA-256 du CSV original |
|---|---:|---|
| SPY | 773 977 | `35e3290e3c4cec117302194f437fd5f8f977d25b983759978eafafdca84390fc` |
| QQQ | 807 421 | `ec954dcbdc0380dc5eaac1a7e06f3f855d21a535972ff5f5609fe3fc773a6f97` |

Acquisition du 19 octobre 2026, fenêtre demandée du 1er janvier 2023 inclus au 21 septembre 2026 exclu ; première et dernière séances retenues : 3 janvier 2023 et 18 septembre 2026. Source : Alpaca Market Data, `feed=sip`, `adjustment=raw`, `timeframe=1Min`. Les manifests d'acquisition originaux sont conservés dans `../docs/data-provenance/` ; leurs chemins désignent les fichiers de la machine d'origine.

Pour télécharger un nouvel instantané depuis le dossier de l'étude :

```powershell
python scripts/download_alpaca.py --start 2023-01-01 --end 2026-09-21 --out data/alpaca_sip_2023_2026 --prompt-credentials
```

La console demande les clés existantes avec saisie masquée. Le script ne les enregistre pas. Voir `../docs/ALPACA_HISTORIQUE_GRATUIT.md` pour le fonctionnement vérifié lors de l'acquisition originale. La profondeur et les droits disponibles peuvent évoluer chez le fournisseur.

Les données originales restent disponibles localement dans le projet de travail et dans son ZIP d'étude. Une nouvelle acquisition peut différer si le fournisseur révise les cotations ; une différence de hash doit être déclarée.
