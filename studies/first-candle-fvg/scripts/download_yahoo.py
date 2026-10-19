"""Acquisition OHLCV réelle, exploratoire uniquement. Aucun prix généré."""
import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import quote


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--symbols",nargs="+",default=["SPY","QQQ"])
    p.add_argument("--range",default="7d",choices=["1d","5d","7d"])
    p.add_argument("--start",help="UTC date inclusive; recent retention only, <=7 days per request")
    p.add_argument("--end",help="UTC date exclusive; used with --start")
    p.add_argument("--out",type=Path,default=Path("data/yahoo"))
    a=p.parse_args(); a.out.mkdir(parents=True,exist_ok=True)
    records=[]
    for symbol in a.symbols:
        base=f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(symbol)}?interval=1m&includePrePost=false"
        windows=[]
        if a.start:
            begin=datetime.fromisoformat(a.start).replace(tzinfo=timezone.utc)
            end=datetime.fromisoformat(a.end).replace(tzinfo=timezone.utc) if a.end else datetime.now(timezone.utc)
            if end<=begin: p.error("end must be after start")
            while begin<end:
                right=min(begin+timedelta(days=7),end)
                windows.append((base+f"&period1={int(begin.timestamp())}&period2={int(right.timestamp())}",begin.strftime("%Y%m%d")))
                begin=right
        else: windows=[(base+f"&range={a.range}","recent")]
        url=windows[0][0]
        record={"symbol":symbol,"url":url,"retrieved_utc":datetime.now(timezone.utc).isoformat(),
                "purpose":"exploratory_only","interval":"1m","adjusted":False}
        try:
            stem=symbol.replace("=","_"); all_rows={}; chunks=[]
            for url,suffix in windows:
                with urlopen(Request(url,headers={"User-Agent":"Mozilla/5.0"}),timeout=30) as response:
                    raw=response.read()
                rawpath=a.out/f"{stem}_{suffix}_raw.json"; rawpath.write_bytes(raw)
                obj=json.loads(raw); results=obj["chart"]["result"]
                if not results: raise ValueError(str(obj["chart"].get("error")))
                chart=results[0]; q=chart["indicators"]["quote"][0]; timestamps=chart["timestamp"]
                for i,ts in enumerate(timestamps):
                    all_rows[ts]=[q.get(k,[None]*len(timestamps))[i] for k in ["open","high","low","close","volume"]]
                chunks.append(dict(url=url,path=str(rawpath),sha256=hashlib.sha256(raw).hexdigest(),rows=len(timestamps)))
            timestamps=sorted(all_rows)
            path=a.out/f"{stem}_1m.csv"
            with path.open("w",newline="",encoding="utf-8") as file:
                writer=csv.writer(file); writer.writerow(["timestamp","open","high","low","close","volume"])
                for ts in timestamps:
                    writer.writerow([datetime.fromtimestamp(ts,timezone.utc).isoformat()]+all_rows[ts])
            record.update(status="downloaded",rows=len(timestamps),csv=str(path),
                          chunks=chunks,csv_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                          first_utc=datetime.fromtimestamp(timestamps[0],timezone.utc).isoformat(),
                          last_utc=datetime.fromtimestamp(timestamps[-1],timezone.utc).isoformat(),meta=chart.get("meta"))
        except Exception as exc:
            record.update(status="failed",error=f"{type(exc).__name__}: {exc}")
        records.append(record); print(json.dumps({k:v for k,v in record.items() if k!="meta"},ensure_ascii=False))
    (a.out/"acquisition.json").write_text(json.dumps(records,indent=2,ensure_ascii=False),encoding="utf-8")
    if not any(r["status"]=="downloaded" for r in records): raise SystemExit(2)


if __name__=="__main__": main()
