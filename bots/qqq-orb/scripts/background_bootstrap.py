from pathlib import Path
import sys
BOT=Path(__file__).resolve().parents[1]
PACKAGES=BOT.parents[2]/'.python_packages'
if PACKAGES.is_dir():sys.path.insert(0,str(PACKAGES))
sys.path.insert(0,str(BOT))
from orb_shadow.service import main
if __name__=='__main__':raise SystemExit(main())
