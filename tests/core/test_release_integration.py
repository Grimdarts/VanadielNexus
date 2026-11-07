"""Bounded 2.2.0 release input and isolated startup evidence."""
import importlib.util,json,os,subprocess,sys
from pathlib import Path
from tests.guide_bundle_fixtures import ROOT,public_resources

def test_release_navigation_excludes_world_map_but_preserves_its_source():
    from vanadiel_nexus.ui.main_window import NAV
    assert 'WorldMapPage' not in {cls.__name__ for _,cls in NAV}
    assert (ROOT/'vanadiel_nexus/ui/pages/world_map.py').exists()
    spec=(ROOT/'VanadielNexus.spec').read_text(encoding='utf-8')
    assert "'world_map_data.json', 'Mote_Nexus_Hook.lua'" in spec
    assert "'vanadiel_nexus.ui.pages.world_map'" in spec

def test_startup_check_validates_real_production_bundle_with_fictional_resources(tmp_path):
    # startup_check deliberately uses this temporary tree, never a player's data.
    resources=public_resources(tmp_path)
    res=tmp_path/'test-windower'/'res'
    res.mkdir(parents=True)
    (res/'items.lua').write_bytes((resources/'res/items.lua').read_bytes())
    result=tmp_path/'result.json'
    env=dict(os.environ,VN_DATA_DIR=str(tmp_path/'data'),QT_QPA_PLATFORM='offscreen')
    run=subprocess.run([sys.executable,'-m','vanadiel_nexus','--startup-check',str(result)],cwd=ROOT,env=env,capture_output=True,text=True,timeout=30)
    assert run.returncode==0,run.stderr
    payload=json.loads(result.read_text())
    assert payload['version']=='2.2.0' and payload['spawn']['ok']
    assert 'map' not in payload['pages']
    assert payload['guide_catalog']=={'ok':True,'error':None,'schema':2,'sets':512,'revisions':539,'retired':27}
