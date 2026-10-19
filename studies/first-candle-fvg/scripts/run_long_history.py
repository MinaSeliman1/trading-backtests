"""Lance l'étude longue une fois les données Alpaca réellement téléchargées et vérifiées."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import argparse
import hashlib
import json
import subprocess
import pandas as pd
from fvg_backtest.data import load_csv


def digest(path):
    result=hashlib.sha256()
    with Path(path).open("rb") as source:
        while chunk:=source.read(1024*1024): result.update(chunk)
    return result.hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir",type=Path,default=Path("data/alpaca_sip_2023_2026"))
    parser.add_argument("--out",type=Path,default=Path("results/alpaca_sip_long"))
    args=parser.parse_args(); args.out.mkdir(parents=True,exist_ok=True)
    specifications=[]; profiles=[]
    for symbol in ["SPY","QQQ"]:
        manifest_path=args.data_dir/f"{symbol}_manifest.json"
        if not manifest_path.exists(): raise SystemExit(f"{symbol}: acquisition authentifiée non encore effectuée")
        manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("status")!="complete" or manifest["parameters"].get("feed")!="sip" or manifest["parameters"].get("adjustment")!="raw":
            raise SystemExit("SIP raw completed manifest required; no IEX substitution")
        csv=Path(manifest["path"])
        if digest(csv)!=manifest["sha256"]: raise SystemExit("dataset checksum mismatch")
        dataset=load_csv(csv,symbol)
        dataset.quality.to_csv(args.out/f"{symbol}_quality_before_execution.csv",index=False)
        if not dataset.sessions: raise SystemExit(f"{symbol}: aucune séance complète")
        dates=[s.index[0].date() for s in dataset.sessions]
        span=(dates[-1]-dates[0]).days+1
        if len(dates)<252 or span<365:
            raise SystemExit(f"{symbol}: couverture insuffisante pour le protocole IS/OOS ({len(dates)} séances, {span} jours)")
        boundary=int(len(dates)*.7)
        profile=dict(instrument=symbol,valid_sessions=len(dates),span_days=span,first=str(dates[0]),last=str(dates[-1]),
                     IS_first=str(dates[0]),IS_last=str(dates[boundary-1]),OOS_first=str(dates[boundary]),OOS_last=str(dates[-1]),
                     valid_session_fraction=float((dataset.quality.status=="accepted").mean()),
                     calendar="XNYS",quality_policy="entire incomplete sessions excluded, no gap filling")
        profiles.append(profile); print(json.dumps(profile),flush=True)
        specifications.extend(["--data",f"{symbol}={csv}"])
    # Freeze dates before any performance result from the new data is calculated.
    (args.out/"PRE_EXECUTION_SPLIT.json").write_text(json.dumps(profiles,indent=2),encoding="utf-8")
    command=[sys.executable,"-m","fvg_backtest",*specifications,"--sensitivity","--out",str(args.out)]
    print("Dates fixées ; lancement des scénarios inchangés et du walk-forward si la couverture le permet.",flush=True)
    completed=subprocess.run(command,check=False)
    raise SystemExit(completed.returncode)


if __name__=="__main__": main()
