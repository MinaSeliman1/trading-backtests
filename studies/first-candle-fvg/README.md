# First Candle Rule + Fair Value Gap

**Référence actuelle : étude Alpaca SIP 2023–2026, terminée pour SPY/QQQ. Conclusion : catégorie 3, aucun avantage démontré dans les conditions testées.**

[Rapport final](results/alpaca_sip_long/RAPPORT_FINAL.md) · [Protocole](docs/PROTOCOLE.md) · [Validation](results/alpaca_sip_long/VALIDATION.md) · [Historique des corrections](results/alpaca_sip_long/CORRECTION_NUMERIQUE.md) · [Mission originale](MISSION.md)

## Ce qui a été exécuté

- 930 séances complètes SPY et 931 QQQ, du 3 janvier 2023 au 18 septembre 2026 ; données 1 minute Alpaca SIP brutes, séances incomplètes exclues.
- 116 scénarios : découpage temporel 70/30 IS/OOS, stops A/B, coûts et sensibilités, ainsi que 11 blocs walk-forward par instrument.
- 41 tests automatisés ; audit indépendant de 872 lignes de trades des scénarios principaux IS/OOS, avec variantes communes ; ces lignes ne sont pas 872 observations indépendantes.
- Contrôle des exports des 116 scénarios et des 122 figures ; rapports, paramètres, journaux et hashes archivés.

| Instrument | Stop | Trades OOS | P&L net OOS (USD) |
|---|---:|---:|---:|
| SPY | A | 75 | −1 325,98 |
| SPY | B | 73 | −2 429,87 |
| QQQ | A | 58 | −246,62 |
| QQQ | B | 56 | −1 096,55 |

Chaque scénario possède son propre capital initial de 100 000 USD. Ces comptes et variantes ne sont pas additionnables. Le rapport détaille les hypothèses d'exécution, le dimensionnement causal, les frais, les contacts au tick, l'incertitude statistique et les limites de la validation rétrospective.

L'exploration Yahoo récente de 72 scénarios est [archivée séparément](results/ARCHIVES.md). ES/NQ ne disposent pas de validation longue sur des contrats datés vérifiables. Le [Pine Script](tradingview/README.md) a été compilé dans TradingView ; le backtest annuel et la parité Python/Pine n'ont pas été validés.

## Installation et tests

Depuis ce dossier, après activation d'un environnement Python :

```powershell
python -m pip install -r requirements-lock.txt
python -m pytest -q --basetemp=.test_tmp_local
```

## Reproduire sur des données locales

Les historiques complets ne sont pas inclus dans GitHub. Voir [data/README.md](data/README.md) pour l'acquisition et les empreintes originales.

```powershell
python scripts/download_alpaca.py --start 2023-01-01 --end 2026-09-21 --out data/alpaca_sip_2023_2026 --prompt-credentials
python scripts/run_long_history.py --data-dir data/alpaca_sip_2023_2026 --out results/reproduction_locale
python scripts/audit_long_history.py --results results/reproduction_locale
python scripts/render_long_figures.py --results results/reproduction_locale
```

Le téléchargement écrit des manifests avec les nouveaux chemins locaux. Un fournisseur peut réviser son historique ; comparer les hashes et documenter un nouvel instantané si les données diffèrent. Les manifests des résultats importés conservent leurs chemins et hashes d'origine. Ils ne doivent pas être réécrits pour simuler une nouvelle validation.

Le contrôleur `scripts/verify_long_outputs.py` est propre à l'exécution de référence et suppose `results/alpaca_sip_long`, les chemins originaux et les attestations originales. Pour vérifier l'import GitHub sans les historiques, utiliser `python ../../tools/verify_snapshot.py`. Cela vérifie l'intégrité des fichiers, pas une nouvelle simulation ni un nouvel audit des données.

[README d'origine](README_ORIGINE.md) : documentation conservée pour la traçabilité ; certaines commandes y supposent les fichiers locaux de la machine d'origine.
