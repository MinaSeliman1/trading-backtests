"""Acquisition SIP 1 minute en lecture seule. Ne transmet les clés qu'à data.alpaca.markets."""
import argparse
import csv
from datetime import datetime, timezone
import getpass
import gzip
import hashlib
import json
import os
from pathlib import Path
import time
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, build_opener, HTTPRedirectHandler


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        return None  # Never forward authentication headers to a redirected destination.


def headers_from_environment():
    key=os.environ.get("APCA_API_KEY_ID") or os.environ.get("ALPACA_API_KEY")
    secret=os.environ.get("APCA_API_SECRET_KEY") or os.environ.get("ALPACA_SECRET_KEY")
    if not key or not secret: raise ValueError("Alpaca credentials unavailable; use --prompt-credentials")
    return {"APCA-API-KEY-ID":key,"APCA-API-SECRET-KEY":secret,"User-Agent":"FirstCandleResearch/1.0"}


def http_transport(url,headers):
    if not url.startswith("https://data.alpaca.markets/v2/stocks/"):
        raise ValueError("unexpected market-data destination")
    opener=build_opener(NoRedirect())
    for attempt in range(4):
        try:
            with opener.open(Request(url,headers=headers),timeout=40) as response:
                return response.read()
        except HTTPError as error:
            if error.code!=429 or attempt==3: raise
            time.sleep(min(30,max(1,int(error.headers.get("Retry-After","2")))))
    raise RuntimeError("unreachable")


def sha256(path):
    digest=hashlib.sha256()
    with Path(path).open("rb") as file:
        while chunk:=file.read(1024*1024): digest.update(chunk)
    return digest.hexdigest()


def download_symbol(symbol,start,end,out,headers,transport=http_transport):
    if symbol not in ("SPY","QQQ"): raise ValueError("this study downloads SPY and QQQ only")
    out=Path(out); out.mkdir(parents=True,exist_ok=True)
    dest=out/f"{symbol}_1m.csv"; partial=out/f"{symbol}_partial.csv"
    if dest.exists(): raise FileExistsError(f"refusing to replace existing dataset: {dest}")
    pages=out/f"{symbol}_raw_pages"; pages.mkdir(exist_ok=True)
    params=dict(timeframe="1Min",start=start+"T00:00:00Z",end=end+"T00:00:00Z",limit=10000,
                adjustment="raw",feed="sip",sort="asc")
    manifest=dict(provider="Alpaca Market Data",symbol=symbol,parameters=params.copy(),
                  retrieved_utc=datetime.now(timezone.utc).isoformat(),pages=[],rows=0,
                  credential_storage="none",account_endpoints_used=False,order_endpoints_used=False)
    token=None; seen_tokens=set(); first=None; last=None
    with partial.open("w",newline="",encoding="utf-8") as output:
        writer=csv.writer(output); writer.writerow(["timestamp","open","high","low","close","volume"])
        while True:
            query=params.copy()
            if token: query["page_token"]=token
            url=f"https://data.alpaca.markets/v2/stocks/{symbol}/bars?{urlencode(query)}"
            payload=transport(url,headers)
            obj=json.loads(payload)
            if "bars" not in obj: raise ValueError("market-data response has no bars")
            bars=obj["bars"] or []
            for bar in bars:
                if any(k not in bar for k in ["t","o","h","l","c","v"]):
                    raise ValueError("incomplete OHLCV schema")
                if first is None: first=bar["t"]
                last=bar["t"]
                writer.writerow([bar[k] for k in ["t","o","h","l","c","v"]])
            page_path=pages/f"{len(manifest['pages'])+1:04d}.json.gz"
            with gzip.open(page_path,"wb") as raw: raw.write(payload)
            manifest["pages"].append(dict(url=url,path=str(page_path),rows=len(bars),sha256=sha256(page_path)))
            manifest["rows"]+=len(bars)
            print(f"{symbol}: page {len(manifest['pages'])}, {manifest['rows']} bars, last={last}",flush=True)
            token=obj.get("next_page_token")
            if not token: break
            if token in seen_tokens: raise ValueError("pagination repeated a token")
            seen_tokens.add(token)
            if transport is http_transport: time.sleep(.35)
    if not manifest["rows"]: raise ValueError("provider returned no historical bars")
    partial.replace(dest)
    manifest.update(status="complete",path=str(dest),sha256=sha256(dest),first_timestamp=first,last_timestamp=last)
    (out/f"{symbol}_manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    return manifest


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start",default="2023-01-01"); parser.add_argument("--end",default="2026-09-21")
    parser.add_argument("--out",type=Path,default=Path("data/alpaca_sip_2023_2026"))
    parser.add_argument("--prompt-credentials",action="store_true")
    args=parser.parse_args(); args.out.mkdir(parents=True,exist_ok=True)
    job=args.out/"job_status.json"
    def status(state,**extra):
        job.write_text(json.dumps(dict(state=state,time_utc=datetime.now(timezone.utc).isoformat(),**extra),indent=2),encoding="utf-8")
    status("awaiting_credentials" if args.prompt_credentials else "starting")
    try:
        end=datetime.fromisoformat(args.end).replace(tzinfo=timezone.utc)
        start=datetime.fromisoformat(args.start).replace(tzinfo=timezone.utc)
        if start>=end or (datetime.now(timezone.utc)-end).total_seconds()<16*60:
            raise ValueError("end must be >15 minutes old, and after start")
        if args.prompt_credentials:
            print("FIRST CANDLE FVG - HISTORIQUE GRATUIT ALPACA SIP",flush=True)
            print("Lecture seule : aucune transaction ni modification de compte.",flush=True)
            print("Collez vos cles API existantes ci-dessous. Saisie masquee ; aucune sauvegarde des cles.",flush=True)
            key=getpass.getpass("Alpaca API Key ID (masque) : ").strip()
            secret=getpass.getpass("Alpaca API Secret (masque) : ").strip()
            if not key or not secret: raise ValueError("credentials missing")
            headers={"APCA-API-KEY-ID":key,"APCA-API-SECRET-KEY":secret,"User-Agent":"FirstCandleResearch/1.0"}
        else: headers=headers_from_environment()
        for symbol in ["SPY","QQQ"]:
            manifest_path=args.out/f"{symbol}_manifest.json"
            if manifest_path.exists():
                existing=json.loads(manifest_path.read_text())
                if existing.get("status")=="complete" and existing["parameters"]["start"]==args.start+"T00:00:00Z" and existing["parameters"]["end"]==args.end+"T00:00:00Z" and sha256(existing["path"])==existing["sha256"]:
                    print(f"{symbol}: existing verified download reused",flush=True); continue
                raise ValueError("existing manifest does not match requested study")
            status("downloading",symbol=symbol)
            download_symbol(symbol,args.start,args.end,args.out,headers)
        headers.clear(); status("complete")
        print("Acquisition terminee. Les donnees sont pretes pour le controle qualite.",flush=True)
    except (Exception,KeyboardInterrupt) as error:
        # HTTP error text is not echoed; identifiers and authorization headers never enter logs.
        http_status=error.code if isinstance(error,HTTPError) else None
        status("failed",error_type=type(error).__name__,http_status=http_status,
               reason="authentication_or_entitlement" if http_status in (401,403) else "download_not_completed")
        print(f"Acquisition non terminee ({type(error).__name__}, HTTP={http_status}). Aucune cle enregistree.",flush=True)
        if args.prompt_credentials:
            try: input("Appuyez sur Entree pour fermer cette fenetre.")
            except (EOFError,KeyboardInterrupt): pass
        raise SystemExit(2)


if __name__=="__main__": main()
