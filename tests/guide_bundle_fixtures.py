"""Explicit retained v1 snapshot and fictional public-resource fixtures for bundle tests."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
LEGACY=ROOT/'docs/catalog/gear-guide-production-v1-2026-11-05.json'

def public_resources(tmp_path):
    """Exercise the actual parser with detached, previously verified public metadata."""
    rows=json.loads((ROOT/'docs/catalog/gear-guide-t7-resource-evidence.json').read_text(encoding='utf-8'))['items']
    root=tmp_path/'fictional-windower';res=root/'res';res.mkdir(parents=True,exist_ok=True)
    def value(v):return json.dumps(v,ensure_ascii=False) if isinstance(v,str) else str(v)
    (res/'items.lua').write_text('return {\n'+''.join('    ['+str(r['id'])+'] = {'+','.join(k+'='+value(v) for k,v in r.items())+'},\n' for r in rows)+'}\n',encoding='utf-8')
    return root
