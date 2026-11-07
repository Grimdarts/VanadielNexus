"""Validate a complete authoring candidate; optionally save it atomically.

This uses the existing catalog service. It never installs bundled resources,
migrates player records, fetches sources or writes Windower/player Lua.
"""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vanadiel_nexus.core.equipment_effects import prepare_source
from vanadiel_nexus.core.guide_catalog import decode_json, validate_catalog


def prepare(raw, source, previous=None):
    candidate = validate_catalog(decode_json(raw), items=source.items,
                                 hand_types=source.hand_types, previous=previous)
    historical = {r['id'] for r in previous['revisions']} if previous else set()
    for revision in candidate['revisions']:
        if revision['id'] not in historical and revision['resource_fingerprint'] != source.fingerprint:
            raise ValueError(f"{revision['id']}: resource fingerprint differs; recheck the evidence")
    return candidate


def serialize(candidate):
    """Candidate bytes; derived validation keys such as _retirements are never written."""
    stored = {k: v for k, v in candidate.items() if not k.startswith('_')}
    return json.dumps(stored, ensure_ascii=False, indent=2) + '\n'


def save_candidate(path, raw, source):
    """Prepare all records and immutable history before touching the old artifact."""
    path = Path(path).resolve()
    root = Path(__file__).resolve().parents[1]
    if path == root / 'vanadiel_nexus/resources/gear_guides.json':
        raise ValueError('This authoring tool cannot replace the production bundle')
    if path.is_relative_to(Path(source.root).resolve()):
        raise ValueError('Windower resources are read-only')
    previous = None
    if path.exists():
        previous = validate_catalog(decode_json(path.read_text(encoding='utf-8')), items=source.items,
                                    hand_types=source.hand_types)
    candidate = prepare(raw, source, previous)
    if previous:
        # The on-disk candidate is its own portable immutable history. Do not
        # silently lose revisions/source records when authoring a later batch.
        for field in ('sets', 'revisions', 'sources'):
            old_ids = {row['id'] for row in previous[field]}
            if not old_ids <= {row['id'] for row in candidate[field]}:
                raise ValueError(f'{field}: retain historical records in the candidate')
    payload = serialize(candidate)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', newline='\n',
                                         dir=path.parent, prefix=path.name + '.',
                                         suffix='.tmp', delete=False) as stream:
            temp = Path(stream.name)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        if temp is not None and temp.exists():
            temp.unlink()
    return candidate


def summary(candidate):
    revisions = candidate['revisions']
    gaps = [r for r in candidate['coverage'] if r['status'] == 'gap']
    return {'schema_version': 2, 'sets': len(candidate['sets']), 'revisions': len(revisions),
            'jobs_with_revisions': sorted({j for s in candidate['sets'] for j in s['jobs']}),
            'verified_revisions': sum(r['verification']['status'] == 'verified' for r in revisions),
            'unresolved_revisions': sum(r['verification']['status'] == 'unresolved' for r in revisions),
            'coverage_rows': len(candidate['coverage']), 'open_priorities': len(gaps),
            'all_job_completion': 'Not certified by structural validation'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('candidate', type=Path)
    parser.add_argument('--windower', required=True)
    parser.add_argument('--output', type=Path, help='Authoring artifact only; default is validation without writes')
    args = parser.parse_args()
    source = prepare_source(args.windower)
    raw = args.candidate.read_text(encoding='utf-8')
    candidate = save_candidate(args.output, raw, source) if args.output else prepare(raw, source)
    print(json.dumps(summary(candidate), indent=2))


if __name__ == '__main__':
    main()
