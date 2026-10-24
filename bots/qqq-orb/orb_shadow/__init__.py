from pathlib import Path
import sys
BOT=Path(__file__).resolve().parents[1]
REPO=BOT.parents[1]
sys.path.insert(0,str(REPO/'bots/qqq-noise-area'))
sys.path.insert(0,str(REPO/'studies/opening-range-5m'))
