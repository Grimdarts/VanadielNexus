import json
import os
import time

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')


def context(qtbot, tmp_path, monkeypatch):
    monkeypatch.setenv('VN_DATA_DIR', str(tmp_path/'data'))
    from vanadiel_nexus.ui.context import AppContext
    ctx=AppContext('test')
    ctx.windower_dir=str(tmp_path/'windower')
    return ctx


def test_guide_page_uses_character_and_does_not_import_without_request(qtbot,tmp_path,monkeypatch):
    from vanadiel_nexus.ui.pages.guides import GuidesPage
    ctx=context(qtbot,tmp_path,monkeypatch)
    ctx.inventory_snapshot={'Someonesmall':[{'name':'Defending Ring','count':1,'character':'Someonesmall'}],
                            'Other':[{'name':'Ring','count':1,'character':'Other'}]}
    ctx.bridge.state={'player_name':'Someonesmall'}  # the character logged in now wins
    before=list(ctx.db.data['wishlist'])
    page=GuidesPage(ctx)
    qtbot.addWidget(page)
    assert page.character_combo.currentText()=='Someonesmall'
    assert ctx.db.data['wishlist']==before
    assert page.target_combo.count()>0 and page.current_set
    page._track()
    once=len(ctx.db.data['wishlist'])
    page._track()
    assert len(ctx.db.data['wishlist'])==once


def test_corrupt_catalog_is_local_error_and_cannot_write_targets(qtbot,tmp_path,monkeypatch):
    from PySide6.QtWidgets import QLabel
    from vanadiel_nexus.core import gear_guides
    from vanadiel_nexus.core.guide_catalog import CatalogError
    from vanadiel_nexus.ui.pages.guides import GuidesPage
    ctx = context(qtbot, tmp_path, monkeypatch)
    before = json.dumps(ctx.db.data, sort_keys=True)
    def rejected(**_):
        raise CatalogError('fixture: duplicate canonical slot ring1')
    monkeypatch.setattr(gear_guides, 'load_catalog', rejected)
    page = GuidesPage(ctx)
    qtbot.addWidget(page)
    page.refresh()
    assert any('Guide catalog unavailable' in label.text() for label in page.findChildren(QLabel))
    assert 'duplicate canonical slot' in page.catalog_error
    assert json.dumps(ctx.db.data, sort_keys=True) == before


def test_guide_page_without_a_known_character_picks_the_first_one_alphabetically(qtbot,tmp_path,monkeypatch):
    from vanadiel_nexus.ui.pages.guides import GuidesPage
    ctx=context(qtbot,tmp_path,monkeypatch)
    ctx.inventory_snapshot={'Zed':[{'name':'Ring','count':1,'character':'Zed'}],
                            'Amy':[{'name':'Ring','count':1,'character':'Amy'}]}
    page=GuidesPage(ctx)
    qtbot.addWidget(page)
    assert page.character_combo.currentText()=='Amy'


def test_g13_displays_exported_labels_and_clears_stale_state(qtbot,tmp_path,monkeypatch):
    from vanadiel_nexus.ui.pages.g13 import G13Page
    ctx=context(qtbot,tmp_path,monkeypatch)
    path=tmp_path/'windower/addons/GearSwap/data/Nova-controls-live.json'
    path.parent.mkdir(parents=True)
    packet={'updated_at':time.time(),'character':'Someonesmall','job':'SMN','layer':'M1',
            'keys':{'M1':['Volt Strike']*22,'M2':['Garuda']*22,'M3':['Help']*22}}
    path.write_text(json.dumps(packet))
    page=G13Page(ctx)
    qtbot.addWidget(page)
    assert page.labels[0].text()=='Volt Strike'
    page.layer.setCurrentText('M2')
    assert page.labels[0].text()=='Garuda'
    packet['updated_at']=time.time()-20
    path.write_text(json.dumps(packet))
    page.refresh()
    assert page.labels[0].text()=='—'
    assert 'Waiting' in page.state_label.text()


# These regressions intentionally exercise the retained v1 compatibility path.
import pytest
from tests.guide_bundle_fixtures import LEGACY

@pytest.fixture(autouse=True)
def retained_v1_bundle(monkeypatch):
    from vanadiel_nexus.core import gear_guides
    monkeypatch.setattr(gear_guides, 'resource_path', lambda *_: str(LEGACY))
