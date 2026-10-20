"""Réconcilie les dividendes : SPY émetteur SSGA, QQQ Alpaca dédoublonné."""
from pathlib import Path
import argparse
import hashlib
import json
from datetime import datetime
import zipfile
import xml.etree.ElementTree as ET


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--workspace',type=Path,required=True)
    args=parser.parse_args();folder=args.workspace/'data/noise_area_sources'
    book=folder/'ssga_distributions.xlsx';ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    with zipfile.ZipFile(book) as archive:
        strings=[''.join(x.itertext()) for x in ET.fromstring(archive.read('xl/sharedStrings.xml')).findall('s:si',ns)]
        rows=ET.fromstring(archive.read('xl/worksheets/sheet1.xml')).findall('.//s:row',ns)
    spy={}
    for row in rows:
        values={}
        for cell in row.findall('s:c',ns):
            value=cell.find('s:v',ns)
            text=value.text if value is not None else ''
            values[cell.get('r').rstrip('0123456789')]=strings[int(text)] if cell.get('t')=='s' else text
        if values.get('B')=='SPY':
            day=datetime.strptime(values['D'],'%m/%d/%Y').date().isoformat()
            if '2016-01-01'<=day<='2026-10-16':
                spy[day]=sum(float(values.get(c,'').strip() or 0) for c in ['G','H','I'])
    actions=[]
    for path in (args.workspace/'data/noise_area_extension/corporate_actions').glob('[0-9]*.json'):
        actions.extend(json.loads(path.read_text())['corporate_actions']['cash_dividends'])
    qqq={};duplicates=[]
    for row in actions:
        if row['symbol']!='QQQ': continue
        if row['ex_date'] in qqq:
            assert qqq[row['ex_date']]==float(row['rate']), 'contradictory duplicate dividend'
            duplicates.append(row['ex_date'])
        qqq[row['ex_date']]=float(row['rate'])
    assert len(spy)==43 and len(qqq)==44
    receipts=dict(SPY=dict(source='SSGA official historical distributions XLSX',sha256=hashlib.sha256(book.read_bytes()).hexdigest(),count=len(spy)),
                  QQQ=dict(source='Alpaca corporate actions; exact equal duplicate removed',count=len(qqq),duplicates_removed=duplicates),
                  notes=['Alpaca SPY misses 2016-03-18, 2018-06-15, 2026-09-18; issuer data used for all SPY cash amounts.',
                         'Yahoo independently provides 43 SPY dates and rounded cash amounts.',
                         'Yahoo QQQ misses 2020-09-21; retained Alpaca event. 2018-06-18 cash differs by about 0.00162 USD; Alpaca value retained.',
                         'No minute OHLC adjustment; ex-dividend cash adjusts previous-close band reference only.'])
    for symbol,values in [('SPY',spy),('QQQ',qqq)]:
        (folder/f'{symbol}_dividends_resolved.json').write_text(json.dumps(dict(sorted(values.items())),indent=2),encoding='utf-8')
    (folder/'DIVIDEND_RECONCILIATION.json').write_text(json.dumps(receipts,indent=2),encoding='utf-8')
    print(json.dumps(receipts,indent=2))


if __name__=='__main__': main()
