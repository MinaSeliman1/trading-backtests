from pathlib import Path
import sys,json
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

@pytest.fixture(scope='session')
def pinned_sources(tmp_path_factory):
 from qqq_eod import source
 bot=Path(__file__).resolve().parents[1];repo=bot.parents[1];lock=json.loads((bot/'ENGINE_LOCK.json').read_text())
 root=source.freeze_sources(repo,lock,tmp_path_factory.mktemp('frozen'))
 source.activate_sources(root,lock)
 return root
