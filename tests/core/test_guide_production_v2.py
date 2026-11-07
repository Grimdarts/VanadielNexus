"""Production publication: real bundle/loader/parser, retained history and explicit adoption."""
from copy import deepcopy
from pathlib import Path
import hashlib,json
import pytest
from tests.guide_bundle_fixtures import ROOT,LEGACY,public_resources
from vanadiel_nexus.core import gear_guides,gear_workspace as ws
from vanadiel_nexus.core.guide_catalog import CatalogError,resolve_reference,effective_revision_id,normalize_legacy
from vanadiel_nexus.core.equipment_matching import requirements_match,allocate_requirements

F=ROOT/'docs/catalog';PROD=ROOT/'vanadiel_nexus/resources/gear_guides.json'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))

@pytest.fixture
def published(tmp_path):
    return gear_guides.load_catalog(windower_dir=str(public_resources(tmp_path)))

def test_publication_is_a_lossless_verified_projection_and_keeps_the_full_candidate():
    c=read(F/'gear-guide-t7-candidate.json');p=read(PROD);proof=read(F/'gear-guide-t7-production-replacement.json')
    sha=lambda x:hashlib.sha256(Path(x).read_bytes()).hexdigest()
    assert sha(PROD)==proof['production_sha256'] and sha(LEGACY)==proof['prior_production_sha256']
    assert sha(F/'gear-guide-t7-candidate.json')==proof['baseline_candidate_sha256']
    assert [len(p[k]) for k in ('sets','revisions','sources')]==[512,539,1331]
    assert [len(c[k]) for k in ('sets','revisions','sources')]==[520,547,1331]
    assert p['sets']==[s for s in c['sets'] if s['id'] not in proof['excluded_unresolved_set_ids']]
    assert p['revisions']==[r for r in c['revisions'] if r['verification']['status']=='verified']
    assert len(proof['excluded_unresolved_revision_ids'])==8
    assert all(r['verification']['status']=='unresolved' for r in c['revisions'] if r['id'] in proof['excluded_unresolved_revision_ids'])
    assert all(p[k]==v for k,v in c.items() if k not in ('sets','revisions','delivery_status'))
    assert not any(k.startswith('_') for k in p)

def test_actual_loader_exposes_512_effective_sets_and_no_private_or_retired_picks(published):
    jobs={j for s in published['sets'] for j in s['jobs']};assert len(jobs)==22
    retired=published['_retirements'];assert len(retired)==27
    picks={r['id']:r for job in jobs for targets in gear_guides.revision_tree(published,job).values() for versions in targets.values() for r in versions}
    assert len(picks)==512 and not set(picks)&set(retired)
    assert all(r['verification']['status']=='verified' for r in picks.values())
    assert not set(read(F/'gear-guide-t7-production-replacement.json')['excluded_unresolved_revision_ids'])&set(picks)

def test_missing_resources_still_fail_closed(tmp_path):
    with pytest.raises(CatalogError,match='resource unavailable'):
        gear_guides.load_catalog(windower_dir=str(tmp_path/'no-resources'))

def test_production_duplicate_slots_require_two_physical_copies(published):
    r=next(r for r in published['revisions'] if r['set_id']=='nexus:run:refresh-idle')
    slots=[s for s in r['slots'] if s['slot'] in ('ring1','ring2')];assert [s['item_id'] for s in slots]==[26184,26184]
    one=allocate_requirements(slots,[dict(item_id=26184,character_key='Fictional',count=1)],'Fictional')
    two=allocate_requirements(slots,[dict(item_id=26184,character_key='Fictional',count=2)],'Fictional')
    assert sum(x['owned'] for x in one.values())==1 and sum(x['owned'] for x in two.values())==2

def test_production_augments_are_literal_and_retired_encoding_cannot_be_picked(published):
    r=next(r for r in published['revisions'] if r['set_id']=='nexus:run:dimidiation')
    req=next(s['requirements'] for s in r['slots'] if s['slot']=='back')
    native=['DEX+20','Accuracy+20 Attack+20','DEX+10','Weapon skill damage +10%','Damage taken-5%']
    assert requirements_match(req,{'augments':native})
    assert not requirements_match(req,{'augments':['DEX+30',*native[1:2],*native[3:]]})

def test_saved_retired_snapshot_overrides_and_bindings_need_explicit_adoption(published,tmp_path):
    old=next(r for r in published['revisions'] if r['set_id']=='nexus:bst:engaged-balanced' and r['version_order']==1)
    target=ws.prepare_target(published,old['id'],target_id='saved',character_key='Fictional')
    target['overrides']=[{'slot':'back','requirements':{'augments':['HP+60']}}]
    target['bindings']=[{'slot':'back','bag_id':8}]
    data=ws.empty_workspace();data['targets']=[target]
    store=ws.WorkspaceStore(tmp_path/'workspace.json');store.load();store.save(data)
    before=store.path.read_bytes();snapshot,status=resolve_reference(target,published)
    assert snapshot==old and status=='retired'
    head=effective_revision_id(published,old['id']);assert next(r for r in published['revisions'] if r['id']==head)['version_order']==3
    proposal,delta=ws.prepare_adoption(store.data,'saved',published,head)
    assert store.path.read_bytes()==before and store.data==data
    assert delta['before']==target and proposal['targets'][0]['revision_id']==head
    assert proposal['targets'][0]['overrides']==target['overrides'] and proposal['targets'][0]['bindings']==target['bindings']

def test_unproven_legacy_association_is_retained_without_guessing_slots(published):
    legacy={'guideSet':'378247','guideItemId':26182,'guideTarget':{'name':'Chirich Ring +1'}}
    before=deepcopy(legacy);result=normalize_legacy(legacy,published['revisions'])
    assert legacy==before and result['original']==before and result['status']=='unresolved' and result['revision_id'] is None
