"""Separate versioned personal guide workspace with explicit transactional saves.

Loading is read-only, including backup recovery. A permanent sidecar lock uses
an OS advisory byte/file lock across generation check, backup and replacement;
the OS releases it on process exit. Never unlink that lock (inode races).
All cooperating writers must use this store. External edits are detected before
save, but arbitrary noncooperating writers cannot be made transactional.
"""
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile

from .guide_catalog import (JOBS, _date, decode_json, index_records, integer,
                            materialize_revision, normalize_slots, records,
                            require, text, validate_requirements)
from .equipment_matching import SLOTS

SCHEMA_VERSION = 1
BASENAME = 'gear_workspace.json'


class WorkspaceError(ValueError):
    pass


class WorkspaceConflict(WorkspaceError):
    pass


class UnsupportedVersion(WorkspaceError):
    pass


def empty_workspace():
    return {'schema_version': 1, 'targets': [], 'drafts': [], 'legacy_associations': []}


def _snapshot(snapshot, set_id, revision_id):
    require(isinstance(snapshot, dict), 'snapshot', 'full revision snapshot required')
    require(snapshot.get('id') == revision_id and snapshot.get('set_id') == set_id,
            'snapshot', 'revision/set identity mismatch')
    require(snapshot.get('composition_kind') in ('loadout', 'partial_loadout'),
            'snapshot', 'options cannot be a target')
    slots = normalize_slots(snapshot.get('slots'))
    require(bool(slots), 'snapshot', 'slot records required')
    require(({s['slot'] for s in slots} == set(SLOTS)) if snapshot['composition_kind'] == 'loadout'
            else len(slots) < len(SLOTS), 'snapshot', 'composition kind conflicts with slot coverage')
    for field in ('label', 'equipment_version', 'origin', 'currency', 'resource_fingerprint', 'rationale'):
        text(snapshot.get(field), 'snapshot.' + field)
    integer(snapshot.get('version_order'), 'snapshot.version_order', 1)
    require(snapshot['origin'] in ('source_adaptation', 'nexus_recommendation') and
            snapshot['currency'] in ('current', 'older', 'unknown'), 'snapshot', 'invalid origin/currency')
    verification = snapshot.get('verification')
    require(isinstance(verification, dict), 'snapshot', 'evidence required')
    require(verification.get('status') in ('verified', 'unresolved', 'fixture-only'), 'snapshot', 'invalid verification')
    _date(verification.get('checked_on'), 'snapshot.checked_on')
    text(verification.get('scope'), 'snapshot.scope')
    require(not any(s['state'] == 'unknown' for s in slots) or verification['status'] == 'unresolved',
            'snapshot', 'unknown slots cannot be verified')
    require(isinstance(snapshot.get('assumptions'), list) and
            all(isinstance(a, str) and a.strip() for a in snapshot['assumptions']), 'snapshot', 'assumptions required')
    refs = snapshot.get('source_ids')
    require(isinstance(refs, list) and refs and all(isinstance(s, str) and s for s in refs)
            and len(set(refs)) == len(refs),
            'snapshot', 'source references required')


def _bindings(bindings, slots):
    seen = set()
    selected = {s['slot'] for s in slots if s['state'] == 'selected'}
    for row in records(bindings, 'bindings'):
        slot = row.get('slot')
        require(isinstance(slot, str) and slot in selected and slot not in seen, 'bindings',
                'unique selected canonical slot required')
        seen.add(slot)
        integer(row.get('bag_id'), 'bindings.bag_id')
        if 'observation' in row:
            observation = row['observation']
            require(isinstance(observation, dict), slot, 'observation object required')
            for field in ('snapshot_id', 'resource_fingerprint'):
                text(observation.get(field), 'observation.' + field)


def validate_workspace(value, *, characters=None):
    require(isinstance(value, dict), 'workspace', 'object required')
    version = value.get('schema_version')
    if type(version) is int and version > SCHEMA_VERSION:
        raise UnsupportedVersion(f'Workspace version {version} is newer than supported version 1')
    require(type(version) is int and version == 1, 'workspace', 'supported schema_version is 1')
    targets = index_records(value.get('targets'), 'targets')
    drafts = index_records(value.get('drafts'), 'drafts')
    for key, row in list(targets.items()) + list(drafts.items()):
        text(row.get('character_key'), key + '.character_key')
        if characters is not None:
            require(row['character_key'] in characters, key, 'unresolved character identity')
        if key in targets and row is targets[key]:
            for field in ('set_id', 'revision_id'):
                text(row.get(field), key + '.' + field)
            _snapshot(row.get('snapshot'), row['set_id'], row['revision_id'])
            # Context and sources must survive catalog removal, not just source IDs.
            require(isinstance(row.get('set_snapshot'), dict) and
                    row['set_snapshot'].get('id') == row['set_id'] and
                    isinstance(row['set_snapshot'].get('context'), dict), key, 'set context snapshot required')
            group = row['set_snapshot']
            require(isinstance(group.get('jobs'), list) and group['jobs']
                    and all(j in JOBS for j in group['jobs']), key, 'job context required')
            for field in ('purpose', 'target'):
                text(group.get(field), key + '.set_snapshot.' + field)
            sources = index_records(row.get('source_snapshots'), key + '.source_snapshots')
            require(all(s in sources for s in row['snapshot']['source_ids']), key, 'source snapshots incomplete')
            slots = normalize_slots(row['snapshot']['slots'])
            seen = set()
            for override in records(row.get('overrides'), key + '.overrides'):
                slot = override.get('slot')
                require(isinstance(slot, str) and slot in {s['slot'] for s in slots if s['state'] == 'selected'}
                        and slot not in seen, key, 'unique selected override slot required')
                seen.add(slot)
                validate_requirements(override.get('requirements'), key + '.override')
        else:
            integer(row.get('revision'), key + '.revision', 1)
            require(row.get('mode') in ('owned', 'planning'), key, 'draft mode required')
            slots = normalize_slots(row.get('slots'))
            require(isinstance(row.get('scenario'), dict), key, 'scenario required')
            records(row.get('source_references'), key + '.source_references')
            for slot in slots:
                if slot['state'] == 'selected':
                    require(slot.get('requirement_origin') in ('observed', 'assumed'), key,
                            'observed versus assumed requirement origin required')
                    require(row['mode'] == 'planning' or slot['requirement_origin'] == 'observed', key,
                            'owned draft cannot assert assumed requirements')
        _bindings(row.get('bindings'), slots)
    for association in records(value.get('legacy_associations'), 'legacy_associations'):
        require(isinstance(association.get('original'), dict), 'association', 'original legacy record required')
        require(association.get('status') in ('proven', 'unresolved', 'conflicting'), 'association', 'invalid status')
        if association['status'] == 'proven':
            text(association.get('revision_id'), 'association.revision_id')
            text(association.get('evidence'), 'association.evidence')
    return deepcopy(value)


@dataclass(frozen=True)
class LoadResult:
    status: str  # missing, ok, recovery_available, unsupported, corrupt, unavailable
    diagnostics: tuple[str, ...]


@contextmanager
def writer_lock(path):
    """Fail fast on a concurrent writer. Lock covers the whole transaction."""
    with open(path, 'a+b') as stream:
        if os.name == 'nt':
            import msvcrt
            stream.seek(0)
            try:
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as error:
                raise WorkspaceConflict('Workspace is being saved by another writer') from error
            try:
                yield
            finally:
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            try:
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as error:
                raise WorkspaceConflict('Workspace is being saved by another writer') from error
            try:
                yield
            finally:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def _bytes(path):
    try:
        return path.read_bytes()
    except FileNotFoundError:
        return None


def _generation(primary, backup):
    return tuple(hashlib.sha256(b).hexdigest() if b is not None else None for b in (primary, backup))


def _write_temp(path, payload):
    """Isolated transaction file in the destination filesystem, flushed before replace."""
    descriptor, name = tempfile.mkstemp(prefix=path.name + '.', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        Path(name).unlink(missing_ok=True)
        raise
    return Path(name)


class WorkspaceStore:
    def __init__(self, path, *, characters=None):
        self.path = Path(path)
        self.backup = self.path.with_name(self.path.name + '.bak')
        self.characters = frozenset(characters) if characters is not None else None
        self._data = None
        self._recovery = None
        self._generation = None
        self.pending = None
        self.result = LoadResult('unavailable', ('Load workspace before saving',))

    @classmethod
    def for_user(cls, **kwargs):
        from .paths import data_dir
        return cls(Path(data_dir()) / BASENAME, **kwargs)

    @property
    def data(self):
        return deepcopy(self._data)

    @property
    def recovery(self):
        return deepcopy(self._recovery)

    def load(self):
        self._data = self._recovery = None
        diagnostics = []
        try:
            primary, backup = _bytes(self.path), _bytes(self.backup)
        except OSError as error:
            self.result = LoadResult('unavailable', (str(error),))
            return self.result
        self._generation = _generation(primary, backup)
        for label, raw in (('primary', primary), ('backup', backup)):
            if raw is None:
                continue
            try:
                data = validate_workspace(decode_json(raw), characters=self.characters)
            except UnsupportedVersion as error:
                diagnostics.append(f'{label}: {error}')
                self.result = LoadResult('unsupported', tuple(diagnostics))
                return self.result
            except (ValueError, TypeError) as error:
                diagnostics.append(f'{label}: {error}')
                continue
            if label == 'primary':
                self._data = data
                self.result = LoadResult('ok', ())
            else:
                self._recovery = data
                self.result = LoadResult('recovery_available', tuple(diagnostics + ['Explicit recovery required']))
            return self.result
        if primary is None and backup is None:
            self._data = empty_workspace()
            self.result = LoadResult('missing', ())
        else:
            self.result = LoadResult('corrupt', tuple(diagnostics))
        return self.result

    def save(self, proposal, *, accept_recovery=False):
        """Publish only after replacement. Keep a failed proposal for user review."""
        self.pending = deepcopy(proposal)
        allowed = self.result.status in ('ok', 'missing') or (
            accept_recovery and self.result.status == 'recovery_available')
        if not allowed:
            raise WorkspaceError(f'Workspace is read-only: {self.result.status}')
        candidate = validate_workspace(proposal, characters=self.characters)
        original = self._data if self._data is not None else self._recovery
        historical = {(t['set_id'], t['revision_id']): t for t in original['targets']}
        for target in candidate['targets']:
            identity = (target['set_id'], target['revision_id'])
            prior = historical.get(identity)
            if prior is not None:
                require(all(prior[k] == target[k] for k in ('snapshot', 'set_snapshot', 'source_snapshots')),
                        target['id'], 'immutable target snapshot conflict; adopt a new revision')
            historical[identity] = target
        payload = (json.dumps(candidate, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode('utf-8')
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        with writer_lock(self.path.with_name(self.path.name + '.lock')):
            primary, backup = _bytes(self.path), _bytes(self.backup)
            if _generation(primary, backup) != self._generation:
                raise WorkspaceConflict('Workspace changed since load; reload and review the unsaved proposal')
            try:
                temporary = _write_temp(self.path, payload)
                if self.result.status == 'recovery_available':
                    # Retain corrupt primary as evidence; do not overwrite the good backup.
                    if primary is not None:
                        evidence = _write_temp(self.path.with_name(self.path.name + '.unreadable'), primary)
                        # The unique file is itself the evidence, not a fixed-name overwrite.
                        os.replace(evidence, evidence.with_suffix('.evidence'))
                elif primary is not None:
                    shutil.copy2(self.path, self.backup)
                next_generation = _generation(payload, _bytes(self.backup))
                os.replace(temporary, self.path)
            except BaseException:
                if temporary is not None:
                    temporary.unlink(missing_ok=True)
                # A failed backup copy may have changed backup bytes. Let this
                # instance retry only when its primary has not changed.
                if _bytes(self.path) == primary:
                    self._generation = _generation(primary, _bytes(self.backup))
                raise
            self._generation = next_generation
            self._data = candidate
            self._recovery = None
            self.pending = None
            self.result = LoadResult('ok', ())
        return self.data


def prepare_target(catalog, revision_id, *, target_id, character_key, bindings=()):
    revision = next((r for r in catalog['revisions'] if r['id'] == revision_id), None)
    require(revision is not None, revision_id, 'revision unavailable')
    revision = materialize_revision(revision)
    group = next(s for s in catalog['sets'] if s['id'] == revision['set_id'])
    group = {k: deepcopy(v) for k, v in group.items() if k != 'default_revision_id'}
    return {'id': target_id, 'character_key': character_key, 'set_id': group['id'],
            'revision_id': revision_id, 'snapshot': revision, 'set_snapshot': deepcopy(group),
            'source_snapshots': [deepcopy(s) for s in catalog['sources'] if s['id'] in revision['source_ids']],
            'overrides': [], 'bindings': deepcopy(list(bindings))}


def prepare_adoption(workspace, target_id, catalog, revision_id):
    """Reviewable detached delta; callers must explicitly save before publication."""
    proposal = deepcopy(workspace)
    old = next(t for t in proposal['targets'] if t['id'] == target_id)
    new = prepare_target(catalog, revision_id, target_id=target_id, character_key=old['character_key'])
    require(new['set_id'] == old['set_id'], target_id, 'adoption must retain conceptual identity')
    # Personal bindings/overrides stay separate and require review if a slot disappears.
    new['bindings'], new['overrides'] = deepcopy(old['bindings']), deepcopy(old['overrides'])
    proposal['targets'][proposal['targets'].index(old)] = new
    validate_workspace(proposal)
    return proposal, {'before': deepcopy(old), 'after': deepcopy(new)}
