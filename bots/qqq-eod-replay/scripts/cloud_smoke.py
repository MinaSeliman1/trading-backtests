"""Public dummy-data artifact smoke test; never reads Alpaca credentials."""
from pathlib import Path
import sys,base64,json,os,argparse,tempfile
BOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(BOT))
from qqq_eod.state import seal_folder,open_folder
from qqq_eod.cloud import GitHubReadOnly
KEY=base64.b64encode(bytes(range(32))).decode();IDENTITY={'kind':'public-synthetic-smoke-only'}
def main():
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['create','verify']);p.add_argument('--folder',type=Path,required=True);p.add_argument('--artifact-id',type=int);a=p.parse_args();a.folder.mkdir(parents=True,exist_ok=True)
 if a.mode=='create':
  with tempfile.TemporaryDirectory() as work:
   (Path(work)/'state.json').write_text('{"synthetic":true}',encoding='utf-8');(a.folder/'state.enc').write_bytes(seal_folder(work,KEY,IDENTITY))
 else:
  client=GitHubReadOnly(os.environ['GH_TOKEN'])
  try:blob=client.artifact_bytes(a.artifact_id)
  finally:client.clear()
  with tempfile.TemporaryDirectory() as work:
   open_folder(blob,KEY,IDENTITY,Path(work)/'restored');assert json.loads((Path(work)/'restored/state.json').read_text())=={'synthetic':True}
  print('Synthetic encrypted artifact restored and authenticated; no market credentials used.')
if __name__=='__main__':main()
