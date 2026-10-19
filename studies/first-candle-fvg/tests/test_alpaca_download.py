"""Réponses contrôlées artificielles ; aucun résultat de marché."""
import json
import pytest
from scripts.download_alpaca import download_symbol, headers_from_environment


def bar(time, price):
    return dict(t=time,o=price,h=price+1,l=price-1,c=price,v=100,n=5,vw=price)


def test_pagination_raw_prices_and_no_secret_in_provenance(tmp_path):
    calls=[]
    pages=[{"bars":[bar("2025-01-02T14:30:00Z",100)],"next_page_token":"next"},
           {"bars":[bar("2025-01-02T14:31:00Z",101)],"next_page_token":None}]
    def transport(url,headers):
        calls.append((url,headers)); return json.dumps(pages.pop(0)).encode()
    headers={"APCA-API-KEY-ID":"fixture_key","APCA-API-SECRET-KEY":"fixture_secret"}
    manifest=download_symbol("SPY","2025-01-01","2025-01-03",tmp_path,headers,transport=transport)
    assert manifest["rows"]==2 and len(calls)==2
    assert "page_token=next" in calls[1][0]
    assert all("feed=sip" in x[0] and "adjustment=raw" in x[0] for x in calls)
    saved=(tmp_path/"SPY_1m.csv").read_text()
    assert "2025-01-02T14:30:00Z,100,101,99,100,100" in saved
    assert "fixture_secret" not in json.dumps(manifest)
    assert "fixture_key" not in (tmp_path/"SPY_manifest.json").read_text()


def test_repeated_token_stops_instead_of_infinite_download(tmp_path):
    page=json.dumps({"bars":[bar("2025-01-02T14:30:00Z",100)],"next_page_token":"same"}).encode()
    with pytest.raises(ValueError,match="pagination"):
        download_symbol("SPY","2025-01-01","2025-01-03",tmp_path,{},transport=lambda *_:page)
    assert not (tmp_path/"SPY_1m.csv").exists()


def test_no_credential_values_printed_and_missing_credentials_fail(monkeypatch):
    for key in ["APCA_API_KEY_ID","APCA_API_SECRET_KEY","ALPACA_API_KEY","ALPACA_SECRET_KEY"]:
        monkeypatch.delenv(key,raising=False)
    with pytest.raises(ValueError,match="credentials"):
        headers_from_environment()
