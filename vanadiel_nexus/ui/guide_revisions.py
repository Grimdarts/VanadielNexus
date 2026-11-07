"""Revision-aware interactions for the existing Guide page; no legacy migration."""
from copy import deepcopy
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QMenu, QPlainTextEdit, QVBoxLayout

from ..core import gear_guides, gear_workspace, item_res
from ..core.guide_catalog import SOURCE_HOSTS, effective_revision_id, resolve_reference
from . import widgets, theme
from .forms import Field, FormDialog

# Plain words for each retirement batch; anything else shows the amendment's own reason.
RETIREMENT_REASONS = {
    'brd-augment-parts-2026-11-04': 'augment requirements corrected to the exact in-game augment text; the gear is the same.',
    'bst-provenance-2026-11-05': 'guide citations corrected; the gear and requirements are the same.',
    'scope-fallback-2026-11-05': 'guide citations corrected; the gear and requirements are the same.',
    'bst-ear-labels-2026-11-05': 'earring names corrected; the gear and requirements are the same.',
}
EDIT_RETIRED_TIP = 'Review the update first; edits to an outdated revision would carry the old requirements forward.'


class RevisionReview(QDialog):
    """One concrete target, complete before/after evidence, explicit save."""
    def __init__(self, parent, before, after):
        super().__init__(parent)
        self.setWindowTitle('Review guide revision')
        self.resize(720, 560)
        layout = QVBoxLayout(self)
        label = widgets.label(f"{before['character_key']} · {before['set_snapshot']['target']}\n"
                              f"{before['revision_id']} → {after['revision_id']}", 'SectionTitle')
        label.setWordWrap(True)
        layout.addWidget(label)
        self.details = QPlainTextEdit()
        self.details.setReadOnly(True)
        # Full snapshots include requirements, assumptions, provenance and personal
        # bindings; a short list of changed item names would hide material changes.
        def describe(target):
            revision = target['snapshot']
            evidence = revision['verification']
            lines = [f"Revision: {target['revision_id']}", f"Version: {revision['equipment_version']}",
                     f"Origin: {revision['origin']} · Currency: {revision['currency']}",
                     f"Verification: {evidence['status']} · {evidence['checked_on']} · {evidence['scope']}",
                     'Context: ' + ('; '.join(f'{k}: {v}' for k, v in target['set_snapshot']['context'].items()) or 'No additional context'),
                     'Assumptions: ' + '; '.join(revision['assumptions']),
                     'Rationale: ' + revision['rationale']]
            for row in revision['slots']:
                item = (parent.revision_items or {}).get(row.get('item_id'))
                lines.append(f"{row['slot']}: {row['state']}" +
                             (f" · {item.en if item else 'Item #' + str(row['item_id'])} · {gear_guides.requirement_text(row['requirements'])}"
                              if row['state'] == 'selected' else ''))
            lines += ['Omitted slots retain no selection.',
                      'Personal overrides: ' + ('; '.join(f"{o['slot']}: {gear_guides.requirement_text(o['requirements'])}"
                                                         for o in target['overrides']) or 'None')]
            names = {b['id']: b['en'] for b in (parent.revision_bags or [])}
            lines.append('Personal bags: ' + ('; '.join(f"{b['slot']}: {names.get(b['bag_id'], 'Bag #' + str(b['bag_id']))}"
                                                       for b in target['bindings']) or 'Any equippable bag'))
            lines.append('Sources:')
            lines.extend(f"{s.get('title', s['id'])} · {s.get('locator', 'Source evidence')}\n{s.get('url') or 'Link unavailable'}"
                         for s in target['source_snapshots'])
            return '\n'.join(lines)
        self.details.setPlainText('SAVED\n' + describe(before) + '\n\nPROPOSED\n' + describe(after))
        layout.addWidget(self.details, 1)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Save).setText('Save this revision')
        buttons.button(QDialogButtonBox.Save).setProperty('kind', 'primary')
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def showEvent(self, event):
        theme.dark_title_bar(self)
        super().showEvent(event)


class RevisionGuideMixin:
    def _init_workspace(self, workspace, items, bags):
        self.workspace = workspace or gear_workspace.WorkspaceStore(Path(self.ctx.data_dir) / gear_workspace.BASENAME)
        self.workspace.load()  # reads only; recovery/adoption never occurs here
        self.revision_items = items
        self.revision_bags = bags
        self.view_target_id = None
        self.unsaved_message = ''

    def _revision_controls(self):
        self.provenance = widgets.label('', 'Caption')
        self.provenance.setWordWrap(True)
        self.retired_banner = widgets.label('', 'Caption')
        self.retired_banner.setWordWrap(True)
        self.retired_banner.setProperty('tone', 'warning')
        self.retired_banner.setVisible(False)
        self.saved_state = widgets.label('', 'Caption')
        self.saved_state.setWordWrap(True)
        self.saved_combo = QComboBox()
        self.saved_combo.setToolTip('Inspect a saved revision, including unavailable source revisions.')
        self.saved_combo.currentIndexChanged.connect(self._saved_picked)
        self.workspace_message = widgets.label('', 'Caption')
        self.workspace_message.setWordWrap(True)
        self.reload_workspace = widgets.button('Reload saved targets', on_click=self._reload_workspace)
        self.recover_workspace = widgets.button('Recover saved targets…', on_click=self._recover_workspace)
        self.layout_.addWidget(self.provenance)
        self.layout_.addWidget(self.retired_banner)
        self.layout_.addWidget(self.saved_state)
        self.layout_.addWidget(self.saved_combo)
        self.layout_.addWidget(self.workspace_message)

    def _revision_resources(self):
        if self.revision_items is None:
            self.revision_items = item_res.items(self.ctx.windower_dir)
        if self.revision_bags is None:
            self.revision_bags = item_res.cached('guide_bag_records', self.ctx.windower_dir, 'bags.lua',
                                                lambda path: item_res.parse_rows(path) if path else [])

    def _target(self):
        data = self.workspace.data or self.workspace.recovery or gear_workspace.empty_workspace()
        return next((t for t in data['targets'] if t['id'] == self.view_target_id
                     and t['character_key'] == self.character_combo.currentText()), None)

    def _matching_target(self):
        if not self.current_set or not self.is_v2:
            return None
        data = self.workspace.data or {}
        return next((t for t in data.get('targets', []) if t['set_id'] == self.current_set['set_id']
                     and t['character_key'] == self.character_combo.currentText()), None)

    def _saved_choices(self):
        data = self.workspace.data or self.workspace.recovery or {}
        choices = [('Browse guide catalog', None)]
        character = self.character_combo.currentText()
        for target in data.get('targets', []):
            if target['character_key'] == character:
                jobs = '/'.join(target['set_snapshot']['jobs'])
                outdated = ' · outdated' if self._retirement(target) else ''
                choices.append((f"Saved: {jobs} · {target['set_snapshot']['target']} · {target['revision_id']}{outdated}",
                                target['id']))
        if self.view_target_id not in {key for _, key in choices}:
            self.view_target_id = None
        self._fill(self.saved_combo, choices, self.view_target_id)
        self.saved_combo.setVisible(len(choices) > 1)

    def _retirement(self, target):
        """Retirement record when a saved target sits, unchanged, on a retired revision."""
        if not target or not self.is_v2 or self.catalog_error is not None:
            return None
        if target['revision_id'] not in (self.catalog.get('_retirements') or {}):
            return None
        if resolve_reference(target, self.catalog)[1] != 'retired':
            return None
        return self.catalog['_retirements'][target['revision_id']]

    def _retired_banner_text(self, target, info):
        try:
            when = ' on ' + date.fromisoformat(info['batch'][-10:]).isoformat()
        except ValueError:
            when = ''
        reason = RETIREMENT_REASONS.get(info['batch'], info['reason'])
        return (f"Outdated guide revision. This saved target uses {target['revision_id']}, replaced{when} by "
                f"{info['effective']}: {reason} Review the update to switch; your saved choices are kept.")

    def _mark_outdated_rows(self, rows, target, info):
        """Changed-requirement slots are never graded against the outdated requirement."""
        head = next((r for r in self.catalog['revisions'] if r['id'] == info['effective']), {})
        current = {s['slot']: s for s in head.get('slots', [])}
        retained = {s['slot']: s for s in target['snapshot'].get('slots', [])}
        personal = {o['slot'] for o in target.get('overrides', [])}
        for row in rows:
            # A personal override is the user's own requirement, not the outdated curated one.
            if row.get('state') != 'selected' or row['canonical_slot'] in personal:
                continue
            slot = row['canonical_slot']
            old, new = retained[slot], current.get(slot)
            if (new and new['state'] == 'selected' and new['item_id'] == old['item_id']
                    and new['requirements'] == old['requirements']):
                continue
            designated = row['requirement'].partition(' · Designated: ')
            row.update(status='Outdated requirement',
                       requirement=gear_guides.requirement_text(old['requirements']) + designated[1] + designated[2],
                       detail='Requirement changed in the current revision; review the update to compare correctly.')
        return rows

    def _saved_picked(self, *_):
        self.view_target_id = self.saved_combo.currentData()
        self.refresh()

    def _browse_revision(self):
        self.view_target_id = None

    def _revision_context(self):
        target = self._target()
        if target:
            return target['snapshot'], target['set_snapshot'], target
        if self.is_v2 and self.current_set:
            revision = self.current_set
            return revision, revision['group'], None
        return None, None, None

    def _revision_notice(self):
        result = self.workspace.result
        messages = list(result.diagnostics)
        if result.status not in ('ok', 'missing'):
            messages.insert(0, f'Saved targets are read-only: {result.status}.')
        if self.unsaved_message:
            messages.append(self.unsaved_message)
        self.workspace_message.setText('\n'.join(messages))
        self.recover_workspace.setVisible(result.status == 'recovery_available')
        self.recover_workspace.setEnabled(self.catalog_error is None)

    def _refresh_revision(self):
        self._saved_choices()
        self._revision_notice()
        revision, group, target = self._revision_context()
        retired = self._retirement(target)
        self.source_button.setText('Sources ↗' if revision else 'Open equipment set ↗')
        self.edit_button.setText('Edit selected target…' if revision else 'Set augment target…')
        if revision is None:
            if self.is_v2:
                self.provenance.setText('No revision selected.')
                self.saved_state.clear()
                self.table.set_rows([])
                self.track_button.setEnabled(False)
                self.edit_button.setEnabled(False)
                self.note.clear()
                return True
            self.provenance.setText('Legacy guide reference · revision association unresolved; exact paired slots are not inferred.')
            self.saved_state.setText('Legacy Wishlist tracking remains separate from saved revision targets.')
            self.track_button.setText('Track this set')
            self.track_button.setEnabled(True)
            self.edit_button.setEnabled(True)
            self.table.setToolTip('Legacy reference; ownership checks do not certify an exact simultaneous loadout.')
            return False
        self._revision_resources()
        character = self.character_combo.currentText()
        # Empty complete snapshots are evidence. Missing snapshots are not.
        available = any(not key.startswith('Imported: ') and key.casefold() == character.casefold()
                        for key in self.ctx.inventory_snapshot)
        evidence = revision['verification']
        origin = 'Nexus recommendation' if revision['origin'] == 'nexus_recommendation' else 'Source adaptation'
        self.provenance.setText(f"{origin} · {revision['currency']} · {evidence['status']} ({evidence['checked_on']}: {evidence['scope']})\n"
                                f"Revision: {revision['id']} · {revision['equipment_version']} · {group['target']}")
        matched = target or self._matching_target()
        outdated = retired or self._retirement(matched)
        self.retired_banner.setText(self._retired_banner_text(matched, outdated) if outdated else '')
        self.retired_banner.setVisible(bool(outdated))
        update = self._revision_update(matched)
        saved = f"Saved revision: {matched['revision_id']}." if matched else 'This revision is not tracked.'
        if target and not any(r['id'] == target['revision_id'] for r in self.catalog.get('revisions', [])):
            saved += ' Source revision unavailable; retained snapshot shown.'
        found = next((r for r in self.catalog.get('revisions', []) if r['id'] == revision['id']), None)
        conflict = target is not None and found is not None and found != target['snapshot']
        if conflict:
            saved += ' Catalog revision conflicts with the retained snapshot; changes are disabled.'
        if update:
            saved += f" Available revision: {update['id']}; review before adopting."
        self.saved_state.setText(saved)
        writable = self.workspace.result.status in ('ok', 'missing') and self.catalog_error is None and not conflict
        playable = revision['composition_kind'] != 'equipment_options'
        self.track_button.setText('Review update…' if outdated else
                                  'Review available revision…' if matched else 'Track this revision')
        self.track_button.setEnabled(writable and playable and bool(character) and character != 'No inventory snapshot'
                                     and (not matched or bool(update)))
        self.edit_button.setEnabled(writable and target is not None and not retired)
        self.edit_button.setToolTip(EDIT_RETIRED_TIP if retired else '')
        self.table.setToolTip('Ownership and bag readiness refer to a saved inventory snapshot, not current game state.')
        if playable:
            try:
                rows = gear_guides.revision_rows(revision, self.ctx.all_inventory(), character, target=target,
                                                 items=self.revision_items, bags=self.revision_bags,
                                                 snapshot_available=available)
            except ValueError as error:
                rows = []
                self.workspace_message.setText(f'Inventory comparison unavailable: {error}')
            if retired:
                rows = self._mark_outdated_rows(rows, target, retired)
        else:
            rows = [{'name': self.revision_items[r['item_id']].en if r['item_id'] in self.revision_items else f"Item #{r['item_id']}",
                     'item_id': r['item_id'], 'status': 'Reference option', 'slot': 'Unassigned',
                     'requirement': gear_guides.requirement_text(r['requirements']),
                     'detail': 'Alternative equipment; cannot track as a simultaneous loadout.'}
                    for r in revision['options']]
        self.table.set_rows(rows)
        self.note.setText(' · '.join(revision['assumptions']) + '\n' + revision['rationale'] +
                          '\nInventory comparison uses a saved snapshot. Partial, omitted and unknown slots remain explicit.')
        return True

    def _revision_update(self, target):
        if not target or not self.is_v2:
            return None
        group = next((s for s in self.catalog['sets'] if s['id'] == target['set_id']), None)
        if not group:
            return None
        # Selecting a version explicitly proposes that version. Otherwise use the
        # catalog's designated recommendation, never infer revision age from tier.
        # A retired snapshot reviews straight to its current head, skipping chain links.
        selected = self.current_set
        wanted = (selected['id'] if selected and selected['set_id'] == target['set_id']
                  and selected['id'] != target['revision_id'] and not self.view_target_id
                  else effective_revision_id(self.catalog, target['revision_id']) if self._retirement(target)
                  else group.get('default_revision_id'))
        return next((r for r in self.catalog['revisions'] if r['id'] == wanted
                     and r['id'] != target['revision_id'] and r['composition_kind'] != 'equipment_options'), None)

    def _save_workspace(self, proposal):
        try:
            self.workspace.save(proposal)
        except (OSError, ValueError) as error:
            self.unsaved_message = f'Save failed; saved target unchanged. {error}'
            self._revision_notice()
            return False
        self.unsaved_message = ''
        self.refresh()
        return True

    def _track_revision(self):
        revision, group, target = self._revision_context()
        if revision is None:
            return False
        if not self.track_button.isEnabled():
            return True
        matched = target or self._matching_target()
        if matched:
            update = self._revision_update(matched)
            if not update:
                return True
            try:
                proposal, delta = gear_workspace.prepare_adoption(self.workspace.data, matched['id'], self.catalog, update['id'])
            except ValueError as error:
                self.unsaved_message = f'Revision needs reconciliation before adoption: {error}'
                self._revision_notice()
                return True
            character = self.character_combo.currentText()
            selection_key = self._source_key()
            reviewed_workspace = self.workspace.data
            if RevisionReview(self, delta['before'], delta['after']).exec() == QDialog.Accepted:
                if (character != self.character_combo.currentText() or selection_key != self._source_key()
                        or self.workspace.data != reviewed_workspace):
                    self.unsaved_message = 'Selection or saved targets changed during review; review the target again.'
                    self._revision_notice()
                    return True
                if self._save_workspace(proposal):
                    self.view_target_id = matched['id']
                    self.refresh()
            return True
        proposal = self.workspace.data
        target = gear_workspace.prepare_target(self.catalog, revision['id'], target_id=uuid4().hex,
                                                character_key=self.character_combo.currentText())
        proposal['targets'].append(target)
        if self._save_workspace(proposal):
            self.view_target_id = target['id']
            self.refresh()
        return True

    def _edit_revision(self):
        revision, _, target = self._revision_context()
        if revision is None:
            return False
        row = self.table.selected_row()
        if not target or not self.edit_button.isEnabled() or not row or row.get('state') != 'selected':
            return True
        slot = row['canonical_slot']
        curated = next(s['requirements'] for s in revision['slots'] if s['slot'] == slot)
        override = next((o for o in target['overrides'] if o['slot'] == slot), None)
        current = override['requirements'] if override else curated
        bag_options = {'Any equippable bag': None}
        bag_options.update({b['en']: b['id'] for b in self.revision_bags if b.get('equippable') is True})
        bound = next((b['bag_id'] for b in target['bindings'] if b['slot'] == slot), None)
        if bound is not None and bound not in bag_options.values():
            bag_options[f'Bag #{bound} (unverified)'] = bound
        values = FormDialog.ask(self, f"Personal target · {row['slot']} · {row['name']}", [
            Field('curated', 'Curated requirements (read-only)', 'choice', [gear_guides.requirement_text(curated)]),
            Field('mode', 'Requirements', 'choice', ['Use curated requirements', 'Personal override']),
            Field('path', 'Required path', 'choice', ['Unknown / any', 'A', 'B', 'C', 'D']),
            Field('rank', 'Minimum rank (0 = unspecified)', 'int'),
            Field('augments', 'Required augment text, one per line', 'long'),
            Field('bag', 'Designated bag', 'choice', list(bag_options))],
            {'mode': 'Personal override' if override else 'Use curated requirements',
             'path': current.get('path', 'Unknown / any'), 'rank': current.get('rank', 0),
             'augments': '\n'.join(current.get('augments', [])),
             'bag': next(k for k, v in bag_options.items() if v == bound)})
        if values is None:
            return True
        if target != self._target():
            self.unsaved_message = 'Target changed while editing; reopen the editor.'
            self._revision_notice()
            return True
        proposal = self.workspace.data
        edited = next(t for t in proposal['targets'] if t['id'] == target['id'])
        edited['overrides'] = [o for o in edited['overrides'] if o['slot'] != slot]
        if values['mode'] == 'Personal override':
            requirements = {}
            if values['rank']:
                requirements['rank'] = values['rank']
            if values['path'] != 'Unknown / any':
                requirements['path'] = values['path']
            augments = [s.strip() for s in values['augments'].splitlines() if s.strip()]
            if augments:
                requirements['augments'] = augments
            edited['overrides'].append({'slot': slot, 'requirements': requirements})
        edited['bindings'] = [b for b in edited['bindings'] if b['slot'] != slot]
        if bag_options[values['bag']] is not None:
            edited['bindings'].append({'slot': slot, 'bag_id': bag_options[values['bag']]})
        self._save_workspace(proposal)
        return True

    def _revision_sources(self):
        revision, _, target = self._revision_context()
        if revision is None:
            return None
        sources = target['source_snapshots'] if target else self.catalog['sources']
        return [s for s in sources if s['id'] in revision['source_ids']]

    def _source_key(self):
        revision, _, target = self._revision_context()
        return (self.character_combo.currentText(), revision['id'] if revision else None,
                target['id'] if target else None)

    def _open_revision_source(self, source, key):
        if key != self._source_key() or source not in (self._revision_sources() or []):
            self.status('Guide selection changed; reopen Sources.')
            return
        url = source.get('url')
        try:
            parsed = urlsplit(url or '')
            valid = (parsed.scheme == 'https' and parsed.hostname in SOURCE_HOSTS.get(source.get('kind'), set())
                     and not parsed.username and not parsed.password and parsed.port in (None, 443))
        except ValueError:
            valid = False
        if not valid:
            self.status('Source link unavailable for this revision.')
            return
        self.ctx.open_url(url)

    def _open_revision_sources(self):
        sources = self._revision_sources()
        if sources is None:
            return False
        key = self._source_key()
        if len(sources) == 1:
            self._open_revision_source(sources[0], key)
        elif sources:
            menu = QMenu(self)
            for source in sources:
                label = f"{source.get('title', source['id'])} · {source.get('locator', 'Source evidence')}"
                menu.addAction(label, lambda checked=False, s=deepcopy(source): self._open_revision_source(s, key))
            menu.exec(self.source_button.mapToGlobal(self.source_button.rect().bottomLeft()))
        else:
            self.status('Source reference unavailable for this revision.')
        return True

    def _reload_workspace(self):
        if self.workspace.pending is not None:
            # Failed proposals remain available in the store until explicitly
            # discarded. A refresh must never silently abandon a user's edits.
            if not self.confirm('Reload saved targets', 'Discard the unsaved proposal and reload saved targets?', 'Discard and reload'):
                return
        self.workspace.load()
        self.workspace.pending = None
        self.unsaved_message = ''
        self.refresh()

    def _recover_workspace(self):
        if not self.recover_workspace.isEnabled() or self.workspace.result.status != 'recovery_available':
            return
        recovery = self.workspace.recovery
        if not self.confirm('Recover saved targets',
                            f"Use the retained backup containing {len(recovery['targets'])} targets and "
                            f"{len(recovery['drafts'])} drafts? The unreadable primary will be preserved as evidence.",
                            'Recover backup'):
            return
        try:
            self.workspace.save(recovery, accept_recovery=True)
        except (OSError, ValueError) as error:
            self.unsaved_message = f'Backup recovery failed; saved files retained. {error}'
        else:
            self.unsaved_message = ''
        self.refresh()
