"""Actual bundled v2 page route with fictional resources and workspace only."""
from copy import deepcopy
import json,os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from tests.guide_bundle_fixtures import ROOT,public_resources
from vanadiel_nexus.core import gear_guides,gear_workspace as ws

def page_context(tmp_path,monkeypatch):
    from vanadiel_nexus.core import windower
    from vanadiel_nexus.ui.context import AppContext
    root=public_resources(tmp_path)
    monkeypatch.setenv('VN_DATA_DIR',str(tmp_path/'fictional-data'))
    monkeypatch.setattr(windower,'find_windower_dir',lambda *_:str(root))
    monkeypatch.setattr(AppContext,'_seed_inventory_from_addon_files',lambda self:None)
    ctx=AppContext('fictional');ctx.windower_dir=str(root)
    ctx.inventory_snapshot={'Fictional':[]}
    return ctx

def test_default_page_loads_production_v2_without_writing_personal_targets(qtbot,tmp_path,monkeypatch):
    from vanadiel_nexus.ui.pages.guides import GuidesPage
    ctx=page_context(tmp_path,monkeypatch);before=deepcopy(ctx.db.data)
    store=ws.WorkspaceStore(tmp_path/'workspace.json')
    page=GuidesPage(ctx,workspace=store);qtbot.addWidget(page)
    assert page.catalog_error is None and page.is_v2 and page.current_set
    assert len(page.catalog['sets'])==512 and page.job_combo.count()==22
    assert ctx.db.data==before and not store.path.exists()
    for job in ('RUN','BRD','BST','DNC'):
        page.job_combo.setCurrentText(job)
        assert page.target_combo.count()>0 and page.current_set['verification']['status']=='verified'
    assert not store.path.exists()

def test_default_page_preserves_a_saved_retired_target_until_review(qtbot,tmp_path,monkeypatch):
    from vanadiel_nexus.ui.pages.guides import GuidesPage
    ctx=page_context(tmp_path,monkeypatch);catalog=gear_guides.load_catalog(windower_dir=ctx.windower_dir)
    old=next(r for r in catalog['revisions'] if r['set_id']=='nexus:bst:engaged-balanced' and r['version_order']==1)
    target=ws.prepare_target(catalog,old['id'],target_id='saved',character_key='Fictional')
    data=ws.empty_workspace();data['targets']=[target]
    store=ws.WorkspaceStore(tmp_path/'workspace.json');store.load();store.save(data);before=store.path.read_bytes()
    page=GuidesPage(ctx,workspace=store);qtbot.addWidget(page)
    page.character_combo.setCurrentText('Fictional');page.saved_combo.setCurrentIndex(page.saved_combo.findData('saved'))
    assert page._target()['revision_id']==old['id'] and store.path.read_bytes()==before
    assert 'replaced' in page.retired_banner.text() and not page.retired_banner.isHidden()
    assert not page.edit_button.isEnabled()
