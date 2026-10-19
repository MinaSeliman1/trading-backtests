"""Télécharge des fichiers publics explicitement indiqués et conserve leur provenance."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen


def fetch(url, dest):
    dest=Path(dest); dest.parent.mkdir(parents=True,exist_ok=True)
    digest=hashlib.sha256(); size=0
    with urlopen(Request(url,headers={"User-Agent":"FirstCandleResearch/1.0"}),timeout=45) as response:
        final_url=response.url
        headers={k:response.headers.get(k) for k in ["Content-Type","Content-Length","Last-Modified","ETag"]}
        with dest.open("wb") as output:
            while chunk:=response.read(1024*1024):
                size+=len(chunk)
                if size>600*1024*1024: raise ValueError("file exceeds research download cap")
                digest.update(chunk); output.write(chunk)
    result=dict(url=url,final_url=final_url,path=str(dest),retrieved_utc=datetime.now(timezone.utc).isoformat(),
                bytes=size,sha256=digest.hexdigest(),headers=headers)
    dest.with_suffix(dest.suffix+".provenance.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps(result),flush=True)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--item",action="append",required=True,help="local_filename=https://public/file")
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    for specification in args.item:
        name,url=specification.split("=",1)
        if Path(name).name!=name: parser.error("local filename only")
        fetch(url,args.out/name)


if __name__=="__main__": main()
