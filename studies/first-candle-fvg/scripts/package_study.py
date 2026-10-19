"""Archive portable du code, des données acquises et des résultats de référence."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import hashlib


def main():
    root=Path(__file__).resolve().parents[1]
    target=root/"First_Candle_FVG_etude_2026-10-19.zip"
    folders=["fvg_backtest","scripts","tests","tradingview","docs","data/yahoo_28d","data/yahoo_contracts","results/etude_2026-10-19"]
    selected=[]
    for folder in folders:
        selected.extend(p for p in (root/folder).rglob("*") if p.is_file() and "__pycache__" not in p.parts and p.suffix!=".pyc")
    selected.extend(root/p for p in ["README.md","requirements.txt","requirements-lock.txt","run.ps1"])
    with ZipFile(target,"w",compression=ZIP_DEFLATED,compresslevel=6) as zipfile:
        for path in sorted(selected): zipfile.write(path,path.relative_to(root))
    digest=hashlib.sha256(target.read_bytes()).hexdigest()
    target.with_suffix(".zip.sha256").write_text(digest+"  "+target.name+"\n",encoding="ascii")
    with ZipFile(target) as zipfile:
        assert zipfile.testzip() is None
        print(f"{target.name}: {len(zipfile.namelist())} files, {target.stat().st_size} bytes, sha256={digest}")


if __name__=="__main__": main()
