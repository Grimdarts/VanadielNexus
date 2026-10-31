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
    before=list(ctx.db.data['wishlist'])
    page=GuidesPage(ctx)
    qtbot.addWidget(page)
    assert page.character_combo.currentText()=='Someonesmall'
    assert ctx.db.data['wishlist']==before
    assert page.set_combo.count()>0
    page._track()
    once=len(ctx.db.data['wishlist'])
    page._track()
    assert len(ctx.db.data['wishlist'])==once


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
