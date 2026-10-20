"""Acquiert les compléments publics réels, sans clé et sans écraser les pièces figées.

Les données peuvent être révisées par les fournisseurs. Un nouveau téléchargement
est une nouvelle acquisition, pas une garantie d'obtenir les hashes de 2026-10-19.
"""
from pathlib import Path
import argparse
from datetime import datetime, timezone
import hashlib
import json
from urllib.request import Request, urlopen


PUBLIC = {
    'paper_revised_2025-09-22.pdf': 'https://concretumgroup.com/wp-content/uploads/2026/02/Beat-the-Market.pdf',
    'authors_python.html': 'https://concretumgroup.com/python-backtesting-beat-the-market-an-effective-intraday-momentum-strategy-for-the-sp500-etf-spy/',
    'VIX_History.csv': 'https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv',
    'ssga_distributions.xlsx': 'https://www.ssga.com/library-content/products/fund-data/etfs/us/spdr-etf-historical-distributions.xlsx',
}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workspace', type=Path, required=True)
    args = p.parse_args()
    folder = args.workspace/'data/noise_area_sources'
    folder.mkdir(parents=True, exist_ok=True)
    receipts = []
    for name, url in PUBLIC.items():
        path = folder/name
        reused = path.exists()
        if not reused:
            with urlopen(Request(url, headers={'User-Agent': 'NoiseAreaResearch/1.0'}), timeout=60) as response:
                body = response.read()
            path.write_bytes(body)
        receipts.append(dict(name=name, url=url, sha256=hashlib.sha256(path.read_bytes()).hexdigest(), reused=reused))
    import yfinance as yf
    yf.set_tz_cache_location(str(folder/'yfinance_cache'))
    for symbol in ['SPY', 'QQQ']:
        path = folder/f'{symbol}_daily_yahoo.csv'
        reused = path.exists()
        if not reused:
            frame = yf.Ticker(symbol).history(start='2016-01-01', end='2026-10-19', interval='1d', auto_adjust=False, actions=True)
            assert not frame.empty and {'Close', 'Dividends'} <= set(frame.columns)
            frame.to_csv(path)
        receipts.append(dict(name=path.name, source='Yahoo Finance via yfinance, daily raw, actions=True',
                             sha256=hashlib.sha256(path.read_bytes()).hexdigest(), reused=reused))
    receipt = dict(utc=datetime.now(timezone.utc).isoformat(), files=receipts)
    (folder/'PUBLIC_DOWNLOAD_RECEIPT.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
