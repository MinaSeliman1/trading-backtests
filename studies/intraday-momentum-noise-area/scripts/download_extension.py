"""Complète les données locales sans enregistrer les clés, uniquement via Market Data."""
from pathlib import Path
import argparse
import getpass
import json
from datetime import datetime, timezone
from urllib.error import HTTPError
from urllib.request import Request, build_opener
from urllib.parse import urlencode
from alpaca_download_base import download_symbol, sha256, NoRedirect


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    def status(state, **extra):
        (args.out/'job_status.json').write_text(json.dumps(dict(state=state, utc=datetime.now(timezone.utc).isoformat(), **extra), indent=2), encoding='utf-8')
    status('awaiting_credentials')
    headers = {}
    try:
        print('NOISE AREA : HISTORIQUE ALPACA SIP 2016-2026', flush=True)
        print('Saisie masquee. Cles en memoire uniquement. Aucune transaction.', flush=True)
        key = getpass.getpass('Alpaca API Key ID : ').strip()
        secret = getpass.getpass('Alpaca API Secret : ').strip()
        if not key or not secret:
            raise ValueError('empty credentials')
        headers = {'APCA-API-KEY-ID': key, 'APCA-API-SECRET-KEY': secret}
        del key, secret
        for label, start, end in [('2016_2022','2016-01-01','2023-01-01'), ('recent','2026-09-21','2026-10-19')]:
            folder = args.out/label
            for symbol in ['SPY','QQQ']:
                manifest_path = folder/f'{symbol}_manifest.json'
                if manifest_path.exists():
                    old = json.loads(manifest_path.read_text(encoding='utf-8'))
                    assert old['status']=='complete' and sha256(old['path'])==old['sha256']
                    print(f'{label} {symbol}: acquisition existante verifiee', flush=True)
                    continue
                status('downloading', window=label, symbol=symbol)
                download_symbol(symbol,start,end,folder,headers)
        # Corporate actions are market data. They adjust the previous-close reference,
        # never the minute bars themselves. A refusal is recorded without substitution.
        try:
            folder = args.out/'corporate_actions'
            folder.mkdir(exist_ok=True)
            token = None
            for page in range(100):
                params = dict(symbols='SPY,QQQ',start='2016-01-01',end='2026-10-19',limit=1000)
                if token: params['page_token']=token
                url='https://data.alpaca.markets/v1/corporate-actions?'+urlencode(params)
                with build_opener(NoRedirect()).open(Request(url,headers=headers),timeout=40) as response:
                    body=response.read()
                (folder/f'{page+1:04d}.json').write_bytes(body)
                token=json.loads(body).get('next_page_token')
                if not token: break
            else: raise ValueError('corporate action pagination limit')
            (folder/'status.json').write_text(json.dumps(dict(status='complete',pages=page+1)),encoding='utf-8')
        except Exception as error:
            (args.out/'corporate_actions_status.json').write_text(json.dumps(dict(status='unavailable',error_type=type(error).__name__,http_status=getattr(error,'code',None))),encoding='utf-8')
        status('complete')
        print('Acquisition terminee. Les cles ne sont pas sauvegardees.', flush=True)
    except (Exception,KeyboardInterrupt) as error:
        status('failed',error_type=type(error).__name__,http_status=getattr(error,'code',None))
        print(f'Acquisition non terminee : {type(error).__name__}, HTTP {getattr(error,"code",None)}',flush=True)
    finally:
        headers.clear()
    input('Appuyez sur Entree pour fermer cette console.')


if __name__=='__main__': main()
