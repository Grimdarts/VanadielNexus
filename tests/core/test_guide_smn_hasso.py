"""Bounded SMN99/SAM49 Hasso counterparts: separate identities, unchanged /WAR records, evidence boundaries."""
from pathlib import Path
from dataclasses import replace
import json,hashlib
import pytest
from vanadiel_nexus.core.item_res import Item
from vanadiel_nexus.core.equipment_hands import hand_types
from vanadiel_nexus.core.equipment_matching import SLOTS
from vanadiel_nexus.core.guide_catalog import composition_diagnostics,validate_catalog
F=Path(__file__).resolve().parents[2]/'docs/catalog'
def read(n):return json.loads((F/n).read_text(encoding='utf-8'))
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
KEYS=['balanced','dt','accuracy']
@pytest.fixture
def batch():
 c=read('gear-guide-t7-candidate.json');p=read('gear-guide-t7-resource-evidence.json');items={x['id']:Item(**x) for x in p['items']};return c,p,items,hand_types(items)
def one(c,set_id):
 r=[x for x in c['revisions'] if x['set_id']==set_id];assert len(r)==1;return r[0]
def test_append_only_history_and_counts(batch):
 c,p,items,h=batch;b=next(x for x in c['authoring_batches'] if x['id']=='smn-hasso-2026-11-05')
 assert {k:len(v) for k,v in b['baseline_record_hashes'].items()}==dict(sets=517,revisions=542,sources=1320)
 for f,history in b['baseline_record_hashes'].items():
  now={r['id']:r for r in c[f]};assert all(digest(now[k])==v for k,v in history.items())
 assert [len(c[k]) for k in ('sets','revisions','sources','coverage')]==[520,547,1331,231] and len(p['items'])==863
 retired={x['retired_revision_id'] for b in c['authoring_amendments'] for x in b.get('amendments',[])}
 assert len(retired)==27 and sum(r['verification']['status']=='verified' and r['id'] not in retired for r in c['revisions'])==512
 assert 'all22jobs' in c['delivery_status'] and 'DNC' in c['delivery_status'] and 'SAM49 Hasso' in c['delivery_status']
 validate_catalog(c,items=items,hand_types=h)
@pytest.mark.parametrize('key',KEYS)
def test_sam_counterpart_identical_gear_separate_context(batch,key):
 c,p,items,h=batch;war=one(c,'nexus:smn:engaged-'+key);sam=one(c,'nexus:smn:engaged-sam-'+key)
 assert sam['slots']==war['slots'] and [x['slot'] for x in sam['slots']]==list(SLOTS)
 assert sam['id']!=war['id'] and war['id'] in sam['rationale'] and sam['origin']=='nexus_recommendation'
 assert h[22100]=='two_handed' and h[22218]=='grip' and not any(x.get('requirements') for x in sam['slots'])
 ctx=next(s['context'] for s in c['sets'] if s['id']==sam['set_id'])
 assert ctx['job'].startswith('SMN99/SAM49') and 'Seigan inactive' in ctx['activation'] and 'not continuous uptime' in ctx['activation']
 assert 'job-ability haste' in ctx['haste'] and 'no numeric Hasso value' in ctx['haste'] and 'No external magic haste' in ctx['haste']
 assert 'No /WAR Double Attack' in ctx['traits'] and 'SAM-main-only' in ctx['traits']
 assert 'does not prove a Ward' in ctx['buffs'] and 'no Hasso/Blood Pact delay interaction' in ctx['casting']
 assert not composition_diagnostics(sam['slots'],items,['SMN'],hand_types=h,context=ctx)
 changed=dict(items);changed[22100]=replace(items[22100],skill=1)
 assert composition_diagnostics(sam['slots'],changed,['SMN'],hand_types=hand_types(changed))
def test_war_records_coverage_and_saved_targets_unchanged(batch):
 c,_,_,_=batch;d=read('gear-guide-t7-smn-engaged-definitions.json');h=read('gear-guide-t7-smn-hasso-definitions.json')
 war_rows=[r for r in c['coverage'] if r['job']=='SMN' and r['priority'].startswith('Engaged ')]
 assert war_rows==[r for r in d['coverage_reconciliation']]
 assert all(len(r['set_ids'])==1 and 'sam-' not in r['set_ids'][0] for r in war_rows)
 rows=[r for r in c['coverage'] if r['priority'].startswith('Hasso Engaged ')]
 assert rows==h['coverage_reconciliation'] and [r['set_ids'] for r in rows]==[['nexus:smn:engaged-sam-'+k] for k in KEYS]
 for k in KEYS:
  war=next(s for s in c['sets'] if s['id']=='nexus:smn:engaged-'+k)
  assert 'SMN99/WAR49' in war['context']['job'] and '/WAR has no Hasso' in war['context']['haste'] and 'default_revision_id' not in war
 assert [x['war_counterpart'] for x in h['definitions']]==['nexus:smn:engaged-'+k for k in KEYS]
def test_browser_evidence_revisions_and_source_records():
 e=read('gear-guide-t7-smn-hasso-evidence.json');c=read('gear-guide-t7-candidate.json');h=read('gear-guide-t7-smn-hasso-definitions.json')
 revs={x['url']:x['revision_id'] for x in e['browser_captures']}
 assert revs=={'https://www.bg-wiki.com/ffxi/Hasso':752340,'https://www.bg-wiki.com/ffxi/Attack_Speed':757807,'https://www.bg-wiki.com/ffxi/Samurai':696531,'https://www.bg-wiki.com/ffxi/Blood_Pact':745754,'https://ffxiclopedia.fandom.com/wiki/Hasso':1542307}
 assert all(x['revision_id']==x['current_revision_id'] for x in e['browser_captures'])
 assert [r['id'] for r in e['reconciliation']]==['HASSO-0'+str(i) for i in range(1,8)]
 assert 'Cloudflare challenge' in e['access_change'] and 'not interacted with' in e['access_change']
 assert '/sam(Hasso 10%JA Haste)' in e['node380_subjob_statement']['quote']
 src={s['id']:s for s in c['sources']}
 assert all(i in src and str(revs[src[i]['url']]) in src[i]['locator'] for i in h['sources_added'])
 assert e['new_resources']==h['new_resources']==h['new_hands']==h['new_requirements']==0
 assert any('Blood Pact' in x for x in h['unclaimed']) and 'BRD runtime retirement' in h['unclaimed'][-1]
 assert hashlib.sha256((F/'gear-guide-t7-smn-hasso-evidence.json').read_bytes()).hexdigest()==h['evidence_sha256']
 prior=read('gear-guide-t7-smn-sam-context.json');assert prior['candidate_saved'] is False and e['prior_context_packet']['sha256']=='bfeb50cc8a46c66c56b9e61370818278eb77ca015dae8196ae3b82a0f8df1f46'
