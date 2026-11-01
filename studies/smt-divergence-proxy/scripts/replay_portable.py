"""Replay frozen rules on relocated, hash-identical private input archives."""
from pathlib import Path,PureWindowsPath
import importlib.util,argparse,json
p=Path(__file__).resolve().parent/'run.py';spec=importlib.util.spec_from_file_location('frozen_run',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--raw-root',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
 expected=json.loads((m.ROOT/'FREEZE.json').read_text(encoding='utf-8'))
 if a.output.resolve()==(m.ROOT/'results').resolve():raise RuntimeError('preserve published results; choose a separate output folder')
 if a.output.exists() and any(a.output.iterdir()):raise RuntimeError('output must be new or empty')
 if m.np.__version__!=expected['numpy'] or m.pd.__version__!=expected['pandas']:raise RuntimeError('use versions pinned at freeze')
 def relocated_hashes():return {name:m.sha(a.raw_root/PureWindowsPath(name).name) for name in expected['input_hashes']}
 m.input_hashes=relocated_hashes
 loader=m.load_sources;m.load_sources=lambda:loader(a.raw_root)
 m.OUT=a.output;a.output.mkdir(parents=True,exist_ok=True);m.run()
 print('Replay complete. Compare numeric CSV SHA values with results/run_receipt.json; completion timestamp differs.')
if __name__=='__main__':main()
