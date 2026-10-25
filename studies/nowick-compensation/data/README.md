# Données Forex Python

Les historiques complets restent locaux et ignorés par Git. Fournisseur : FXCM, archives publiques hebdomadaires minute `https://candledata.fxcorporate.com/m1/{pair}/{year}/{week}.csv.gz`. Documentation officielle : https://github.com/fxcm/MarketData.

`fxcm_raw/` conserve les octets gzip acquis. `prepared/` contient les tableaux NumPy de timestamps UTC, Bid/Ask OHLC en ticks entiers et indicateurs de validité, puis les features15m dérivées. Les SHA256 et statuts HTTP sont dans `results/2026-10-24-python/source_manifest.json`. Le prix en ticks doit être divisé par100000 pour GBPUSD/AUDUSD, par1000 pour USDJPY.

Les prix FXCM sont indicatifs ; des Ask/Bid de clôture sont croisés. Le modèle principal utilise uniquement les Bid avec un coût synthétique fixe, pas une promesse de fills réels au spread constaté. Les trous ne sont pas forward-fill. Voir `PYTHON_PROTOCOL.md` pour la politique de signal et de pénalité de couverture.

Reproduction : lancer `python scripts/download_fxcm.py` depuis le dossier de l'étude, puis `python scripts/run_python.py --run-id <nouvel-identifiant>`. Le téléchargement est reprenable ; un résultat existant n'est pas écrasé. Les archives peuvent devenir indisponibles ou changer chez le fournisseur ; comparer les empreintes au manifest publié. Ne pas republier les historiques complets : conserver les conditions d'utilisation du fournisseur et publier seulement les résultats dérivés nécessaires.
