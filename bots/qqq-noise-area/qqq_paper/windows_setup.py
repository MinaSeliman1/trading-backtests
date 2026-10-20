"""Saisie masquée et enregistrement Windows après contrôle PAPER en lecture seule."""
import argparse
from datetime import datetime,timezone
import getpass
import json
from pathlib import Path
import sqlite3
import sys
import pandas as pd
from .windows_vault import WindowsVault,CredentialError,validate_credentials
from .alpaca import Transport,PaperBroker,DataClient,APIError


def configure(runtime,vault=None):
    runtime=Path(runtime);vault=vault if vault is not None else WindowsVault()
    print('QQQ - CONFIGURATION WINDOWS. Simulation SIP differee uniquement.',flush=True)
    print('Cles PAPER masquees, stockees dans Windows Credential Manager pour cet utilisateur et ce PC.',flush=True)
    key=getpass.getpass('Paper API Key ID : ').strip();secret=getpass.getpass('Paper API Secret : ').strip()
    validate_credentials(key,secret);transport=Transport(key,secret)
    try:
        broker=PaperBroker(transport);account=broker.account()
        if account.get('status')!='ACTIVE' or account.get('account_blocked') or account.get('trading_blocked'):
            raise ValueError('Compte PAPER inactif ou bloque')
        path=runtime/'shadow-sip/state.sqlite'
        if path.exists():
            with sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True) as db:
                previous=db.execute("SELECT value FROM meta WHERE key='paper_account_id'").fetchone()
            if previous and previous[0]!=account.get('id'):raise ValueError('Compte PAPER different du journal existant')
        elif float(account['equity'])<100000:raise ValueError('Capital PAPER initial insuffisant')
        now=pd.Timestamp(broker.clock()['timestamp'])
        probe=DataClient(transport).bars(now-pd.Timedelta(minutes=25),now-pd.Timedelta(minutes=20),'sip')
        vault.save(key,secret)
        folder=runtime/'windows';folder.mkdir(parents=True,exist_ok=True)
        result=dict(state='windows_credentials_configured',utc=datetime.now(timezone.utc).isoformat(),
            mode='shadow',feed='sip',sip_probe_rows=len(probe),storage='Windows Credential Manager, current user/local computer')
        (folder/'setup.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        print('Compte PAPER et acces SIP verifies. Identifiants enregistres dans le coffre Windows. Aucun ordre envoye.',flush=True)
    finally:
        transport.clear();del key,secret


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--runtime',type=Path,default=Path('runtime'))
    p.add_argument('--check-stored',action='store_true');a=p.parse_args(argv)
    try:
        if a.check_stored:
            WindowsVault().load();print('Identifiants PAPER disponibles dans Windows, valeurs masquees.');return 0
        configure(a.runtime);return 0
    except (CredentialError,APIError,ConnectionError,ValueError):
        print('Configuration non terminee : verification PAPER/SIP ou coffre Windows refusee. Aucune cle affichee.',flush=True);return 1
    except KeyboardInterrupt:return 1


if __name__=='__main__':sys.exit(main())
