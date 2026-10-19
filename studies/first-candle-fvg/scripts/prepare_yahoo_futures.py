"""Ajoute uniquement l'identité vérifiée du contrat, sans modifier les prix."""
import csv
import json
import hashlib
from pathlib import Path


def main():
    folder=Path("data/yahoo_contracts")
    records=json.loads((folder/"acquisition.json").read_text(encoding="utf-8"))
    mapping={"ESZ26.CME":"ES","NQZ26.CME":"NQ"}; provenance=[]
    for record in records:
        if record["status"]!="downloaded": continue
        symbol=record["symbol"]; meta=record["meta"]
        if symbol not in mapping or meta.get("symbol")!=symbol or meta.get("instrumentType")!="FUTURE":
            raise ValueError("unverified contract metadata")
        source=Path(record["csv"]); dest=folder/(mapping[symbol]+"_1m.csv")
        with source.open(newline="",encoding="utf-8") as fin, dest.open("w",newline="",encoding="utf-8") as fout:
            reader=csv.DictReader(fin); writer=csv.DictWriter(fout,fieldnames=reader.fieldnames+["contract"])
            writer.writeheader()
            for row in reader: row["contract"]=symbol; writer.writerow(row)
        provenance.append(dict(source=str(source),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                               output=str(dest),output_sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),
                               transformation="contract column only",identity=meta.get("shortName")))
    (folder/"normalization.json").write_text(json.dumps(provenance,indent=2),encoding="utf-8")
    # Fixed December contracts throughout this sample. No volume-based retrospective switching.
    (folder/"rolls.csv").write_text("effective_date,instrument,contract\n2026-09-21,ES,ESZ26.CME\n2026-09-21,NQ,NQZ26.CME\n",encoding="utf-8")
    print(json.dumps(provenance,indent=2))


if __name__=="__main__": main()
