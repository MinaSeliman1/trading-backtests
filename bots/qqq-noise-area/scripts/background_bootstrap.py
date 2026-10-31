"""Windowless entry; capture fatal metadata without credential values."""
from pathlib import Path
import sys
BOT=Path(__file__).resolve().parents[1]
PACKAGES=BOT.parents[2]/'.python_packages'
if PACKAGES.is_dir():sys.path.insert(0,str(PACKAGES))
sys.path.insert(0,str(BOT))
from qqq_paper.diagnostics import run,runtime_from_args

def entry():
    from qqq_paper.background import main
    return main()

if __name__=='__main__':
    raise SystemExit(run(entry,runtime_from_args(sys.argv[1:],BOT/'runtime'),'noise'))
