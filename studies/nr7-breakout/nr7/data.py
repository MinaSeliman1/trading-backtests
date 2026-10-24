from pathlib import Path
import importlib.util,sys
ROOT=Path(__file__).resolve().parents[1]
path=ROOT.parent/'closing-momentum/scripts/run_study.py'
spec=importlib.util.spec_from_file_location('nr7_verified_sources',path)
source=importlib.util.module_from_spec(spec);sys.modules[spec.name]=source;spec.loader.exec_module(source)
load_sources=source.load_sources
